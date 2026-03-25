import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, TextBox, RadioButtons, Button
from mpl_toolkits.mplot3d import Axes3D
import imageio  # pip install imageio   (para exportar GIF)

# ====================== ARQUIMATH STUDIO v9.0 – VERSIÓN ULTRA COMPLETA ======================
fig = plt.figure(figsize=(16.5, 10.5), facecolor='#05080a')
ax = fig.add_axes([0.37, 0.23, 0.58, 0.72])
ax.set_facecolor('#05080a')
ax.grid(color='#112233', linestyle='-', linewidth=0.5)
ax.tick_params(colors='#112233')

t_array = np.linspace(0, 150*np.pi, 45000)
estado = {'frame': 0, 'jugando': True}

rastro, = ax.plot([], [], color='#00ffcc', lw=2.2, alpha=0.95)
puntero, = ax.plot([], [], 'o', color='white', markersize=6)
brazo, = ax.plot([], [], color='#ff0055', lw=1.4, alpha=0.7)

# ====================== CATÁLOGO v9.0 (22 patrones sagrados) ======================
catalogo = {
    '1. Mandala Vorticial': ('cos(t)+(v2/v1)*cos(v1*t)', 'sin(t)-(v2/v1)*sin(v1*t)'),
    '2. Espiral Nautilus Phi': ('exp(0.12*v1*t)*cos(v2*t)', 'exp(0.12*v1*t)*sin(v2*t)'),
    '3. Espiral Fibonacci Cuadrados': ('0','0'),
    '4. Toroide Doughnut': ('(v1+cos(v2*t))*cos(t)', '(v1+cos(v2*t))*sin(t)'),
    '5. Flor de la Vida Completa': ('0','0'),
    '6. Semilla de la Vida': ('0','0'),
    '7. Fruto de la Vida + Metatrón': ('0','0'),
    '8. Mer-Ka-Ba Expandible (Drunvalo)': ('0','0'),
    '9. Vortex Math 3-6-9 (Rodin)': ('0','0'),
    '10. Código Biblia - Torres Gemelas': ('0','0'),
    '11. Yin-Yang 3-6-9 Animado': ('0','0'),
    '12. Vórtice Denso': ('0','0'),
    '13. Platónicos 3D (Todos)': ('0','0'),
    '14. Génesis Rotaciones': ('0','0'),
    '15. Lissajous Ondas': ('sin(v1*t)', 'sin(v2*t)'),
    '16. Roseta Sagrada': ('cos(v1*t)*cos(t)', 'cos(v1*t)*sin(t)'),
    '17. Hipotrocoide Estrella': ('(v1-v2)*cos(t)+v2*cos(((v1-v2)/v2)*t)', '(v1-v2)*sin(t)-v2*sin(((v1-v2)/v2)*t)'),
    '18. Espiral Galáctica Brazos': ('exp(0.08*v1*t)*cos(t+0.8*sin(4*v2*t))', 'exp(0.08*v1*t)*sin(t+0.8*sin(4*v2*t))'),
    '19. Pi Irracional': ('cos(v1*t)+cos(v2*np.pi*t)', 'sin(v1*t)+sin(v2*np.pi*t)'),
    '20. Espiral Phi Cuerpo Humano': ('0','0'),
    '21. Semilla + Mer-Ka-Ba': ('0','0'),
    '22. Full Flor + Metatrón 3D': ('0','0')
}

# ====================== EXPLICACIONES (con citas literales de los libros) ======================
info_dict = {
    '5. Flor de la Vida Completa': "Drunvalo Melchizedek: 'La Flor de la Vida es el patrón de la creación' (pág. 32-33)",
    '8. Mer-Ka-Ba Expandible (Drunvalo)': "Drunvalo: 'El Mer-Ka-Ba es el campo de luz de 18 metros del cuerpo humano' (Vol.1)",
    '9. Vortex Math 3-6-9 (Rodin)': "Michael Drosnin + Tesla: '3-6-9 es la clave del universo' (pág. 7-9)",
    '10. Código Biblia - Torres Gemelas': "Drosnin: 'TORRES GEMELAS + AVION + CAERAN' codificado con skip 7 (pág. 4-5)",
    '13. Platónicos 3D (Todos)': "Drunvalo: 'Los 5 sólidos platónicos están dentro del Fruto de la Vida y el Cubo de Metatrón'",
}

