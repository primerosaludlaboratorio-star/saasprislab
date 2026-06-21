#!/usr/bin/env python
"""
AI Coordination Hub for PRISLAB.

Keeps a shared, file-based coordination board for Codex, Claude and Cascada.
It does not call external AI tools directly; it prepares clean handoff prompts,
stores reports as evidence, and maintains a current status document.

Examples:
    python scripts/ai_coordination_hub.py init
    python scripts/ai_coordination_hub.py ingest --agent claude --file reporte.txt
    python scripts/ai_coordination_hub.py brief --agent cascada
    python scripts/ai_coordination_hub.py status
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HUB_DIR = ROOT / "docs" / "ai_coordination"
INBOX_DIR = HUB_DIR / "inbox"
OUTBOX_DIR = HUB_DIR / "outbox"
PROCESSED_DIR = HUB_DIR / "processed"
DROP_DIR = HUB_DIR / "drop"
STATE_PATH = HUB_DIR / "state.json"
STATUS_MD = ROOT / "AI_COORDINATION_STATUS.md"
NEXT_ACTIONS_MD = HUB_DIR / "NEXT_ACTIONS.md"


AGENTS = ("codex", "claude", "cascada")


DEFAULT_NEXT_ACTIONS = """\
# NEXT ACTIONS - PRISLAB Multi-IA

Este archivo es la cola viva de trabajo. Cada agente debe leerlo junto con su
brief antes de empezar. Si no puede ejecutar su tarea principal, toma la
siguiente tarea de su carril sin esperar al usuario.

## Reglas de reparto

- Codex: codigo, causa raiz, pruebas automaticas, commits, documentacion tecnica.
- Claude: auditoria funcional humana en produccion, paso por paso, con evidencia UI/API.
- Cascada: analisis de evidencia, contradicciones, riesgo, priorizacion y checklist.
- Nadie debe pisar archivos que otro agente declare en uso.
- Si un hallazgo no tiene evidencia reproducible, clasificarlo como PENDIENTE_VALIDAR o RUIDO.
- Si aparece un 500, separar primero OPERATIVO vs BUG antes de concluir.

## Carril Codex

1. Cerrar el patron LIMS/legacy `DetalleOrden.estudio` en codigo productivo.
2. Agregar regresiones para cada bloqueo real confirmado.
3. Ejecutar pruebas focalizadas y `manage.py check`.
4. Hacer commit pequeno con mensaje claro y actualizar docs de control.
5. Preparar instrucciones de deploy solo cuando tests pasen.

## Carril Claude

1. Auditar Laboratorio en produccion como usuario real:
   recepcion -> paciente -> estudios -> cobro -> toma -> procesamiento -> captura -> validacion -> PDF -> entrega.
2. No saltarse pasos ni navegar directo a pantallas internas salvo para confirmar.
3. Probar variantes: descuento, cortesia, parcial/CxC, cancelacion/devolucion, impresion.
4. Si Chrome falla, reportar LIMITACION_HERRAMIENTA y pasar a auditoria UI visual de pantallas disponibles.
5. Entregar cada hallazgo con: URL, usuario, paso, esperado, real, evidencia visible, severidad.

## Carril Cascada

1. Leer reportes nuevos en `docs/ai_coordination/inbox`.
2. Clasificar: CONFIRMADO, PROBABLE, PENDIENTE_VALIDAR, OPERATIVO, LIMITACION_HERRAMIENTA, RUIDO.
3. Buscar contradicciones contra commits, tests y `AI_COORDINATION_STATUS.md`.
4. Proponer el siguiente bloque de verificacion sin tocar codigo salvo autorizacion explicita.
5. Mantener lista de deuda real, no ruido.

## Si no hay reportes nuevos

- Claude sigue con el siguiente modulo funcional: Farmacia, Consultorio, Pacientes, Entrega, Finanzas.
- Cascada revisa deuda arquitectonica pendiente: doble arbol Farmacia y permisos rol/grupos.
- Codex revisa bugs de alto impacto y agrega pruebas donde falten.
"""


ROLE_PROMPTS = {
    "codex": """\
