"""
Módulo de Capacitación: Manual Operativo PRISLAB (UI + PDF).
"""

from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


@login_required
def manual_operativo(request):
    """
    Vista tipo documentación con navegación por capítulos.
    """
    empresa = getattr(request, "empresa_actual", None) or getattr(request.user, "empresa", None)
    return render(
        request,
        "core/manual_usuario.html",
        {
            "empresa": empresa,
        },
    )


@login_required
def manual_operativo_pdf(request):
    """
    Genera un PDF imprimible del Manual Operativo usando ReportLab.
    """
    # Import local para no romper imports si reportlab no está instalado (aunque ya lo usamos en el proyecto)
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors

    empresa = getattr(request, "empresa_actual", None) or getattr(request.user, "empresa", None)
    empresa_nombre = getattr(empresa, "nombre", None) or "PRISLAB"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"Manual Operativo {empresa_nombre}",
        author=empresa_nombre,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>Manual Operativo {empresa_nombre}</b>", styles["Title"]))
    story.append(Paragraph("Versión de capacitación (SaaS Pris-Valle 2030)", styles["Italic"]))
    story.append(Spacer(1, 0.25 * inch))

    # Índice rápido (para impresión)
    story.append(Paragraph("<b>Índice</b>", styles["Heading2"]))
    toc_data = [
        ["1. PDV (Farmacia) – Alerta FEFO + Pop-up Neón"],
        ["2. Cotización Flash (Móvil) – Flujo paso a paso"],
        ["3. Triple Llave (Laboratorio) – Por qué se bloquean PDFs/WhatsApp"],
    ]
    toc_table = Table(toc_data, colWidths=[6.5 * inch])
    toc_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(toc_table)
    story.append(PageBreak())

    # 1) PDV
    story.append(Paragraph("1) PDV (Farmacia) – Alerta FEFO + Pop-up Neón", styles["Heading1"]))
    story.append(
        Paragraph(
            "Cuando agregues un producto al carrito, el sistema selecciona automáticamente el lote FEFO "
            "(primero en caducar). Si el lote vence en menos de 30 días, aparece un Pop-up Neón de alerta.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("<b>ADVERTENCIA (Obligatorio)</b>", styles["Heading2"]))
    story.append(
        Paragraph(
            "Está estrictamente prohibido ignorar la caducidad. La venta NO debe cerrarse sin confirmar que "
            "se leyó la alerta. Prioriza siempre la salida del lote por FEFO.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Capturas de pantalla (placeholders):", styles["Heading3"]))
    story.append(Paragraph("- PDV: búsqueda + agregar al carrito", styles["BodyText"]))
    story.append(Paragraph("- Pop-up Neón FEFO: confirmación obligatoria", styles["BodyText"]))
    story.append(Paragraph("- Cierre de venta: bloqueo si no se confirmó FEFO", styles["BodyText"]))
    story.append(PageBreak())

    # 2) Cotización Flash
    story.append(Paragraph("2) Cotización Flash (Móvil) – Tutorial paso a paso", styles["Heading1"]))
    story.append(
        Paragraph(
            "La Cotización Flash está diseñada para tablet/móvil. Permite seleccionar/crear paciente, "
            "agregar estudios/perfiles con autocompletado y ver el total en tiempo real con énfasis rojo.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.15 * inch))
    pasos = [
        "Paso 1: Buscar paciente por nombre (o crear en 10 segundos).",
        "Paso 2: Buscar estudios/perfiles (catálogo 163) y agregarlos.",
        "Paso 3: Confirmar total (Neón) y enviar por WhatsApp o convertir a Orden.",
        "Paso 4: Convertir a Orden redirige a Recepción con datos precargados.",
    ]
    for p in pasos:
        story.append(Paragraph(f"• {p}", styles["BodyText"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Capturas de pantalla (placeholders):", styles["Heading3"]))
    story.append(Paragraph("- Cotización Flash: pantalla principal", styles["BodyText"]))
    story.append(Paragraph("- Autocompletado de estudios", styles["BodyText"]))
    story.append(Paragraph("- Botones grandes: WhatsApp / Convertir a Orden", styles["BodyText"]))
    story.append(PageBreak())

    # 3) Triple Llave
    story.append(Paragraph("3) Triple Llave (Laboratorio) – Diagrama de bloqueo", styles["Heading1"]))
    story.append(
        Paragraph(
            "El PDF de resultados y el envío por WhatsApp se bloquean automáticamente si NO se cumple "
            "la Triple Llave: (1) deuda cero, (2) validación del químico, (3) privacidad/firma registrada.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("<b>Diagrama (texto)</b>", styles["Heading2"]))
    story.append(Paragraph("Deuda = $0.00  ✅", styles["BodyText"]))
    story.append(Paragraph("Validación Q.C.  ✅", styles["BodyText"]))
    story.append(Paragraph("Privacidad / Teléfono verificado ✅", styles["BodyText"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("Si falta cualquiera: PDF/WhatsApp = BLOQUEADO + explicación en pantalla.", styles["BodyText"]))

    def _footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillGray(0.4)
        canvas.drawRightString(7.5 * inch, 0.5 * inch, f"{empresa_nombre} · Manual Operativo · Página {_doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="manual_operativo_{empresa_nombre.lower()}.pdf"'
    return resp

