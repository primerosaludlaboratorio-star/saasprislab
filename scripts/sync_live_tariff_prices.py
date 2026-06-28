from __future__ import annotations

import argparse
import csv
import re
import time
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import logging


def _clean(value) -> str:
    if value is None:
        return ''
    s = str(value).strip()
    return '' if s.lower() in ('nan', 'none') else s


def _norm(text: str) -> str:
    t = _clean(text).upper()
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', t).strip()


def _parse_price(raw) -> Decimal:
    txt = _clean(raw).replace('$', '').replace(',', '').strip()
    if not txt:
        return Decimal('0.00')
    try:
        return Decimal(txt).quantize(Decimal('0.01'))
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _parse_price (sync_live_tariff_prices.py)")
        return Decimal('0.00')


def _read_tarifa_csv(path: Path):
    rows = []
    for encoding in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            with path.open('r', encoding=encoding, newline='') as fh:
                reader = csv.reader(fh)
                for line in reader:
                    if line and _clean(line[0]).lower() == 'tipo':
                        break
                for line in reader:
                    if not line or len(line) < 5:
                        continue
                    rows.append({
                        'tipo': _clean(line[0]),
                        'codigo': _clean(line[1]),
                        'abreviatura': _clean(line[2]),
                        'descripcion': _clean(line[3]),
                        'importe': _parse_price(line[4]),
                    })
            return rows
        except UnicodeError:
            rows = []
    return rows


@dataclass
class PriceRow:
    precio_id: int
    tipo: str
    codigo: str
    nombre: str
    current: Decimal


def _parse_price_page(html: str):
    soup = BeautifulSoup(html, 'html.parser')
    out: list[PriceRow] = []
    for tr in soup.select('tbody tr'):
        pid = tr.select_one('input.chk-item[data-precio-id]')
        tipo_tag = tr.select_one('span.badge')
        code_tag = tr.select_one('td code')
        price_input = tr.select_one('input.inp-precio')
        cells = tr.select('td')
        if not pid or not tipo_tag or not code_tag or len(cells) < 4 or not price_input:
            continue
        out.append(
            PriceRow(
                precio_id=int(pid.get('data-precio-id')),
                tipo=tipo_tag.get_text(strip=True),
                codigo=code_tag.get_text(' ', strip=True),
                nombre=cells[3].get_text(' ', strip=True),
                current=_parse_price(price_input.get('value')),
            )
        )
    return out


def _build_indexes(rows: list[PriceRow]):
    by_type_code = {'A': {}, 'P': {}, 'Q': {}}
    by_type_name = {'A': {}, 'P': {}, 'Q': {}}
    for row in rows:
        key_code = _norm(row.codigo)
        key_name = _norm(row.nombre)
        by_type_code.setdefault(row.tipo, {})[key_code] = row
        by_type_name.setdefault(row.tipo, {})[key_name] = row
        if row.tipo == 'P' and '|' in key_code:
            by_type_code[row.tipo].setdefault(key_code.split('|', 1)[0], row)
    return by_type_code, by_type_name


def _tipo_tarifa(tipo: str) -> str:
    t = _norm(tipo)
    if 'PAQUETE' in t:
        return 'Q'
    if 'PERFIL' in t:
        return 'P'
    return 'A'


def main():
    parser = argparse.ArgumentParser(description='Sincroniza precios LIMS en producción vía HTTP.')
    parser.add_argument('--base-url', default='https://prislab.labcorecloud.com')
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument(
        '--tarifa-csv',
        default=str(Path(__file__).resolve().parents[1] / 'datos_lims' / 'Tarifa_estudios de laboratorio.csv'),
    )
    parser.add_argument('--retries', type=int, default=12)
    parser.add_argument('--sleep-seconds', type=int, default=30)
    args = parser.parse_args()

    base = args.base_url.rstrip('/')
    tarifa_path = Path(args.tarifa_csv)
    tarifa_rows = _read_tarifa_csv(tarifa_path)
    if not tarifa_rows:
        raise SystemExit(f'No pude leer la tarifa original: {tarifa_path}')

    session = requests.Session()

    login_ok = False
    last_login_status = None
    for attempt in range(1, args.retries + 1):
        session.get(base + '/login/', timeout=30)
        csrf = session.cookies.get('csrftoken', '')
        resp = session.post(
            base + '/login/',
            data={
                'username': args.username,
                'password': args.password,
                'csrfmiddlewaretoken': csrf,
                'next': '/dashboard/',
            },
            headers={'Referer': base + '/login/'},
            timeout=30,
            allow_redirects=False,
        )
        last_login_status = resp.status_code
        if resp.status_code in (302, 303):
            login_ok = True
            break
        if resp.status_code == 429 and attempt < args.retries:
            print(f'[WAIT] login rate limit, intento {attempt}/{args.retries}. Reintento en {args.sleep_seconds}s.')
            time.sleep(args.sleep_seconds)
            continue
        break

    if not login_ok:
        raise SystemExit(f'No pude autenticarme. Último estado de login: {last_login_status}')

    page = session.get(base + '/lims/precios/', timeout=60)
    page.raise_for_status()
    price_rows = _parse_price_page(page.text)
    by_code, by_name = _build_indexes(price_rows)

    print(f'[OK] PrecioItem visibles en página: {len(price_rows)}')
    print(f'[OK] Filas de tarifa leídas: {len(tarifa_rows)}')

    updated = 0
    skipped_same = 0
    missing = []

    for row in tarifa_rows:
        precio = row['importe']
        if precio <= 0:
            continue
        tipo = _tipo_tarifa(row['tipo'])
        code = _norm(row['codigo'])
        abrev = _norm(row['abreviatura'])
        desc = _norm(row['descripcion'])

        hit = by_code.get(tipo, {}).get(code) or by_code.get(tipo, {}).get(abrev) or by_name.get(tipo, {}).get(desc)
        if not hit and tipo == 'P' and code:
            for k, v in by_code.get('P', {}).items():
                if k.startswith(code + '|'):
                    hit = v
                    break
        if not hit:
            missing.append((tipo, row['codigo'], row['abreviatura'], row['descripcion'], str(precio)))
            continue

        if hit.current == precio:
            skipped_same += 1
            continue

        csrf = session.cookies.get('csrftoken', '')
        resp = session.post(
            f'{base}/lims/precios/{hit.precio_id}/actualizar/',
            json={'precio_venta': float(precio)},
            headers={
                'Referer': f'{base}/lims/precios/',
                'X-CSRFToken': csrf,
                'X-Requested-With': 'XMLHttpRequest',
            },
            timeout=30,
        )
        if resp.status_code != 200:
            missing.append((tipo, row['codigo'], row['abreviatura'], row['descripcion'], str(precio), f'HTTP {resp.status_code}'))
            continue
        updated += 1

    print(f'[OK] Precios actualizados: {updated}')
    print(f'[OK] Precios ya alineados: {skipped_same}')
    print(f'[OK] Tarifas sin match directo: {len(missing)}')
    for item in missing[:12]:
        print('[MISS]', item)


if __name__ == '__main__':
    main()