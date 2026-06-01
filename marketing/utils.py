from __future__ import annotations

import os
from django.conf import settings
from django.utils import timezone


def generar_codigo_cupon(prefix: str = "CUPON") -> str:
    return f"{prefix}-{timezone.now().strftime('%Y%m%d%H%M%S')}"


def generar_cupon_imagen_jpg(*, empresa_nombre: str, paciente_nombre: str, payload_qr: str, out_dir_rel: str = "cupones") -> str:
    """
    Genera un cupón como imagen (JPG) con texto + QR.
    Retorna ruta relativa MEDIA (ej: cupones/xxx.jpg).
    """
    from PIL import Image, ImageDraw
    import qrcode

    media_root = getattr(settings, "MEDIA_ROOT", "media")
    out_dir = os.path.join(media_root, out_dir_rel)
    os.makedirs(out_dir, exist_ok=True)

    qr = qrcode.QRCode(version=2, box_size=10, border=2)
    qr.add_data(payload_qr)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    w = 900
    h = 520
    canvas = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(canvas)

    draw.text((30, 30), empresa_nombre or "PRISLAB", fill=(0, 0, 0))
    draw.text((30, 85), "Cupón de Descuento", fill=(30, 30, 30))
    draw.text((30, 140), f"Paciente: {paciente_nombre or 'N/A'}", fill=(30, 30, 30))

    # Pegar QR
    qr_size = 320
    qr_img = qr_img.resize((qr_size, qr_size))
    canvas.paste(qr_img, (w - qr_size - 40, 120))

    filename = f"cupon_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    out_path = os.path.join(out_dir, filename)
    canvas.save(out_path, format="JPEG", quality=92)

    return os.path.join(out_dir_rel, filename).replace("\\", "/")

