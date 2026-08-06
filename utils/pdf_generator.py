import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generar_recibo_pdf(datos_pago, ruta_salida="recibo_temp.pdf"):
    """
    Genera un PDF en formato Carta (Letter) que contiene en una sola hoja:
    - Mitad Superior: ORIGINAL
    - Línea divisoria de corte
    - Mitad Inferior: COPIA
    """
    c = SimpleDocTemplate(
        ruta_salida,
        pagesize=letter,
        rightMargin=30, leftMargin=30, topMargin=20, bottomMargin=20
    )
    styles = getSampleStyleSheet()
    story = []

    def crear_bloque_recibo(etiqueta_copia):
        bloque = []
        # Encabezado
        bloque.append(Paragraph(f"<b>SISTEMA FUNERARIO - RECIBO DE PAGO</b> [{etiqueta_copia}]", styles['Heading2']))
        
        info_header = [
            [f"N° Recibo: #{datos_pago['num_recibo']}", f"Fecha: {datos_pago['fecha']}"],
            [f"Titular: {datos_pago['nombre_titular']}", f"Cédula: {datos_pago['cedula']}"],
            [f"Contrato N°: {datos_pago['num_contrato']}", f"Detalle: {datos_pago.get('cuota_info', 'N/A')}"]
        ]
        t_header = Table(info_header, colWidths=[270, 270])
        t_header.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f2f2f2")),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        bloque.append(t_header)
        bloque.append(Spacer(1, 10))

        # Detalle del Cobro
        detalle = [
            ["Tipo de Pago", "Monto Pagado (Bs.)", "Tasa BCV", "Monto (USD)"],
            [
                datos_pago['forma_pago'],
                f"Bs. {datos_pago['monto_bs']:,.2f}",
                f"Bs. {datos_pago['tasa_bcv']:,.2f}",
                f"$ {datos_pago['monto_usd']:,.2f}"
            ]
        ]
        
        if datos_pago['forma_pago'] in ["Transferencia", "Pago Móvil"]:
            detalle.append(["Banco Pagador", "Banco Receptor", "N° Operación", ""])
            detalle.append([
                datos_pago['banco_origen'],
                datos_pago['banco_destino'],
                datos_pago['num_operacion'],
                ""
            ])

        t_detalle = Table(detalle, colWidths=[135, 135, 135, 135])
        t_detalle.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#7f8c8d")),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1f538d")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#f9f9f9")),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
        ]))
        bloque.append(t_detalle)
        bloque.append(Spacer(1, 20))
        
        # Firmas
        firmas = [
            ["___________________________", "___________________________"],
            ["Firma / Sello Caja", "Firma Conforme Cliente"]
        ]
        t_firmas = Table(firmas, colWidths=[270, 270])
        t_firmas.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
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