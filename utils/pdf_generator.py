import os
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generar_recibo_pdf(datos_pago, ruta_salida=None):
    """
    Genera un PDF en formato Carta (Letter) que contiene en una sola hoja:
    - Mitad Superior: ORIGINAL
    - Línea divisoria de corte
    - Mitad Inferior: COPIA

    Si no se indica ruta_salida, se genera un archivo único en la carpeta
    temporal del sistema para evitar bloqueos por archivos fijos.
    """

    # ------------------------------------------------------------------
    # Determinar la ruta de salida del PDF
    # ------------------------------------------------------------------
    num_recibo_txt = str(datos_pago.get("num_recibo", "temp"))

    if not ruta_salida:
        ruta_salida = os.path.join(
            tempfile.gettempdir(),
            f"recibo_{num_recibo_txt}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
        )

    ruta_salida = os.path.abspath(ruta_salida)

    # ------------------------------------------------------------------
    # Datos seguros del pago (con valores por defecto)
    # ------------------------------------------------------------------
    num_recibo = datos_pago.get("num_recibo", "N/A")
    fecha = datos_pago.get("fecha", "")
    nombre_titular = datos_pago.get("nombre_titular", "N/A")
    cedula = datos_pago.get("cedula", "N/A")
    num_contrato = datos_pago.get("num_contrato", "N/A")
    tipo_contrato = datos_pago.get("tipo_contrato", "N/A")
    cuota_info = datos_pago.get("cuota_info", "N/A")
    forma_pago = datos_pago.get("forma_pago", "N/A")
    banco_origen = datos_pago.get("banco_origen", "N/A")
    banco_destino = datos_pago.get("banco_destino", "N/A")
    num_operacion = datos_pago.get("num_operacion", "N/A")

    def _float(valor):
        """Convierte a número de forma segura para evitar errores de formato."""
        try:
            return float(valor)
        except (TypeError, ValueError):
            return 0.0

    monto_bs = _float(datos_pago.get("monto_bs"))
    monto_usd = _float(datos_pago.get("monto_usd"))
    tasa_bcv = _float(datos_pago.get("tasa_bcv"))

    # ------------------------------------------------------------------
    # Configuración del documento PDF
    # ------------------------------------------------------------------
    c = SimpleDocTemplate(
        ruta_salida,
        pagesize=letter,
        rightMargin=30, leftMargin=30, topMargin=20, bottomMargin=20
    )

    styles = getSampleStyleSheet()

    # Estilo para que el texto largo se AJUSTE dentro de la celda
    # en lugar de desbordarse fuera de los márgenes.
    estilo_celda = ParagraphStyle(
        'celdaRecibo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.black
    )

    story = []

    def crear_bloque_recibo(etiqueta_copia):
        bloque = []

        # Encabezado del recibo
        bloque.append(Paragraph(f"<b>SISTEMA FUNERARIO - RECIBO DE PAGO</b> [{etiqueta_copia}]", styles['Heading2']))

        # Encabezado de datos.
        # El "Detalle" ocupa una línea completa (SPAN) para que aparezca
        # completo y no se desborde de los márgenes del recibo.
        info_header = [
            [f"N° Recibo: #{num_recibo}", f"Fecha: {fecha}"],
            [f"Titular: {nombre_titular}", f"Cédula: {cedula}"],
            [f"Contrato N°: {num_contrato}", Paragraph(f"Tipo: {tipo_contrato}", estilo_celda)],
            [Paragraph(f"Detalle: {cuota_info}", estilo_celda), ""]
        ]

        t_header = Table(info_header, colWidths=[270, 270])
        t_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f2f2f2")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Une las 2 columnas en la fila del Detalle (toda la línea)
            ('SPAN', (0, 3), (1, 3)),
            ('ALIGN', (0, 3), (-1, 3), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        bloque.append(t_header)
        bloque.append(Spacer(1, 10))

        # Detalle del Cobro
        detalle = [
            ["Tipo de Pago", "Monto Pagado (Bs.)", "Tasa BCV", "Monto (USD)"],
            [
                forma_pago,
                f"Bs. {monto_bs:,.2f}",
                f"Bs. {tasa_bcv:,.2f}",
                f"$ {monto_usd:,.2f}"
            ]
        ]

        if forma_pago in ["Transferencia", "Pago Móvil"]:
            detalle.append(["Banco Pagador", "Banco Receptor", "N° Operación", ""])
            detalle.append([
                banco_origen,
                banco_destino,
                num_operacion,
                ""
            ])

        t_detalle = Table(detalle, colWidths=[135, 135, 135, 135])
        t_detalle.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#7f8c8d")),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1f538d")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#f9f9f9")),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ]))

        bloque.append(t_detalle)
        bloque.append(Spacer(1, 20))

        # Firmas
        firmas = [
            ["___________________________", "___________________________"],
            ["Firma / Sello Caja", "Firma Conforme Cliente"]
        ]
        t_firmas = Table(firmas, colWidths=[270, 270])
        t_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        bloque.append(t_firmas)

        return bloque

    # Construir ORIGINAL
    story.extend(crear_bloque_recibo("ORIGINAL"))

    story.append(Spacer(1, 30))
    story.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -", styles['Normal']))
    story.append(Spacer(1, 30))

    # Construir COPIA
    story.extend(crear_bloque_recibo("COPIA"))

    c.build(story)

    return ruta_salida