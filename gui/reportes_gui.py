# =========================================================================
# gui/reportes_gui.py (Archivo nuevo completo)
# =========================================================================
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def renderizar_grafico_cobranza(parent_frame, datos_meses):
    """
    Dibuja un gráfico de barras comparativo de cobros entre meses.
    datos_meses = {'Ene': 1200, 'Feb': 1500, 'Mar': 1800}
    """
    fig, ax = plt.subplots(figsize=(6, 3), dpi=100)
    fig.patch.set_facecolor('#2b2b2b') # Coincide con CustomTkinter Dark Mode
    ax.set_facecolor('#2b2b2b')

    meses = list(datos_meses.keys())
    monto_usd = list(datos_meses.values())

    barras = ax.bar(meses, monto_usd, color='#1f538d')
    ax.tick_params(colors='white')
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_title("Cobranza Total USD por Mes", color='white', fontsize=12, fontweight='bold')

    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)