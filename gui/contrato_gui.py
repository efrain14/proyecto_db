# =========================================================================
# MÓDULO DE GENERACIÓN DE CONTRATOS (CAVELA C.A.)
# =========================================================================
# Genera el contrato en PDF con 2 páginas:
#   Página 1: formulario con datos automáticos + datos del operario.
#   Página 2: cláusulas y condiciones (se imprime al reverso).
# =========================================================================
import os
import sys
import tempfile
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import customtkinter as ctk
from tkinter import messagebox, filedialog

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from xml.sax.saxutils import escape

from database.conexion import conectar

# Ruta opcional del logo: si existe "logo_cavela.png" en la raíz del
# proyecto, se usa; si no, se imprime el membrete solo con texto.
RUTA_LOGO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logo_cavela.png'))


# =========================================================================
# UTILIDADES
# =========================================================================

def _num_a_palabras(n):
    """Convierte un número entero a palabras en español (mayúsculas)."""
    unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO",
                "NUEVE", "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE",
                "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE", "VEINTE",
                "VEINTIUN", "VEINTIDOS", "VEINTITRES", "VEINTICUATRO", "VEINTICINCO",
                "VEINTISEIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"]
    decenas = ["", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
                "SEISCIENTOS", "SETESCIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

    if n == 0:
        return "CERO"
    if n == 100:
        return "CIEN"

    partes = []
    millones = n // 1000000
    if millones:
        partes.append("UN MILLON" if millones == 1 else _num_a_palabras(millones) + " MILLONES")
        n %= 1000000

    miles = n // 1000
    if miles:
        partes.append("MIL" if miles == 1 else _num_a_palabras(miles) + " MIL")
        n %= 1000

    if n:
        cent, resto = n // 100, n % 100
        if cent:
            partes.append(centenas[cent])
        if resto:
            if resto < 30:
                partes.append(unidades[resto])
            else:
                t = decenas[resto // 10]
                if resto % 10:
                    t += " Y " + unidades[resto % 10]
                partes.append(t)

    return " ".join(p for p in partes if p)


def monto_en_letras(monto):
    """Devuelve el monto en formato 'DOSCIENTOS BOLÍVARES CON 00/100'."""
    try:
        entero = int(round(float(monto)))
    except (TypeError, ValueError):
        return ""
    return f"{_num_a_palabras(entero)} BOLÍVARES"


def calcular_edad(fecha_str):
    try:
        fn = datetime.strptime(fecha_str, "%d/%m/%Y")
        h = datetime.now()
        return h.year - fn.year - ((h.month, h.day) < (fn.month, fn.day))
    except Exception:
        return ""


def _linea(v, guiones=25):
    """Devuelve el valor o una línea de guiones si está vacío (para llenar a mano)."""
    return str(v) if v else "_" * guiones


# =========================================================================
# CONSULTA DE DATOS DEL TITULAR Y SUS AFILIADOS
# =========================================================================

def consultar_datos_contrato(cedula):
    """Consulta titulares y familiares para armar el contrato."""
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cedula, nombres, apellidos, fecha_nacimiento, telefono, direccion,
               tipo_contrato, contrato_nuevo, fecha_inicio
        FROM titulares WHERE cedula = ?
    """, (cedula,))
    t = cursor.fetchone()

    if not t:
        conn.close()
        return None

    cursor.execute("""
        SELECT nombres, apellidos, cedula, parentesco, fecha_nacimiento
        FROM familiares WHERE titular_cedula = ? ORDER BY id ASC
    """, (cedula,))
    fam = cursor.fetchall()
    conn.close()

    tipo = t[6] or ""
    tipo_lower = tipo.lower()

    # PLAN A = solo velación | PLAN B = velación + entierro
    plan = "B" if "entierro" in tipo_lower else "A"
    cuota = 20.0 if "entierro" in tipo_lower else 10.0
    cuotas = 12 if "renovación" in tipo_lower or "renovacion" in tipo_lower else 24

    hoy = datetime.now()
    mes_sig = hoy.month + 1
    anno_sig = hoy.year
    if mes_sig > 12:
        mes_sig = 1
        anno_sig += 1

    return {
        "cedula": t[0],
        "titular": f"{(t[1] or '').title()} {(t[2] or '').title()}",
        "fecha_nac": t[3] or "",
        "edad": calcular_edad(t[3]),
        "telefono": t[4] or "",
        "direccion": t[5] or "",
        "tipo_contrato": tipo,
        "contrato_nuevo": t[7] or "",
        "plan": plan,
        "cuota": cuota,
        "cuotas": cuotas,
        "total": cuota * cuotas,
        "plazo": f"{cuotas} meses",
        "afiliados": fam,
        "fecha_emision": hoy.strftime("%d/%m/%Y"),
        "fecha_vencimiento": f"{min(hoy.day, 28):02d}/{mes_sig:02d}/{anno_sig}",
    }


# =========================================================================
# GENERADOR DEL PDF DEL CONTRATO (2 páginas)
# =========================================================================

def generar_contrato_pdf(d, ruta_destino):
    """
    Genera el PDF del contrato.
    d = diccionario con todos los datos (automáticos + del operario).

    NOTA TÉCNICA: la función P() NO escapa el texto porque recibe formato
    HTML intencional (<b>, <br/>, &nbsp;). Los DATOS VARIABLES se escapan
    con E() antes de insertarlos, para que ningún dato rompa el PDF.
    """
    doc = SimpleDocTemplate(
        ruta_destino, pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=28, bottomMargin=28
    )

    styles = getSampleStyleSheet()

    mini = ParagraphStyle('mini', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10)
    miniB = ParagraphStyle('miniB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10)
    miniC = ParagraphStyle('miniC', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, alignment=TA_CENTER)
    tit = ParagraphStyle('tit', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, alignment=TA_CENTER)
    sec = ParagraphStyle('sec', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER, textColor=colors.white)
    clau = ParagraphStyle('clau', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=13)

    def P(txt, st=mini):
        """Párrafo con formato HTML intencional (NO se escapa)."""
        return Paragraph(str(txt), st)

    def E(v):
        """Escapa solo los datos variables (nombres, cédulas, etc.)."""
        return escape(str(v))

    def linea(v, guiones=25):
        """Valor escapado o línea de guiones para llenar a mano."""
        return escape(str(v)) if v else "_" * guiones

    NEGRO = colors.black
    GRIS = colors.HexColor("#c0c0c0")
    story = []

    # =====================================================================
    # PÁGINA 1: FORMULARIO DEL CONTRATO
    # =====================================================================

    # --- Membrete: logo | datos empresa | caja NOTA ---
    if os.path.exists(RUTA_LOGO):
        logo_celda = RLImage(RUTA_LOGO, width=75, height=75)
    else:
        logo_celda = P("<b>CAVELA C.A.</b><br/>Capillas Velatorias Los Andes, C.A.", miniB)

    centro = P(
        "<b>CAPILLAS VELATORIAS LOS ANDES, C.A.</b><br/>"
        "RIF.: J-31355409-0<br/>"
        "Av. Universidad Casa N° 191-125, sector Naguanagua, Edo. Carabobo.<br/>"
        "Zona Postal 2005. Telfs.: 0241-866.6042 / 0424-457.7347",
        miniC
    )

    nota = P(
        "<b>NOTA:</b><br/>NO ES VALIDO COMO UN COMPROBANTE.<br/>"
        "NO ES UN RECIBO DE CAJA,<br/>NO ES UN RECIBO",
        miniC
    )

    t_membrete = Table([[logo_celda, centro, nota]], colWidths=[95, 315, 130])
    t_membrete.setStyle(TableStyle([
        ('BOX', (2, 0), (2, 0), 1, NEGRO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_membrete)
    story.append(Spacer(1, 6))

    # --- Número de contrato en rojo ---
    story.append(Paragraph(
        f'<font size="12"><b>CONTRATO&nbsp;&nbsp;&nbsp;<font color="red">N° {E(d["contrato_nuevo"])}</font></b></font>',
        ParagraphStyle('num', parent=styles['Normal'], alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 6))

    # --- Tabla superior: PLAN N° | INICIAL | PLAZO | CUOTAS ---
    t_plan = Table(
        [
            ["PLAN N°", "INICIAL", "PLAZO", "CUOTAS"],
            [d["contrato_nuevo"], f"${d['inicial']:,.2f}", d["plazo"], str(d["cuotas"])],
        ],
        colWidths=[135, 135, 135, 135]
    )
    t_plan.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.7, NEGRO),
        ('BACKGROUND', (0, 0), (-1, 0), GRIS),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_plan)

    # --- Texto de autorización (fijo) ---
    story.append(Table(
        [[P("Por medio de la presente autorizo a <b>CAPILLAS VELATORIAS LOS ANDES, C.A.</b>, para que me sean elaborados los documentos respectivos para, afiliarme al plan de cobertura familiar", miniC)]],
        colWidths=[540]
    ))
    story.append(Spacer(1, 6))

    # --- DATOS DEL COMPRADOR ---
    filas = [
        [P("DATOS DEL COMPRADOR", sec), '', '', ''],
        [P(f"Titular: <b>{E(d['titular'])}</b>"), '', '', ''],
        [P(f"Estado Civil: {linea(d['estado_civil'], 15)}"), '', P(f"C.I.: <b>{E(d['cedula'])}</b>"), P(f"Edad: {linea(d['edad'], 4)}")],
        [P(f"Nacionalidad: {linea(d['nacionalidad'], 12)}"), P(f"Profesión: {linea(d['profesion'], 15)}"), '', P(f"Fecha de Nacimiento: <b>{E(d['fecha_nac'])}</b>")],
        [P(f"Dirección de habitación: <b>{E(d['direccion'])}</b>"), '', '', ''],
        [P("", mini), '', '', ''],
        [P(f"Punto de referencia: {linea(d['punto_ref'], 60)}"), '', '', ''],
        [P(f"Nombre de la empresa: {linea(d['empresa'], 60)}"), '', '', ''],
        [P(f"Dirección de oficina o trabajo: {linea(d['dir_trabajo'], 55)}"), '', '', ''],
        [P("", mini), '', P(f"Departamento: {linea(d['departamento'], 15)}"), ''],
        [P(f"Teléfonos: <b>{E(d['telefono'])}</b>"), '', P(f"Telf. Trabajo: {linea(d['ext'], 6)}"), ''],
    ]

    t_datos = Table(filas, colWidths=[170, 170, 100, 100])
    t_datos.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.7, NEGRO),
        ('BACKGROUND', (0, 0), (-1, 0), GRIS),
        ('SPAN', (0, 0), (3, 0)),
        ('SPAN', (0, 1), (3, 1)),
        ('SPAN', (0, 2), (1, 2)),
        ('SPAN', (1, 3), (2, 3)),
        ('SPAN', (0, 4), (3, 4)),
        ('SPAN', (0, 5), (3, 5)),
        ('SPAN', (0, 6), (3, 6)),
        ('SPAN', (0, 7), (3, 7)),
        ('SPAN', (0, 8), (3, 8)),
        ('SPAN', (0, 9), (1, 9)),
        ('SPAN', (2, 9), (3, 9)),
        ('SPAN', (0, 10), (1, 10)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_datos)
    story.append(Spacer(1, 6))

    # --- AFILIADOS (8 filas automáticas) ---
    filas_af = [
        [P("A F I L I A D O S", sec), '', '', ''],
        [P("NOMBRE Y APELLIDO", miniB), P("C.I.", miniB), P("PARENTESCO", miniB), P("FECHA DE NACIMIENTO", miniB)],
    ]

    for i in range(8):
        if i < len(d["afiliados"]):
            f = d["afiliados"][i]
            filas_af.append([
                P(E(f"{(f[0] or '').title()} {(f[1] or '').title()}")),
                P(E(f[2] or "")),
                P(E((f[3] or '').title())),
                P(E(f[4] or "")),
            ])
        else:
            filas_af.append([P("", mini), P("", mini), P("", mini), P("", mini)])

    t_af = Table(filas_af, colWidths=[220, 100, 110, 110])
    t_af.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.7, NEGRO),
        ('BACKGROUND', (0, 0), (-1, 1), GRIS),
        ('SPAN', (0, 0), (3, 0)),
        ('ALIGN', (1, 1), (3, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_af)
    story.append(Spacer(1, 6))

    # --- COMPONENTES DE CADA SERVICIO (fijo) ---
    t_comp = Table([
        [P("COMPONENTES DE CADA SERVICIO", sec)],
        [P("Ataúd básico. Preparación de cuerpo por 24h. Traslado local. Carroza para sepelio. Servicio cafetería en capilla. Capilla a disposición o capilla en domicilio. Asesoría de diligencias de ley. ATENCIÓN EN EL MOMENTO DE LA EMERGENCIA.", miniC)],
    ], colWidths=[540])
    t_comp.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.7, NEGRO),
        ('BACKGROUND', (0, 0), (0, 0), GRIS),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 6))

    # --- CONDICIONES DE PAGO ---
    cantidad_letras = d.get("cantidad_letras") or (monto_en_letras(d.get("monto_bs")) if d.get("monto_bs") else "")

    filas_pago = [
        [P("CONDICIONES DE PAGO", sec), '', '', ''],
        [P(f"Recibimos de: <b>{E(d['titular'])}</b> &nbsp;&nbsp; C.I.: <b>{E(d['cedula'])}</b>"), '', '', ''],
        [P(f"La Cantidad de: {linea(cantidad_letras, 60)}"), '', '', ''],
        [P("", mini), '', P(f"<b>Bs. {linea(d.get('monto_bs'), 12)}</b>"), ''],
        [P(f"Por concepto de: {linea(d['por_concepto'], 55)}"), '', '', ''],
        [P(f"Costo del Plan: <b>${d['cuota']:.2f} mensuales</b> (Total del plan: ${d['total']:.2f})"), '', '', ''],
        [P(f"Forma de pago: {linea(d['forma_pago'], 20)}"), '', '', ''],
    ]

    t_pago = Table(filas_pago, colWidths=[170, 170, 100, 100])
    t_pago.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.7, NEGRO),
        ('BACKGROUND', (0, 0), (-1, 0), GRIS),
        ('SPAN', (0, 0), (3, 0)),
        ('SPAN', (0, 1), (3, 1)),
        ('SPAN', (0, 2), (3, 2)),
        ('SPAN', (0, 3), (1, 3)),
        ('SPAN', (0, 4), (3, 4)),
        ('SPAN', (0, 5), (3, 5)),
        ('SPAN', (0, 6), (3, 6)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_pago)
    story.append(Spacer(1, 6))

    # --- Tabla final: MONTO | CUOTAS | FECHAS | PLAN | FIRMA ---
    check_a = "[X]" if d["plan"] == "A" else "[ ]"
    check_b = "[X]" if d["plan"] == "B" else "[ ]"

    t_fin = Table([
        [P("MONTO", miniB), P("N° DE CUOTAS", miniB), P("FECHA DE EMISIÓN", miniB), P("FECHA DE VENCIMIENTO", miniB)],
        [P(f"${d['total']:.2f}"), P(str(d['cuotas'])), P(E(d['fecha_emision'])), P(E(d['fecha_vencimiento']))],
        [P("<b>TIPO DE PLAN:</b>"), P(f"{check_a} PLAN A &nbsp;&nbsp; {check_b} PLAN B"), '', P("<b>TITULAR AFILIADO:</b><br/><br/>______________________")],
    ], colWidths=[135, 135, 135, 135])
    t_fin.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.7, NEGRO),
        ('BACKGROUND', (0, 0), (-1, 0), GRIS),
        ('BACKGROUND', (0, 2), (0, 2), GRIS),
        ('SPAN', (1, 2), (2, 2)),
        ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_fin)

    # =====================================================================
    # PÁGINA 2: CLÁUSULAS Y CONDICIONES (reverso de la hoja)
    # =====================================================================
    story.append(PageBreak())

    if os.path.exists(RUTA_LOGO):
        logo2 = RLImage(RUTA_LOGO, width=75, height=75)
    else:
        logo2 = P("<b>CAVELA C.A.</b>", miniB)

    caja2 = P(
        "<b>CAPILLAS VELATORIAS LOS ANDES C.A.</b><br/>"
        "<b>J-313554090</b><br/>"
        "AV. UNIVERSIDAD DE NAGUANAGUA. DIAGONAL AL LUXOR. CASA 191-125<br/>"
        "SAN BLAS. DIST SAN BLAS. AV LARA. FRENTE C.C. LA PRIMERA PARADA<br/>"
        "0424-457.73.47 &nbsp; 0412-405.42.58 &nbsp; CAVELAC.A@GMAIL.COM",
        miniC
    )

    t_memb2 = Table([[logo2, caja2]], colWidths=[120, 420])
    t_memb2.setStyle(TableStyle([
        ('BOX', (1, 0), (1, 0), 1, NEGRO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_memb2)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>CLAUSULAS Y CONDICIONES PLAN (PPA)</b>", tit))
    story.append(Spacer(1, 10))

    clausulas = [
        "Solamente se podrá afiliar; MAMA, PAPA, HIJO hasta 20 años, CONYUGUE, HERMANO.",
        "Dicha cobertura, consiste en que para el momento del servicio o fallecimiento, el familiar o afiliado deberá cancelar el total de las cuotas pendientes.",
        "La cobertura es por 12 meses o 24 meses depende el plan y cuyo costo de mensualidad es por 10$ dólares o 20$ o su equivalente en moneda nacional. Para un total final de: el plan básico 240$ y el plan premium 20$",
        "La renovación es a los 24 meses.",
        "La cancelación será estrictamente por las oficinas ubicadas en Av: Universidad Naguanagua diagonal a Luxor o en Av: Lara sector San Blas al lado de cerámicas el morro.",
        "Todo servicio por accidente deberá esperar por el protocolo de las autoridades.",
        "Servicio a nivel regional solo en el Edo Carabobo.",
        "Los servicios certificados por COVID 19 o cualquier enfermedad infectocontagiosa, no podrá ser manipulado por nuestro personal.",
        "La cremación o gasto de servicio en cementerio municipal (FOSA) será exclusivo para los afiliados en el contrato, en el plan premium.",
        "Una vez que se use el servicio será renovado automático y sigue la cancelación habitual de las cuotas.",
        "Todo afiliado deberá tener sus cuotas al dia para la prestación del servicio según plan.",
        "Servicios de cremación no tienen remuneración de cofre ni otro entre similar.",
    ]

    for i, c in enumerate(clausulas, 1):
        story.append(Paragraph(f"{i}.&nbsp;&nbsp;{E(c)}", clau))
        story.append(Spacer(1, 6))

    # Componentes del servicio (página 2)
    comps = [
        "ATAUD",
        "TRASLADO LOCAL Y AL CEMENTERIO",
        "VELACION EN CAPILLAS AUTORIZADAS O DOMICILIO NIVEL REGIONAL POR 24H.",
        "PREPARACION BASICA DEL CUERPO",
        "ASESORIA EN DILIGENCIA DE LEY",
        "CREMACION DEL CUERPO O GASTOS MUNICIPALES DE FOSA. (Plan premium)",
    ]

    filas_c2 = [[P("<b>COMPONENTES DEL SERVICIO</b>", miniB)]]
    for c in comps:
        filas_c2.append([P(f"&nbsp;&nbsp;&nbsp;-&nbsp;&nbsp;{E(c)}", mini)])

    t_c2 = Table(filas_c2, colWidths=[500])
    t_c2.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, NEGRO),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(Spacer(1, 6))
    story.append(t_c2)

    doc.build(story)
    return ruta_destino


# =========================================================================
# VENTANA DEL CONTRATO (datos editables + guardar/imprimir)
# =========================================================================

def abrir_modulo_contrato(ventana_padre, cedula):
    """
    Abre la ventana para emitir el contrato de un titular.
    Los datos del sistema se cargan solos; el operario completa el resto.
    """
    datos_auto = consultar_datos_contrato(cedula)

    if not datos_auto:
        messagebox.showerror("No Encontrado", "No se localizó al titular para generar el contrato.")
        return

    pop = ctk.CTkToplevel(ventana_padre)
    pop.title(f"📄 Contrato - {datos_auto['titular']}")
    pop.geometry("760x640")
    pop.grab_set()

    # -----------------------------------------------------------------
    # Resumen automático (solo lectura)
    # -----------------------------------------------------------------
    frame_auto = ctk.CTkFrame(pop)
    frame_auto.pack(pady=8, padx=15, fill="x")

    ctk.CTkLabel(
        frame_auto,
        text=(
            f"Titular: {datos_auto['titular']}   |   C.I.: {datos_auto['cedula']}   |   Edad: {datos_auto['edad']}\n"
            f"Contrato N°: {datos_auto['contrato_nuevo']}   |   Plan {datos_auto['plan']} ({datos_auto['tipo_contrato']})\n"
            f"Cuota: ${datos_auto['cuota']:.2f}   |   Cuotas: {datos_auto['cuotas']}   |   Total: ${datos_auto['total']:.2f}   |   Afiliados: {len(datos_auto['afiliados'])}"
        ),
        font=("Arial", 11, "bold"),
        justify="left",
        text_color="#2ecc71"
    ).pack(pady=8, padx=10, anchor="w")

    # -----------------------------------------------------------------
    # Campos que completa el operario
    # -----------------------------------------------------------------
    frame_campos = ctk.CTkFrame(pop)
    frame_campos.pack(pady=5, padx=15, fill="both", expand=True)

    campos = {}

    defs = [
        ("estado_civil", "Estado Civil:", "", 0, 0),
        ("nacionalidad", "Nacionalidad:", "Venezolana", 0, 1),
        ("profesion", "Profesión:", "", 0, 2),
        ("punto_ref", "Punto de referencia:", "", 1, 0),
        ("empresa", "Nombre de la empresa:", "", 1, 1),
        ("departamento", "Departamento:", "", 1, 2),
        ("dir_trabajo", "Dirección de oficina o trabajo:", "", 2, 0),
        ("ext", "(Telf Trabajo):", "", 2, 1),
        ("forma_pago", "Forma de pago:", "Efectivo USD", 2, 2),
        ("inicial", "Inicial (USD):", str(datos_auto["cuota"]), 3, 0),
        ("monto_bs", "Monto Bs. (inicial):", "", 3, 1),
        ("por_concepto", "Por concepto de:", "Cuota inicial del plan de cobertura familiar", 3, 2),
        ("fecha_emision", "Fecha de emisión:", datos_auto["fecha_emision"], 4, 0),
        ("fecha_vencimiento", "Fecha de vencimiento:", datos_auto["fecha_vencimiento"], 4, 1),
    ]

    for clave, texto, defecto, r, c in defs:
        ctk.CTkLabel(frame_campos, text=texto, font=("Arial", 11, "bold")).grid(row=r * 2, column=c, padx=8, sticky="w")
        e = ctk.CTkEntry(frame_campos, width=220)
        if defecto:
            e.insert(0, defecto)
        e.grid(row=r * 2 + 1, column=c, padx=8, pady=(0, 6))
        campos[clave] = e

    # -----------------------------------------------------------------
    # Acciones: guardar PDF / imprimir / cerrar
    # -----------------------------------------------------------------
    def recolectar_datos():
        d = dict(datos_auto)
        for clave in [k for k, _, _, _, _ in defs]:
            d[clave] = campos[clave].get().strip()

        try:
            d["inicial"] = float((d["inicial"] or "0").replace(",", "."))
        except ValueError:
            d["inicial"] = datos_auto["cuota"]

        return d

    def guardar_pdf():
        d = recolectar_datos()

        ruta = filedialog.asksaveasfilename(
            title="Guardar Contrato",
            defaultextension=".pdf",
            initialfile=f"contrato_{d['contrato_nuevo']}.pdf",
            filetypes=[("Archivo PDF", "*.pdf"), ("Todos los archivos", "*.*")]
        )

        if not ruta:
            return

        try:
            generar_contrato_pdf(d, ruta)
            messagebox.showinfo("Contrato Generado", f"✅ Contrato guardado en:\n\n{ruta}")
            os.startfile(ruta)
        except PermissionError:
            messagebox.showerror("Error de Permisos", "No se pudo guardar el PDF. Intente otra ubicación.")
        except Exception as e:
            messagebox.showerror("Error al Generar Contrato", f"Ocurrió un error:\n\n{e}")

    def imprimir():
        d = recolectar_datos()

        ruta_temp = os.path.join(
            tempfile.gettempdir(),
            f"contrato_{d['contrato_nuevo']}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
        )

        try:
            generar_contrato_pdf(d, ruta_temp)
        except Exception as e:
            messagebox.showerror("Error de Impresión", f"No se pudo generar el contrato:\n\n{e}")
            return

        try:
            os.startfile(ruta_temp, "print")
            messagebox.showinfo("Imprimiendo", "🖨 Contrato enviado a la impresora.\n\nRecuerda imprimir a doble cara para que las cláusulas queden al reverso.")
        except Exception:
            os.startfile(ruta_temp)
            messagebox.showwarning("Impresión", "No se pudo imprimir directo.\nEl contrato se abrió en el visor: imprime con Ctrl + P (doble cara).")

    frame_bot = ctk.CTkFrame(pop, fg_color="transparent")
    frame_bot.pack(pady=10, padx=15, fill="x")

    ctk.CTkButton(frame_bot, text="💾 Guardar PDF", fg_color="#1f538d", font=("Arial", 12, "bold"), command=guardar_pdf).pack(side="left", padx=5)
    ctk.CTkButton(frame_bot, text="🖨 Imprimir", fg_color="#8e44ad", font=("Arial", 12, "bold"), command=imprimir).pack(side="left", padx=5)
    ctk.CTkButton(frame_bot, text="Cerrar", fg_color="#7f8c8d", command=pop.destroy).pack(side="right", padx=5)