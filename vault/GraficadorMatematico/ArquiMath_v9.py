import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, TextBox, RadioButtons, Button
from mpl_toolkits.mplot3d import Axes3D
import imageio   # pip install imageio

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

# ====================== CATÁLOGO v9.0 ======================
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
    '14. Lissajous Ondas': ('sin(v1*t)', 'sin(v2*t)'),
    '15. Roseta Sagrada': ('cos(v1*t)*cos(t)', 'cos(v1*t)*sin(t)'),
    '16. Hipotrocoide Estrella': ('(v1-v2)*cos(t)+v2*cos(((v1-v2)/v2)*t)', '(v1-v2)*sin(t)-v2*sin(((v1-v2)/v2)*t)'),
    '17. Espiral Galáctica Brazos': ('exp(0.08*v1*t)*cos(t+0.8*sin(4*v2*t))', 'exp(0.08*v1*t)*sin(t+0.8*sin(4*v2*t))'),
    '18. Pi Irracional': ('cos(v1*t)+cos(v2*np.pi*t)', 'sin(v1*t)+sin(v2*np.pi*t)'),
}

# ====================== GENERADORES ======================
def generar_merkaba(exp):
    t = np.linspace(0, 2*np.pi, 1500)
    x1 = np.cos(t) * exp
    y1 = np.sin(t) * exp
    x2 = -np.cos(t*1.618) * exp * 0.85
    y2 = -np.sin(t*1.618) * exp * 0.85
    return np.concatenate([x1, [np.nan], x2]), np.concatenate([y1, [np.nan], y2])

def generar_bible_code(skip):
    size = 45
    x = np.linspace(-1.3, 1.3, size)
    y = np.linspace(-1.3, 1.3, size)
    palabra = "TORRESGEMELASAVIONCAERAN"
    xs = [x[(i*skip)%size] for i in range(len(palabra))]
    ys = [y[(i*7)%size] for i in range(len(palabra))]
    return np.array(xs), np.array(ys)

# ====================== INTERFAZ ======================
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
slider_v1 = Slider(ax_v1, 'v1 Zoom', 0.01, 20.0, valinit=1.0, color='#ff0055')
ax_v2 = plt.axes([0.05, 0.43, 0.20, 0.03])
slider_v2 = Slider(ax_v2, 'v2 Capas', 0.01, 15.0, valinit=1.0, color='#ff0055')
ax_fase = plt.axes([0.05, 0.38, 0.20, 0.03])
slider_fase = Slider(ax_fase, 'Fase', 0, 360, valinit=0, color='#00aaff')
ax_skip = plt.axes([0.05, 0.33, 0.20, 0.03])
slider_skip = Slider(ax_skip, 'Skip Biblia', 1, 50, valinit=7, color='#ffff00')
ax_exp = plt.axes([0.05, 0.28, 0.20, 0.03])
slider_exp = Slider(ax_exp, 'Expansión Mer-Ka-Ba', 0.5, 5.0, valinit=1.0, color='#ff8800')

btn_mp4 = Button(plt.axes([0.05, 0.18, 0.20, 0.06]), 'Exportar MP4', color='#00ffcc')
btn_gif = Button(plt.axes([0.05, 0.11, 0.20, 0.06]), 'Exportar GIF', color='#00ccff')
btn_3d = Button(plt.axes([0.05, 0.04, 0.20, 0.06]), '3D Orbit + Mouse', color='#ffaa00')

# ====================== LÓGICA ======================
x_data = y_data = np.zeros(1)

def recalcular_todo(val=None):
    global x_data, y_data
    label = radio_menu.value_selected

    if label == '8. Mer-Ka-Ba Expandible (Drunvalo)':
        x_data, y_data = generar_merkaba(slider_exp.val)
    elif label == '10. Código Biblia - Torres Gemelas':
        x_data, y_data = generar_bible_code(int(slider_skip.val))
    elif label in ['5. Flor de la Vida Completa', '6. Semilla de la Vida', '7. Fruto de la Vida + Metatrón']:
        circles = [(0,0,1)]
        for i in range(6):
            ang = i * np.pi / 3
            circles.append((np.cos(ang), np.sin(ang), 1))
        xl, yl = [], []
        for cx,cy,r in circles:
            th = np.linspace(0,2*np.pi,400)
            xl.extend([cx + r*np.cos(th), [np.nan]])
            yl.extend([cy + r*np.sin(th), [np.nan]])
        x_data = np.concatenate(xl) * slider_v1.val
        y_data = np.concatenate(yl) * slider_v1.val
    else:
        x_data = evaluar_formula(box_x.text, t_array, slider_v1.val, slider_v2.val)
        y_data = evaluar_formula(box_y.text, t_array, slider_v1.val, slider_v2.val)

    maxv = max(np.max(np.abs(x_data)), np.max(np.abs(y_data))) * 1.25
    ax.set_xlim(-maxv, maxv)
    ax.set_ylim(-maxv, maxv)
    estado['frame'] = 0

def evaluar_formula(texto, t, v1, v2):
    texto = texto.replace('^', '**')
    dic = {'t': t, 'v1': v1, 'v2': v2, 'sin': np.sin, 'cos': np.cos, 'pi': np.pi, 'exp': np.exp}
    try:
        return eval(texto, {"__builtins__": None}, dic)
    except:
        return np.zeros_like(t)

def al_cambiar_menu(label):
    if label in ['8. Mer-Ka-Ba Expandible (Drunvalo)', '10. Código Biblia - Torres Gemelas']:
        box_x.set_val("ESPECIAL")
        box_y.set_val("usa sliders")
    else:
        fx, fy = catalogo.get(label, ('0','0'))
        box_x.set_val(fx)
        box_y.set_val(fy)
    recalcular_todo()

def exportar_gif(event):
    print("Generando GIF...")
    frames = []
    for i in range(100):
        idx = int(i * len(x_data) / 100)
        rastro.set_data(x_data[:idx], y_data[:idx])
        fig.canvas.draw()
        frame = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(fig.canvas.get_width_height()[::-1] + (3,))
        frames.append(frame)
    imageio.mimsave(f'ArquiMath_v9_{radio_menu.value_selected.replace(" ", "_")}.gif', frames, fps=30)
    print("¡GIF guardado!")

def mostrar_3d_orbit(event):
    fig3d = plt.figure(figsize=(11,11), facecolor='#05080a')
    ax3d = fig3d.add_subplot(111, projection='3d')
    ax3d.set_facecolor('#05080a')
    line3d, = ax3d.plot([], [], [], color='#00ffcc', lw=3)
    z = np.linspace(0, 15, len(x_data))
    def update(f):
        idx = min(f*40, len(x_data)-1)
        line3d.set_data_3d(x_data[:idx], y_data[:idx], z[:idx])
        ax3d.view_init(elev=30, azim=f*2.5)
    animation.FuncAnimation(fig3d, update, frames=400, interval=25)
    plt.show()

# Conexiones
radio_menu.on_clicked(al_cambiar_menu)
slider_v1.on_changed(recalcular_todo)
slider_v2.on_changed(recalcular_todo)
slider_fase.on_changed(recalcular_todo)
slider_skip.on_changed(recalcular_todo)
slider_exp.on_changed(recalcular_todo)
btn_gif.on_clicked(exportar_gif)
btn_3d.on_clicked(mostrar_3d_orbit)

ani = animation.FuncAnimation(fig, lambda f: None, interval=20, blit=True)
recalcular_todo()
plt.show()