Rol: Codex

Responsabilidad:
- Cerrar codigo y causa raiz de hallazgos reales.
- Agregar pruebas automaticas cuando el riesgo lo amerite.
- Hacer commits trazables y actualizar documentos de control.
- Separar problema funcional, problema operativo y limitacion de herramienta.

Reglas:
- No asumir que un reporte externo es cierto sin evidencia.
- Si hay bug real, corregirlo y verificar.
- Si el problema ya esta cerrado con commit/prueba, marcarlo como cerrado y no reabrirlo.
""",
    "claude": """\
Rol: Claude

Responsabilidad:
- Auditoria funcional humana en produccion cuando el navegador este estable.
- Probar flujos reales sin saltarse pasos.
- Reportar paso exacto, esperado, resultado real y si bloquea operacion.

Reglas:
- Si falla Chrome/extensiones, marcar LIMITACION DE HERRAMIENTA.
- No clasificar 500/login/timeouts como bug funcional sin logs.
- Antes de concluir, capturar URL, usuario, paso, mensaje visible y respuesta API si existe.
""",
    "cascada": """\
Rol: Cascada

Responsabilidad:
- Analista de evidencia.
- Clasificar reportes nuevos como CONFIRMADO, PROBABLE, PENDIENTE DE VALIDAR o RUIDO.
- Detectar contradicciones entre reportes y estado real de commits/despliegue.

