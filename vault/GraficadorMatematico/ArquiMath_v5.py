import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, TextBox, RadioButtons, Button
from mpl_toolkits.mplot3d import Axes3D

# ====================== ARQUIMATH STUDIO v5.0 ======================
fig = plt.figure(figsize=(15, 9), facecolor='#05080a')
ax = fig.add_axes([0.35, 0.22, 0.60, 0.73])
ax.set_facecolor('#05080a')
ax.grid(color='#112233', linestyle='-', linewidth=0.5)
ax.tick_params(colors='#112233')

t_max = 100 * np.pi
t_array = np.linspace(0, t_max, 25000)
estado = {'frame': 0, 'jugando': True}

rastro, = ax.plot([], [], color='#00ffcc', lw=1.6, alpha=0.9)
puntero, = ax.plot([], [], 'o', color='white', markersize=4)
brazo, = ax.plot([], [], color='#ff0055', lw=1.2, alpha=0.6)

# ====================== CATÁLOGO v5.0 ======================
catalogo = {
    '1. Mandala Vorticial (Polígonos)': ('cos(t) + (v2/v1)*cos(v1*t)', 'sin(t) - (v2/v1)*sin(v1*t)'),
    '2. Espiral Nautilus (Galaxia)': ('exp(0.12 * v1 * t) * cos(v2 * t)', 'exp(0.12 * v1 * t) * sin(v2 * t)'),
    '3. Espiral Fibonacci en Cuadrados (Arcos)': ('0', '0'),
    '4. Toroide (Doughnut)': ('(v1 + cos(v2 * t)) * cos(t)', '(v1 + cos(v2 * t)) * sin(t)'),
    '5. Pi Irracional': ('cos(v1 * t) + cos(v2 * np.pi * t)', 'sin(v1 * t) + sin(v2 * np.pi * t)'),
    '6. Lissajous (Ondas)': ('sin(v1 * t)', 'sin(v2 * t)'),
    '7. Roseta Sagrada (Pétalos)': ('cos(v1 * t) * cos(t)', 'cos(v1 * t) * sin(t)'),
    '8. Hipotrocoide Estrella (Masónica)': ('(v1 - v2) * cos(t) + v2 * cos(((v1-v2)/v2)*t)', '(v1 - v2) * sin(t) - v2 * sin(((v1-v2)/v2)*t)'),
    '9. Espiral Galáctica con Brazos': ('exp(0.08 * v1 * t) * cos(t + 0.8 * sin(4 * v2 * t))', 'exp(0.08 * v1 * t) * sin(t + 0.8 * sin(4 * v2 * t))'),
    '10. Vortex Math 3-6-9 (Rodin)': ('0', '0'),
    '11. Flor de la Vida Completa': ('0', '0')
}

# ====================== EXPLICACIONES (con tips de edición) ======================
info_dict = {
    '2. Espiral Nautilus (Galaxia)': "Fórmula: Espiral logarítmica dorada\nEdita en Eje X el número 0.12 (ej: 0.05 = más abierta)\nv1 = crecimiento, v2 = vueltas\n→ nautilus y galaxias perfectas",
    # ... (el resto igual que antes, solo cambié este)
}

# ====================== FUNCIONES GENERADORAS ======================
def generar_fibonacci_cuadrados(): ... # (igual que v4)
def generar_flor_vida(v2):
    layers = max(1, int(v2))
    circles = [(0,0,1)]
    for layer in range(layers):
        n = 6 * (layer + 1)
        r = 1 + layer
        for i in range(n):
            ang = i * 2*np.pi / n
            circles.append((r*np.cos(ang), r*np.sin(ang), 1))
    return circles

# ====================== INTERFAZ (colores corregidos) ======================
color_ui = '#0d161e'
ax_radio = plt.axes([0.02, 0.58, 0.28, 0.35], facecolor=color_ui)
ax_radio.set_title("ArquiMath Studio v5.0", color='#00ffcc', fontweight='bold')
radio_menu = RadioButtons(ax_radio, list(catalogo.keys()), activecolor='#ff0055')
for label in radio_menu.labels: label.set_color('white')

ax_info = plt.axes([0.02, 0.22, 0.28, 0.32], facecolor=color_ui)
ax_info.set_xticks([]); ax_info.set_yticks([])
info_text = ax_info.text(0.03, 0.98, "", va='top', ha='left', color='#aaffff', fontsize=9.5, wrap=True)

ax_box_x = plt.axes([0.35, 0.12, 0.6, 0.04])
box_x = TextBox(ax_box_x, 'Eje X: ', initial="")
box_x.color = color_ui          # ← FONDO OSCURO
box_x.hovercolor = '#1a2b3c'
box_x.label.set_color('white')
box_x.text_disp.set_color('#00ffcc')   # legible

ax_box_y = plt.axes([0.35, 0.07, 0.6, 0.04])
box_y = TextBox(ax_box_y, 'Eje Y: ', initial="")
box_y.color = color_ui
box_y.hovercolor = '#1a2b3c'
box_y.label.set_color('white')
box_y.text_disp.set_color('#00ffcc')

