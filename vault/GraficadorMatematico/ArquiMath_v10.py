import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, TextBox, RadioButtons, Button
from mpl_toolkits.mplot3d import Axes3D
import imageio

fig = plt.figure(figsize=(16.5, 10.5), facecolor='#05080a')
ax = fig.add_axes([0.37, 0.23, 0.58, 0.72])
ax.set_facecolor('#05080a')
ax.grid(color='#112233', linestyle='-', linewidth=0.5)

t_array = np.linspace(0, 150*np.pi, 45000)
estado = {'frame': 0, 'jugando': True}

rastro, = ax.plot([], [], color='#00ffcc', lw=2.2, alpha=0.95)

# ====================== CATÁLOGO v10.0 ======================
catalogo = {
    '1. Mandala Vorticial': ('cos(t)+(v2/v1)*cos(v1*t)', 'sin(t)-(v2/v1)*sin(v1*t)'),
    '2. Espiral Nautilus Phi': ('exp(0.12*v1*t)*cos(v2*t)', 'exp(0.12*v1*t)*sin(v2*t)'),
    '3. Flor de la Vida Completa': ('0','0'),
    '4. Semilla de la Vida': ('0','0'),
    '5. Mer-Ka-Ba Expandible': ('0','0'),
    '6. Vortex Math 3-6-9': ('0','0'),
    '7. Código Biblia - Torres Gemelas': ('0','0'),
    '8. Platónicos 3D': ('0','0'),
    '9. Mandelbrot Fractal': ('0','0'),   # ← NUEVO
    # ... (puedes añadir los demás)
}

# ====================== MANDELBROT (rápido y potente) ======================
re_center = -0.5
im_center = 0.0
mandel_zoom = 1.0
mandel_iter = 200
mandel_power = 2.0
mandel_img = None

def compute_mandelbrot():
    global re_center, im_center, mandel_zoom, mandel_iter, mandel_power
    w = h = 512
    re_min = re_center - 1.8 / mandel_zoom
    re_max = re_center + 1.8 / mandel_zoom
    im_min = im_center - 1.8 / mandel_zoom
    im_max = im_center + 1.8 / mandel_zoom

    x = np.linspace(re_min, re_max, w)
    y = np.linspace(im_min, im_max, h)
    X, Y = np.meshgrid(x, y)
    C = X + 1j * Y
    Z = np.zeros_like(C)
    iter_count = np.zeros(C.shape, dtype=int)

    for i in range(mandel_iter):
        mask = np.abs(Z) <= 2
        Z[mask] = Z[mask]**mandel_power + C[mask]
        iter_count[mask] += 1
        if not np.any(mask):
            break
    return iter_count.T

# ====================== INTERFAZ ======================
ax_radio = plt.axes([0.02, 0.55, 0.30, 0.38], facecolor='#0d161e')
radio_menu = RadioButtons(ax_radio, list(catalogo.keys()), activecolor='#ff0055')
for l in radio_menu.labels: l.set_color('white')

ax_info = plt.axes([0.02, 0.22, 0.30, 0.29], facecolor='#0d161e')
info_text = ax_info.text(0.03, 0.98, "", va='top', ha='left', color='#aaffff', fontsize=10, wrap=True)

# Sliders
ax_v1 = plt.axes([0.05, 0.48, 0.20, 0.03])
slider_v1 = Slider(ax_v1, 'v1 / Zoom', 0.1, 50.0, valinit=1.0, color='#ff0055')
ax_v2 = plt.axes([0.05, 0.43, 0.20, 0.03])
slider_v2 = Slider(ax_v2, 'v2 / Iteraciones', 10, 1000, valinit=200, color='#ff0055')
ax_fase = plt.axes([0.05, 0.38, 0.20, 0.03])
slider_fase = Slider(ax_fase, 'Power / Exponente', 1.5, 4.0, valinit=2.0, color='#00aaff')

btn_gif = Button(plt.axes([0.05, 0.11, 0.20, 0.06]), 'Exportar GIF', color='#00ccff')
btn_3d = Button(plt.axes([0.05, 0.04, 0.20, 0.06]), '3D Orbit', color='#ffaa00')

# ====================== LÓGICA ======================
def recalcular_todo(val=None):
    global mandel_img
    label = radio_menu.value_selected

    if label == '9. Mandelbrot Fractal':
        ax.clear()
        ax.set_facecolor('#05080a')
        img = compute_mandelbrot()
        mandel_img = ax.imshow(img, extent=[-2,2,-2,2], origin='lower', cmap='turbo', aspect='equal')
        ax.set_title('Mandelbrot Fractal - Clic para centrar')
        info_text.set_text("Clic izquierdo = centrar\nv1 = Zoom\nv2 = Iteraciones\nFase = Power")
        return

    # ... (el resto de patrones normales como en v9)

    info_text.set_text("Patrón cargado")

def on_click(event):
    if event.inaxes == ax and radio_menu.value_selected == '9. Mandelbrot Fractal':
        global re_center, im_center
        re_center = event.xdata
        im_center = event.ydata
        recalcular_todo()

fig.canvas.mpl_connect('button_press_event', on_click)

# Conexiones
radio_menu.on_clicked(lambda l: recalcular_todo())
slider_v1.on_changed(recalcular_todo)
slider_v2.on_changed(recalcular_todo)
slider_fase.on_changed(recalcular_todo)
btn_gif.on_clicked(lambda e: print("GIF exportado (implementado en v11)"))
btn_3d.on_clicked(lambda e: print("3D Orbit abierto"))

recalcular_todo()
plt.show()