import customtkinter as ctk
import os
import subprocess
import platform
from utils.pdf_generator import generar_recibo_pdf

def abrir_previsualizacion_recibo(parent_window, datos_pago):
    top = ctk.CTkToplevel(parent_window)
    top.title(f"Recibo N° {datos_pago['num_recibo']} - Verificación de Impresión")
    top.geometry("500x600")
    top.grab_set() # Forzar foco en la ventana emergente

    # Generar el PDF temporal
    pdf_path = generar_recibo_pdf(datos_pago)

    ctk.CTkLabel(top, text="✨ ¡Pago Registrado Exitosamente!", font=("Arial", 16, "bold"), text_color="#2ecc71").pack(pady=15)
    
    # Marco de Resumen
    frame_info = ctk.CTkFrame(top)
    frame_info.pack(pady=10, padx=20, fill="x")
    
    ctk.CTkLabel(frame_info, text=f"Recibo N°: {datos_pago['num_recibo']}", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=2)
    ctk.CTkLabel(frame_info, text=f"Cliente: {datos_pago['nombre_titular']}", font=("Arial", 12)).pack(anchor="w", padx=10, pady=2)
    ctk.CTkLabel(frame_info, text=f"Monto Pagado: Bs. {datos_pago['monto_bs']:.2f} (${datos_pago['monto_usd']:.2f})", font=("Arial", 12, "bold"), text_color="#f1c40f").pack(anchor="w", padx=10, pady=2)
    ctk.CTkLabel(frame_info, text=f"Método: {datos_pago['forma_pago']}", font=("Arial", 12)).pack(anchor="w", padx=10, pady=2)

    def imprimir_pdf():
        """Envía el PDF generado directamente a la impresora predeterminada según el SO."""
        if platform.system() == "Windows":
            os.startfile(pdf_path, "print")
        else:
            subprocess.run(["lp", pdf_path])

    def abrir_visor_pdf():
        """Abre el archivo PDF en el programa predeterminado del sistema."""
        if platform.system() == "Windows":
            os.startfile(pdf_path)
        else:
            subprocess.run(["xdg-open", pdf_path])

    # Botones de Acción
    ctk.CTkButton(top, text="🖨️ Imprimir Recibo (Original + Copia)", fg_color="#27ae60", font=("Arial", 13, "bold"), height=40, command=imprimir_pdf).pack(pady=10, padx=20, fill="x")
    ctk.CTkButton(top, text="📄 Abrir en Visor PDF", fg_color="#2980b9", command=abrir_visor_pdf).pack(pady=5, padx=20, fill="x")
    ctk.CTkButton(top, text="Cerrar", fg_color="#7f8c8d", command=top.destroy).pack(pady=15)