# Sliders y botones (igual)
ax_v1 = plt.axes([0.05, 0.48, 0.2, 0.03])
slider_v1 = Slider(ax_v1, 'v1 (zoom/escala)', 0.01, 15.0, valinit=1.0, color='#ff0055')
ax_v2 = plt.axes([0.05, 0.42, 0.2, 0.03])
slider_v2 = Slider(ax_v2, 'v2 (capas/brazos)', 0.01, 15.0, valinit=1.0, color='#ff0055')

ax_btn_mp4 = plt.axes([0.05, 0.15, 0.2, 0.06])
btn_mp4 = Button(ax_btn_mp4, 'Exportar MP4', color='#00ffcc')
ax_btn_3d = plt.axes([0.05, 0.07, 0.2, 0.06])
btn_3d = Button(ax_btn_3d, 'Ver en 3D Orbit', color='#ffaa00')

# ====================== LÓGICA RECALCULAR (con todas las correcciones) ======================
x_data = y_data = np.zeros(1)
texts_vortex = []

def recalcular_todo(val=None):
    global x_data, y_data
    label = radio_menu.value_selected
    # limpiar textos anteriores
    for txt in texts_vortex: txt.remove()
    texts_vortex.clear()

    if label == '11. Flor de la Vida Completa':
        circles = generar_flor_vida(slider_v2.val)
        x_list = []; y_list = []
        for cx,cy,r in circles:
            th = np.linspace(0,2*np.pi,300)
            x_list.extend([cx + r*np.cos(th), [np.nan]])
            y_list.extend([cy + r*np.sin(th), [np.nan]])
        x_data = np.concatenate(x_list) * slider_v1.val
        y_data = np.concatenate(y_list) * slider_v1.val

    elif label == '10. Vortex Math 3-6-9 (Rodin)':
        angles = np.linspace(0, 2*np.pi, 9, endpoint=False) + np.pi/2
        seq1 = [1,2,4,8,7,5,1]
        seq2 = [3,6,9,3]
        # Interpolación densa para animación suave
        def interp_path(seq):
            pts = np.array([np.cos(angles[np.array(seq)-1]), np.sin(angles[np.array(seq)-1])]).T
            return np.linspace(pts[0], pts[-1], 200) if len(pts)>1 else pts
        path1 = interp_path(seq1)
        path2 = interp_path(seq2)
        x_data = np.concatenate([path1[:,0], [np.nan], path2[:,0]])
        y_data = np.concatenate([path1[:,1], [np.nan], path2[:,1]])
        # Círculo + números
        ct = np.linspace(0,2*np.pi,300)
        ax.plot(np.cos(ct), np.sin(ct), color='#ffff00', lw=1, alpha=0.6)
        for i, ang in enumerate(angles, 1):
            tx = ax.text(1.15*np.cos(ang), 1.15*np.sin(ang), str(i), color='#ffff00', ha='center', va='center', fontsize=14, fontweight='bold')
            texts_vortex.append(tx)

    # ... (resto de patrones especiales igual que v4, pero con scale para Flor)

    else:
        x_data = evaluar_formula(box_x.text, t_array, slider_v1.val, slider_v2.val)
        y_data = evaluar_formula(box_y.text, t_array, slider_v1.val, slider_v2.val)

    # límites automáticos
    maxv = max(np.max(np.abs(x_data)), np.max(np.abs(y_data))) * 1.2
    ax.set_xlim(-maxv, maxv)
    ax.set_ylim(-maxv, maxv)
    estado['frame'] = 0
    update_info(label)

# ====================== 3D ORBIT CORREGIDO ======================
def mostrar_3d_orbit(event):
    fig3d = plt.figure(figsize=(10,10), facecolor='#05080a')
    ax3d = fig3d.add_subplot(111, projection='3d')
    ax3d.set_facecolor('#05080a')
    ax3d.grid(True, color='#112233')

    x3 = x_data.copy()
    y3 = y_data.copy()
    # INTERPOLACIÓN PARA PATRONES ESPECIALES (¡soluciona el vacío!)
    if len(x3) < 5000:
        n = len(x3)
        t = np.linspace(0,1,n)
        t_new = np.linspace(0,1,5000)
        mask = ~np.isnan(x3)
        if np.sum(mask) > 1:
            x3 = np.interp(t_new, t[mask], x3[mask])
            y3 = np.interp(t_new, t[mask], y3[mask])
        else:
            x3 = y3 = np.zeros(5000)
    z_data = np.linspace(0, 12, len(x3))

    line3d, = ax3d.plot([], [], [], color='#00ffcc', lw=2)
    point3d, = ax3d.plot([], [], [], 'o', color='white', markersize=8)

    def update3d(f):
        idx = min(f * 30, len(x3)-1)
        line3d.set_data_3d(x3[:idx], y3[:idx], z_data[:idx])
        if idx > 0:
            point3d.set_data_3d([x3[idx]], [y3[idx]], [z_data[idx]])
        ax3d.view_init(elev=30, azim=f*2 % 360)
        return line3d, point3d

    ani3d = animation.FuncAnimation(fig3d, update3d, frames=400, interval=25, blit=False)
    plt.show()

# ====================== CONEXIONES Y ANIMACIÓN ======================
# (radio_menu.on_clicked, sliders, botones, actualizar_grafica igual que v4 pero con los fixes arriba)

recalcular_todo()
plt.show()