Reglas:
- No navegar produccion salvo instruccion explicita.
- No reauditar desde cero lo que ya tiene commit, prueba y cierre.
- No declarar modulo aprobado final sin prueba funcional humana + evidencia tecnica + despliegue confirmado.
""",
}


@dataclass
class Evidence:
    id: str
    timestamp: str
    agent: str
    source_file: str
    classification: str
    summary: str


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dirs() -> None:
    for folder in (HUB_DIR, INBOX_DIR, OUTBOX_DIR, PROCESSED_DIR, DROP_DIR):
        folder.mkdir(parents=True, exist_ok=True)
    for agent in AGENTS:
        (DROP_DIR / agent).mkdir(parents=True, exist_ok=True)
    if not NEXT_ACTIONS_MD.exists():
        NEXT_ACTIONS_MD.write_text(DEFAULT_NEXT_ACTIONS, encoding="utf-8")


def load_state() -> dict:
    ensure_dirs()
    if not STATE_PATH.exists():
        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_updated": None,
            "current_focus": "Laboratorio: validacion funcional en produccion",
            "production_commits": {
                "confirmed": ["7da855b"],
                "pending_confirm": ["efa5c2f", "b4f210c"],
            },
            "closed": [
                "Busqueda de pacientes devuelve JSON controlado",
                "Contrato LIMS crea orden con tokens analito/perfil",
                "LAB_VALIDATION_PIN falla cerrado sin configuracion",
            ],
            "pending": [
                "Auditoria funcional humana completa de Laboratorio",
                "Confirmar despliegue VPS de efa5c2f y b4f210c",
                "Validar cancelacion con devolucion financiera",
                "Definir/probar storage final: Vultr Object Storage, Drive o buffer local",
                "Monitorear conexiones idle PostgreSQL",
            ],
            "evidence": [],
        }
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    state["last_updated"] = datetime.now().isoformat(timespec="seconds")
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    write_status_markdown(state)


def classify_text(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("commit", "ok (", "corregido", "desplegado", "validado via api")):
        return "CONFIRMADO"
    if any(k in t for k in ("500", "timeout", "postgresql", "connection", "gunicorn", "nginx")):
        return "OPERATIVO"
    if any(k in t for k in ("chrome extension", "viewport 0x0", "herramienta", "desconectada")):
        return "LIMITACION_HERRAMIENTA"
    if any(k in t for k in ("probable", "posible", "pendiente", "requiere validar")):
        return "PENDIENTE_VALIDAR"
    return "SIN_CLASIFICAR"


def summarize_text(text: str, max_len: int = 280) -> str:
    cleaned = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return cleaned[:max_len] + ("..." if len(cleaned) > max_len else "")


def write_status_markdown(state: dict) -> None:
    lines = [
        "# AI Coordination Status - PRISLAB",
        "",
        f"Ultima actualizacion: {state.get('last_updated') or 'N/A'}",
        f"Foco actual: {state.get('current_focus', 'N/A')}",
        "",
        "## Commits de Produccion",
        "",
        "- Confirmados: " + ", ".join(state.get("production_commits", {}).get("confirmed", [])),
        "- Pendientes de confirmar en VPS: "
        + ", ".join(state.get("production_commits", {}).get("pending_confirm", [])),
        "",
        "## Cerrado",
        "",
    ]
    lines += [f"- {item}" for item in state.get("closed", [])]
    lines += ["", "## Pendiente", ""]
    lines += [f"- {item}" for item in state.get("pending", [])]
    lines += ["", "## Evidencia Reciente", ""]
    for item in state.get("evidence", [])[-10:]:
        lines.append(
            f"- {item['timestamp']} | {item['agent']} | {item['classification']} | {item['summary']}"
        )
    lines.append("")
    STATUS_MD.write_text("\n".join(lines), encoding="utf-8")


def command_init(_: argparse.Namespace) -> None:
    state = load_state()
    save_state(state)
    for agent in AGENTS:
        write_brief(agent, state)
    print(f"Hub inicializado: {HUB_DIR}")
    print(f"Estado: {STATUS_MD}")


def command_ingest(args: argparse.Namespace) -> None:
    ensure_dirs()
    agent = args.agent.lower()
    if agent not in AGENTS:
        raise SystemExit(f"Agente invalido: {agent}. Usa: {', '.join(AGENTS)}")

    if args.file:
        src = Path(args.file)
        text = src.read_text(encoding="utf-8", errors="replace")
        evidence_name = f"{now_stamp()}_{agent}_{src.name}"
        dest = INBOX_DIR / evidence_name
        shutil.copyfile(src, dest)
    else:
        text = args.text or ""
        evidence_name = f"{now_stamp()}_{agent}_manual.md"
        dest = INBOX_DIR / evidence_name
        dest.write_text(text, encoding="utf-8")

    if not text.strip():
        raise SystemExit("No hay texto para ingestar.")

    state = load_state()
    evidence = Evidence(
        id=dest.stem,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        agent=agent,
        source_file=str(dest.relative_to(ROOT)),
        classification=classify_text(text),
        summary=summarize_text(text),
    )
    state.setdefault("evidence", []).append(asdict(evidence))
    save_state(state)
    for target in AGENTS:
        write_brief(target, state)
    print(f"Evidencia registrada: {evidence.id}")
    print(f"Clasificacion inicial: {evidence.classification}")


def ingest_file(agent: str, file_path: Path) -> Evidence:
    """Ingesta un archivo local y devuelve la evidencia creada."""
    ensure_dirs()
    agent = agent.lower()
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise ValueError(f"Archivo vacio: {file_path}")

    evidence_name = f"{now_stamp()}_{agent}_{file_path.name}"
    dest = INBOX_DIR / evidence_name
    shutil.copyfile(file_path, dest)

    state = load_state()
    evidence = Evidence(
        id=dest.stem,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        agent=agent,
        source_file=str(dest.relative_to(ROOT)),
        classification=classify_text(text),
        summary=summarize_text(text),
    )
    state.setdefault("evidence", []).append(asdict(evidence))
    save_state(state)
    for target in AGENTS:
        write_brief(target, state)

    processed_agent_dir = PROCESSED_DIR / agent
    processed_agent_dir.mkdir(parents=True, exist_ok=True)
    processed_name = f"{now_stamp()}_{file_path.name}"
    shutil.move(str(file_path), str(processed_agent_dir / processed_name))
    return evidence


def write_brief(agent: str, state: dict) -> Path:
    ensure_dirs()
    path = OUTBOX_DIR / f"brief_{agent}.md"
    next_actions = NEXT_ACTIONS_MD.read_text(encoding="utf-8", errors="replace")
    lines = [
        f"# Brief para {agent.title()}",
        "",
        ROLE_PROMPTS[agent].strip(),
        "",
        "## Estado Compartido",
        "",
        f"Foco actual: {state.get('current_focus', 'N/A')}",
        "",
        "## Cerrado",
        "",
    ]
    lines += [f"- {item}" for item in state.get("closed", [])]
    lines += ["", "## Pendiente", ""]
    lines += [f"- {item}" for item in state.get("pending", [])]
    lines += [
        "",
        "## Cola Viva de Trabajo",
        "",
        next_actions.strip(),
    ]
    lines += ["", "## Evidencia Reciente", ""]
    for item in state.get("evidence", [])[-8:]:
        lines.append(
            f"- {item['timestamp']} | {item['agent']} | {item['classification']} | {item['summary']}"
        )
    lines += [
        "",
        "## Instruccion",
        "",
        "Trabaja solo sobre esta evidencia y el codigo actual. Si necesitas clasificar, usa:",
        "CONFIRMADO, PROBABLE, PENDIENTE_VALIDAR, OPERATIVO, LIMITACION_HERRAMIENTA, RUIDO.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def command_brief(args: argparse.Namespace) -> None:
    state = load_state()
    path = write_brief(args.agent.lower(), state)
    print(path)


def command_status(_: argparse.Namespace) -> None:
    state = load_state()
    write_status_markdown(state)
    print(STATUS_MD.read_text(encoding="utf-8"))


def command_watch(args: argparse.Namespace) -> None:
    ensure_dirs()
    print("PRISLAB AI Coordination Hub activo.")
    print(f"Coloca reportes en: {DROP_DIR}\\<agente>")
    print("Agentes: " + ", ".join(AGENTS))
    print("Ctrl+C para detener.")

    poll_seconds = max(1, int(args.interval))
    while True:
        try:
            processed_any = False
            for agent in AGENTS:
                agent_drop = DROP_DIR / agent
                for path in sorted(agent_drop.iterdir()):
                    if not path.is_file():
                        continue
                    if path.suffix.lower() not in (".txt", ".md", ".log", ".json"):
                        continue
                    try:
                        evidence = ingest_file(agent, path)
                        processed_any = True
                        print(
                            f"[{evidence.timestamp}] {agent}: "
                            f"{evidence.classification} -> {evidence.summary}"
                        )
                    except Exception as exc:
                        print(f"ERROR procesando {path}: {exc}")
            if processed_any:
                print(f"Estado actualizado: {STATUS_MD}")
                print(f"Briefs actualizados: {OUTBOX_DIR}")
            time.sleep(poll_seconds)
        except KeyboardInterrupt:
            print("\nHub detenido.")
            return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PRISLAB AI coordination hub")
    sub = parser.add_subparsers(required=True)

    p_init = sub.add_parser("init", help="Create coordination folders and briefs")
    p_init.set_defaults(func=command_init)

    p_ingest = sub.add_parser("ingest", help="Register a report from an agent")
    p_ingest.add_argument("--agent", required=True, choices=AGENTS)
    p_ingest.add_argument("--file", help="Path to report file")
    p_ingest.add_argument("--text", help="Inline report text")
    p_ingest.set_defaults(func=command_ingest)

    p_brief = sub.add_parser("brief", help="Generate a brief for one agent")
    p_brief.add_argument("--agent", required=True, choices=AGENTS)
    p_brief.set_defaults(func=command_brief)

    p_status = sub.add_parser("status", help="Print current shared status")
    p_status.set_defaults(func=command_status)

    p_watch = sub.add_parser("watch", help="Watch local drop folders and auto-ingest reports")
    p_watch.add_argument("--interval", type=int, default=3, help="Polling interval in seconds")
    p_watch.set_defaults(func=command_watch)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
