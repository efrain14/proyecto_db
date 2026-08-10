import customtkinter as ctk
from tkinter import messagebox
import os
import subprocess
import platform
import tempfile
import shutil
from datetime import datetime

from utils.pdf_generator import generar_recibo_pdf

# Lista para controlar ventanas de recibo abiertas
_ventanas_recibo_abiertas = []


def abrir_previsualizacion_recibo(parent_window, datos_pago):
    global _ventanas_recibo_abiertas

    # Cerrar ventanas anteriores de recibo para evitar acumulación
    for win in list(_ventanas_recibo_abiertas):
        try:
            if win.winfo_exists():
                win.destroy()
        except Exception:
            pass

        if win in _ventanas_recibo_abiertas:
            _ventanas_recibo_abiertas.remove(win)

    top = ctk.CTkToplevel(parent_window)
    top.title(f"Recibo N° {datos_pago.get('num_recibo', 'TEMP')} - Verificación de Impresión")
    top.geometry("520x620")
    top.grab_set()

    _ventanas_recibo_abiertas.append(top)

    # Generar un nombre de PDF único para evitar bloqueos con recibo_temp.pdf
    num_recibo_txt = str(datos_pago.get("num_recibo", "temp")).strip()
    num_recibo_txt = num_recibo_txt.replace("/", "-").replace("\\", "-").replace(" ", "_")

    archivo_destino = os.path.join(
        tempfile.gettempdir(),
        f"recibo_{num_recibo_txt}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    )

    # Se pasa la ruta deseada al generador.
    # IMPORTANTE:
    # Para que esto funcione completamente, generar_recibo_pdf debería aceptar
    # un segundo parámetro llamado ruta_pdf.
    datos_pago["ruta_pdf"] = archivo_destino

    pdf_path = None
    error_pdf = None

    try:
        try:
            # Intento ideal: el generador acepta ruta destino
            pdf_path = generar_recibo_pdf(datos_pago, archivo_destino)
        except TypeError:
            # Compatibilidad con versión vieja que solo acepta datos_pago
            pdf_generado = generar_recibo_pdf(datos_pago)

            if pdf_generado and os.path.exists(pdf_generado):
                try:
                    # Intentamos copiarlo a un archivo único
                    shutil.copy2(pdf_generado, archivo_destino)
                    pdf_path = archivo_destino
                except Exception:
                    pdf_path = pdf_generado
            else:
                pdf_path = pdf_generado

    except Exception as e:
        error_pdf = str(e)
        pdf_path = None

    # Validación final del PDF
    if not error_pdf:
        if not pdf_path and os.path.exists(archivo_destino):
            pdf_path = archivo_destino

        if pdf_path and not os.path.exists(pdf_path):
            error_pdf = "El archivo PDF indicado no existe."
            pdf_path = None

        if not pdf_path:
            error_pdf = "No se pudo generar el archivo PDF."

    # Título superior
    if error_pdf:
        ctk.CTkLabel(
            top,
            text="⚠️ Pago registrado, pero hubo un problema con el PDF",
            font=("Arial", 15, "bold"),
            text_color="#e67e22"
        ).pack(pady=15, padx=20)

        ctk.CTkLabel(
            top,
            text=error_pdf,
            font=("Arial", 11),
            text_color="#e74c3c",
            wraplength=440,
            justify="left"
        ).pack(pady=(0, 10), padx=20)
    else:
        ctk.CTkLabel(
            top,
            text="✨ ¡Pago Registrado Exitosamente!",
            font=("Arial", 16, "bold"),
            text_color="#2ecc71"
        ).pack(pady=15)

    # Marco de Resumen
    frame_info = ctk.CTkFrame(top)
    frame_info.pack(pady=10, padx=20, fill="x")

    ctk.CTkLabel(
        frame_info,
        text=f"Recibo N°: #{datos_pago.get('num_recibo', 'N/A')}",
        font=("Arial", 12, "bold")
    ).pack(anchor="w", padx=10, pady=2)

    ctk.CTkLabel(
        frame_info,
        text=f"Cliente: {datos_pago.get('nombre_titular', 'N/A')}",
        font=("Arial", 12)
    ).pack(anchor="w", padx=10, pady=2)

    if datos_pago.get('cuota_info'):
        ctk.CTkLabel(
            frame_info,
            text=f"Detalle: {datos_pago['cuota_info']}",
            font=("Arial", 11, "italic"),
            text_color="#3498db"
        ).pack(anchor="w", padx=10, pady=2)

    ctk.CTkLabel(
        frame_info,
        text=f"Monto Pagado: Bs. {datos_pago.get('monto_bs', 0):,.2f} (${datos_pago.get('monto_usd', 0):.2f})",
        font=("Arial", 12, "bold"),
        text_color="#f1c40f"
    ).pack(anchor="w", padx=10, pady=2)

    ctk.CTkLabel(
        frame_info,
        text=f"Método: {datos_pago.get('forma_pago', 'N/A')}",
        font=("Arial", 12)
    ).pack(anchor="w", padx=10, pady=2)

    ctk.CTkLabel(
        frame_info,
        text=f"Archivo PDF: {pdf_path if pdf_path else 'No generado'}",
        font=("Arial", 10),
        text_color="#95a5a6",
        wraplength=440,
        justify="left"
    ).pack(anchor="w", padx=10, pady=2)

    def imprimir_pdf():
        """Envía el PDF generado directamente a la impresora predeterminada según el SO."""
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning(
                "PDF no disponible",
                "No se puede imprimir porque el archivo PDF no fue generado."
            )
            return

        try:
            if platform.system() == "Windows":
                os.startfile(pdf_path, "print")
            else:
                subprocess.run(["lp", pdf_path])
        except Exception as e:
            messagebox.showerror("Error al imprimir", f"No se pudo imprimir el PDF:\n{e}")

    def abrir_visor_pdf():
        """Abre el archivo PDF en el programa predeterminado del sistema."""
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning(
                "PDF no disponible",
                "No se puede abrir porque el archivo PDF no fue generado."
            )
            return

        try:
            if platform.system() == "Windows":
                os.startfile(pdf_path)
            else:
                subprocess.run(["xdg-open", pdf_path])
        except Exception as e:
            messagebox.showerror("Error al abrir PDF", f"No se pudo abrir el PDF:\n{e}")

    def cerrar():
        try:
            top.destroy()
        except Exception:
            pass

        if top in _ventanas_recibo_abiertas:
            _ventanas_recibo_abiertas.remove(top)

    estado_botones = "normal" if pdf_path and os.path.exists(pdf_path) else "disabled"

    ctk.CTkButton(
        top,
        text="🖨️ Imprimir Recibo (Original + Copia)",
        fg_color="#27ae60",
        font=("Arial", 13, "bold"),
        height=40,
        state=estado_botones,
        command=imprimir_pdf
    ).pack(pady=10, padx=20, fill="x")

    ctk.CTkButton(
        top,
        text="📄 Abrir en Visor PDF",
        fg_color="#2980b9",
        state=estado_botones,
        command=abrir_visor_pdf
    ).pack(pady=5, padx=20, fill="x")

    ctk.CTkButton(
        top,
        text="Cerrar",
        fg_color="#7f8c8d",
        command=cerrar
    ).pack(pady=15)

    top.protocol("WM_DELETE_WINDOW", cerrar)