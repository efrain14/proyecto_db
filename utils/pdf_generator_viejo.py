import os
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


def _sanitizar_nombre_archivo(valor):
    """
    Limpia el número de recibo u otro texto para usarlo como nombre de archivo.
    Elimina caracteres inválidos en Windows.
    """
    texto = str(valor or "temp")

    caracteres_invalidos = [
        "\\",
        "/",
        ":",
        "*",
        "?",
        "\"",
        "<",
        ">",
        "|",
        " ",
        ",",
        ";",
    ]

    for caracter in caracteres_invalidos:
        texto = texto.replace(caracter, "_")

    return texto


def _float_seguro(valor):
    """
    Convierte un valor a float de forma segura.
    Si no es válido, devuelve 0.0.
    """
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _archivo_escribible(ruta):
    """
    Verifica si un archivo existente puede ser sobrescrito.
    Si está abierto en otro programa, normalmente devolverá False.
    """
    try:
        with open(ruta, "ab"):
            pass
        return True
    except OSError:
        return False


def generar_recibo_pdf(datos_pago, ruta_salida=None):
    """
    Genera un PDF en formato Carta (Letter) que contiene en una sola hoja:

    - Mitad Superior: ORIGINAL
    - Línea divisoria de corte
    - Mitad Inferior: COPIA

    Si no se indica ruta_salida, genera automáticamente un archivo único
    en la carpeta temporal del sistema para evitar bloqueos con recibo_temp.pdf.
    """

    # Si el módulo de vista pasa una ruta dentro del diccionario, se puede usar.
    if not ruta_salida:
        ruta_salida = datos_pago.get("ruta_pdf")

    num_recibo_txt = _sanitizar_nombre_archivo(datos_pago.get("num_recibo", "temp"))

    # Si no hay ruta, o si intentan usar el viejo recibo_temp.pdf,
    # se genera una ruta única automática.
    if not ruta_salida or os.path.basename(str(ruta_salida)).strip().lower() == "recibo_temp.pdf":
        ruta_salida = os.path.join(
            tempfile.gettempdir(),
            f"recibo_{num_recibo_txt}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
        )

    ruta_salida = os.path.abspath(ruta_salida)

    # Garantizar que la carpeta destino exista
    try:
        carpeta_destino = os.path.dirname(ruta_salida)
        if carpeta_destino:
            os.makedirs(carpeta_destino, exist_ok=True)
    except Exception:
        # Si no puede crear la carpeta, usa la carpeta temporal del sistema
        ruta_salida = os.path.join(
            tempfile.gettempdir(),
            f"recibo_{num_recibo_txt}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
        )

    # Si el archivo ya existe y está bloqueado, generar otro nombre
    if os.path.exists(ruta_salida) and not _archivo_escribible(ruta_salida):
        base, extension = os.path.splitext(ruta_salida)
        ruta_salida = f"{base}_{datetime.now().strftime('%H%M%S_%f')}{extension}"

    # Datos seguros
    num_recibo = datos_pago.get("num_recibo", "N/A")
    fecha = datos_pago.get("fecha", "")
    nombre_titular = datos_pago.get("nombre_titular", "N/A")
    cedula = datos_pago.get("cedula", "N/A")
    num_contrato = datos_pago.get("num_contrato", "N/A")
    cuota_info = datos_pago.get("cuota_info", "N/A")
    forma_pago = datos_pago.get("forma_pago", "N/A")

    monto_bs = _float_seguro(datos_pago.get("monto_bs"))
    monto_usd = _float_seguro(datos_pago.get("monto_usd"))
    tasa_bcv = _float_seguro(datos_pago.get("tasa_bcv"))

    banco_origen = datos_pago.get("banco_origen", "N/A")
    banco_destino = datos_pago.get("banco_destino", "N/A")
    num_operacion = datos_pago.get("num_operacion", "N/A")

    def construir_story():
        styles = getSampleStyleSheet()
        story = []

        def crear_bloque_recibo(etiqueta_copia):
            bloque = []

            # Encabezado
            bloque.append(
                Paragraph(
                    f"<b>SISTEMA FUNERARIO - RECIBO DE PAGO</b> [{etiqueta_copia}]",
                    styles['Heading2']
                )
            )

            info_header = [
                [
                    f"N° Recibo: #{num_recibo}",
                    f"Fecha: {fecha}"
                ],
                [
                    f"Titular: {nombre_titular}",
                    f"Cédula: {cedula}"
                ],
                [
                    f"Contrato N°: {num_contrato}",
                    f"Detalle: {cuota_info}"
                ]
            ]

            t_header = Table(info_header, colWidths=[270, 270])
            t_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f2f2f2")),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
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
            t_firmas.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER')
            ]))

            bloque.append(t_firmas)

            return bloque

        # Construir ORIGINAL
        story.extend(crear_bloque_recibo("ORIGINAL"))

        story.append(Spacer(1, 30))
        story.append(
            Paragraph(
                "- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -",
                styles['Normal']
            )
        )
        story.append(Spacer(1, 30))

        # Construir COPIA
        story.extend(crear_bloque_recibo("COPIA"))

        return story

    def intentar_generar(ruta_destino):
        documento = SimpleDocTemplate(
            ruta_destino,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=20,
            bottomMargin=20
        )

        documento.build(construir_story())

    # Intentar generar el PDF en la ruta seleccionada
    try:
        intentar_generar(ruta_salida)

    except (PermissionError, OSError):
        # Si la ruta original falla por permisos o bloqueo, usar carpeta temporal
        ruta_alternativa = os.path.join(
            tempfile.gettempdir(),
            f"recibo_{num_recibo_txt}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
        )

        intentar_generar(ruta_alternativa)
        ruta_salida = ruta_alternativa

    return ruta_salida