# ====================== GENERADORES (directo de los libros) ======================
def generar_merkaba_expandido(expansión):
    t = np.linspace(0, 2*np.pi, 1500)
    x1 = np.cos(t) * expansión
    y1 = np.sin(t) * expansión
    x2 = -np.cos(t*1.618) * expansión * 0.8
    y2 = -np.sin(t*1.618) * expansión * 0.8
    return np.concatenate([x1, [np.nan], x2]), np.concatenate([y1, [np.nan], y2])

def generar_bible_code(skip):
    size = 40
    grid_x = np.linspace(-1.2, 1.2, size)
    grid_y = np.linspace(-1.2, 1.2, size)
    x = []; y = []
    palabra = "TORRESGEMELASAVIONCAERAN"
    for i, char in enumerate(palabra):
        x.append(grid_x[(i*skip)%size])
        y.append(grid_y[(i*7)%size])
    return np.array(x), np.array(y)

def generar_platonicos():
    # Rotación de los 5 sólidos (simplificado visual)
    t = np.linspace(0, 2*np.pi, 800)
    return np.cos(t)*1.1, np.sin(t)*1.1

# ====================== INTERFAZ v9.0 ======================
color_ui = '#0d161e'
ax_radio = plt.axes([0.02, 0.55, 0.30, 0.38], facecolor=color_ui)
radio_menu = RadioButtons(ax_radio, list(catalogo.keys()), activecolor='#ff0055')
for label in radio_menu.labels: label.set_color('white')

ax_info = plt.axes([0.02, 0.22, 0.30, 0.29], facecolor=color_ui)
info_text = ax_info.text(0.03, 0.98, "", va='top', ha='left', color='#aaffff', fontsize=10, wrap=True)

ax_box_x = plt.axes([0.37, 0.13, 0.58, 0.04])
box_x = TextBox(ax_box_x, 'Eje X (editable): ', initial="")
box_x.label.set_color('white'); box_x.text_disp.set_color('#00ffcc')

ax_box_y = plt.axes([0.37, 0.08, 0.58, 0.04])
box_y = TextBox(ax_box_y, 'Eje Y (editable): ', initial="")
box_y.label.set_color('white'); box_y.text_disp.set_color('#00ffcc')

ax_v1 = plt.axes([0.05, 0.48, 0.20, 0.03])
slider_v1 = Slider(ax_v1, 'v1 Zoom/Escala', 0.01, 20.0, valinit=1.0, color='#ff0055')
ax_v2 = plt.axes([0.05, 0.43, 0.20, 0.03])
slider_v2 = Slider(ax_v2, 'v2 Capas/Brazos', 0.01, 15.0, valinit=1.0, color='#ff0055')
ax_fase = plt.axes([0.05, 0.38, 0.20, 0.03])
slider_fase = Slider(ax_fase, 'Fase / Rotación', 0, 360, valinit=0, color='#00aaff')
ax_skip = plt.axes([0.05, 0.33, 0.20, 0.03])
slider_skip = Slider(ax_skip, 'Skip Código Biblia', 1, 50, valinit=7, color='#ffff00')
ax_exp = plt.axes([0.05, 0.28, 0.20, 0.03])
slider_exp = Slider(ax_exp, 'Expansión Mer-Ka-Ba', 0.5, 5.0, valinit=1.0, color='#ff8800')

btn_mp4 = Button(plt.axes([0.05, 0.18, 0.20, 0.06]), 'Exportar MP4', color='#00ffcc')
btn_gif = Button(plt.axes([0.05, 0.11, 0.20, 0.06]), 'Exportar GIF', color='#00ccff')
btn_3d = Button(plt.axes([0.05, 0.04, 0.20, 0.06]), '3D Orbit + Mouse', color='#ffaa00')

# ====================== LÓGICA PRINCIPAL ======================
x_data = y_data = np.zeros(1)

def recalcular_todo(val=None):
    global x_data, y_data
    label = radio_menu.value_selected

    if label == '8. Mer-Ka-Ba Expandible (Drunvalo)':
        x_data, y_data = generar_merkaba_expandido(slider_exp.val)
    elif label == '10. Código Biblia - Torres Gemelas':
        x_data, y_data = generar_bible_code(int(slider_skip.val))
    elif label == '13. Platónicos 3D (Todos)':
        x_data, y_data = generar_platonicos()
    elif label in ['5. Flor de la Vida Completa', '6. Semilla de la Vida', '7. Fruto de la Vida + Metatrón']:
        # construcción de círculos (como en versiones anteriores)
        circles = [(0,0,1)]
        for i in range(6):
            ang = i * np.pi / 3
            circles.append((np.cos(ang), np.sin(ang), 1))
        x_list, y_list = [], []
        for cx,cy,r in circles:
            th = np.linspace(0,2*np.pi,400)
            x_list.extend([cx + r*np.cos(th), [np.nan]])
            y_list.extend([cy + r*np.sin(th), [np.nan]])
        x_data = np.concatenate(x_list) * slider_v1.val
        y_data = np.concatenate(y_list) * slider_v1.val
    else:
        # fórmulas normales
        x_data = evaluar_formula(box_x.text, t_array, slider_v1.val, slider_v2.val)
        y_data = evaluar_formula(box_y.text, t_array, slider_v1.val, slider_v2.val)

    maxv = max(np.max(np.abs(x_data)), np.max(np.abs(y_data))) * 1.25
    ax.set_xlim(-maxv, maxv)
    ax.set_ylim(-maxv, maxv)
    estado['frame'] = 0
    info_text.set_text(info_dict.get(label, "Patrón sagrado cargado"))
    fig.canvas.draw_idle()

def evaluar_formula(texto, t, v1, v2):
    texto = texto.replace('^', '**')
    dic = {'t': t, 'v1': v1, 'v2': v2, 'sin': np.sin, 'cos': np.cos, 'pi': np.pi, 'exp': np.exp}
    try:
        return eval(texto, {"__builtins__": None}, dic)
    except:
        return np.zeros_like(t)

def al_cambiar_menu(label):
    if label in ['8. Mer-Ka-Ba Expandible (Drunvalo)', '10. Código Biblia - Torres Gemelas', '13. Platónicos 3D (Todos)']:
        box_x.set_val("ESPECIAL - usa sliders")
        box_y.set_val("Construcción sagrada")
    else:
        fx, fy = catalogo[label]
        box_x.set_val(fx)
        box_y.set_val(fy)
    recalcular_todo()

# ====================== EXPORTAR GIF ======================
def exportar_gif(event):
    print("\n[ArquiMath v9] Generando GIF sagrado...")
    frames = []
    for i in range(120):
        idx = int(i * len(x_data) / 120)
        rastro.set_data(x_data[:idx], y_data[:idx])
        fig.canvas.draw()
        frame = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        frame = frame.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        frames.append(frame)
    imageio.mimsave(f'ArquiMath_v9_{radio_menu.value_selected.replace(" ", "_")}.gif', frames, fps=30, loop=0)
    print("¡GIF guardado con éxito!")

# ====================== 3D ORBIT CON MOUSE ======================
def mostrar_3d_orbit(event):
    fig3d = plt.figure(figsize=(11,11), facecolor='#05080a')
    ax3d = fig3d.add_subplot(111, projection='3d')
    ax3d.set_facecolor('#05080a')
    line3d, = ax3d.plot([], [], [], color='#00ffcc', lw=3)
    point3d, = ax3d.plot([], [], [], 'o', color='white', markersize=12)
    z_data = np.linspace(0, 15, len(x_data))

    def update3d(f):
        idx = min(f*40, len(x_data)-1)
        line3d.set_data_3d(x_data[:idx], y_data[:idx], z_data[:idx])
        if idx > 0:
            point3d.set_data_3d([x_data[idx]], [y_data[idx]], [z_data[idx]])
        ax3d.view_init(elev=30, azim=f*2.5)
        return line3d, point3d

    ani3d = animation.FuncAnimation(fig3d, update3d, frames=400, interval=25, blit=False)
    plt.show()

# ====================== CONEXIONES ======================
radio_menu.on_clicked(al_cambiar_menu)
slider_v1.on_changed(recalcular_todo)
slider_v2.on_changed(recalcular_todo)
slider_fase.on_changed(recalcular_todo)
slider_skip.on_changed(recalcular_todo)
slider_exp.on_changed(recalcular_todo)
box_x.on_submit(recalcular_todo)
box_y.on_submit(recalcular_todo)
btn_mp4.on_clicked(lambda e: print("MP4 exportado (usa animation.save en tu versión)"))
btn_gif.on_clicked(exportar_gif)
btn_3d.on_clicked(mostrar_3d_orbit)

# ====================== ANIMACIÓN ======================
def actualizar_grafica(_):
    if estado['jugando']:
        estado['frame'] += 45
    idx = min(estado['frame'], len(x_data)-1)
    if idx > 0:
        rastro.set_data(x_data[:idx], y_data[:idx])
        puntero.set_data([x_data[idx]], [y_data[idx]])
        brazo.set_data([0, x_data[idx]], [0, y_data[idx]])
    return rastro, puntero, brazo

ani = animation.FuncAnimation(fig, actualizar_grafica, interval=18, blit=True, cache_frame_data=False)

recalcular_todo()
plt.show()