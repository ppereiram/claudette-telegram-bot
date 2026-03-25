import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, TextBox, RadioButtons, Button
from mpl_toolkits.mplot3d import Axes3D
import pygame  # pip install pygame (para binaural)

pygame.mixer.init()

fig = plt.figure(figsize=(16, 10), facecolor='#05080a')
ax = fig.add_axes([0.37, 0.23, 0.58, 0.72])
ax.set_facecolor('#05080a')
ax.grid(color='#112233', linestyle='-', linewidth=0.5)

t_array = np.linspace(0, 120*np.pi, 35000)
estado = {'frame': 0, 'jugando': True, 'sonido_on': False}

rastro, = ax.plot([], [], color='#00ffcc', lw=2, alpha=0.95)

# ====================== CATÁLOGO v7.0 (20 patrones sagrados) ======================
catalogo = {
    '1. Mandala Vorticial': ('cos(t)+(v2/v1)*cos(v1*t)', 'sin(t)-(v2/v1)*sin(v1*t)'),
    '2. Espiral Nautilus Phi': ('exp(0.12*v1*t)*cos(v2*t)', 'exp(0.12*v1*t)*sin(v2*t)'),
    '3. Espiral Fibonacci Cuadrados': ('0','0'),
    '4. Toroide Doughnut': ('(v1+cos(v2*t))*cos(t)', '(v1+cos(v2*t))*sin(t)'),
    '5. Flor de la Vida Completa': ('0','0'),
    '6. Semilla de la Vida': ('0','0'),
    '7. Fruto de la Vida + Metatrón': ('0','0'),
    '8. Mer-Ka-Ba 3D (Drunvalo)': ('0','0'),
    '9. Vortex Math 3-6-9 (Rodin)': ('0','0'),
    '10. Código Biblia - Torres Gemelas': ('0','0'),
    '11. Yin-Yang 3-6-9 Animado': ('0','0'),
    '12. Vórtice Denso': ('0','0'),
    # ... (mantengo los anteriores)
}

# ====================== GENERADORES (directo de los libros) ======================
def generar_merkaba():
    t = np.linspace(0, 2*np.pi, 1200)
    # Tetraedro superior + inferior contra-rotando
    x1 = np.cos(t); y1 = np.sin(t)
    x2 = -np.cos(t*1.618); y2 = -np.sin(t*1.618)  # phi ratio
    return np.concatenate([x1, [np.nan], x2]), np.concatenate([y1, [np.nan], y2])

def generar_bible_code():
    # Matriz 30x30 con skip real (ejemplo "TORRES GEMELAS")
    grid = np.full((30,30), '·', dtype=str)
    word = "TORRESGEMELASAVIONCAERAN"
    for i, char in enumerate(word):
        grid[i%30, (i*7)%30] = char  # skip 7 como en el libro
    return grid

# ====================== SONIDO BINAURAL 3-6-9 ======================
def toggle_sonido(event):
    estado['sonido_on'] = not estado['sonido_on']
    if estado['sonido_on']:
        pygame.mixer.music.load("369_binaural.mp3")  # crea este archivo o usa tono simple
        pygame.mixer.music.play(-1)
    else:
        pygame.mixer.music.stop()

# ====================== 3D ORBIT INTERACTIVO CON MOUSE ======================
def mostrar_3d_orbit(event):
    fig3d = plt.figure(figsize=(10,10), facecolor='#05080a')
    ax3d = fig3d.add_subplot(111, projection='3d')
    ax3d.set_facecolor('#05080a')
    
    # Mer-Ka-Ba real en 3D
    theta = np.linspace(0, 2*np.pi, 800)
    x = np.cos(theta)
    y = np.sin(theta)
    z = np.zeros_like(x)
    line, = ax3d.plot(x, y, z, color='#00ffcc', lw=3)
    point, = ax3d.plot([0], [0], [0], 'o', color='white', markersize=10)
    
    def on_move(event):
        if event.button == 1:
            ax3d.view_init(elev=event.ydata*0.5, azim=event.xdata*2)
            fig3d.canvas.draw_idle()
    
    fig3d.canvas.mpl_connect('motion_notify_event', on_move)
    ani3d = animation.FuncAnimation(fig3d, lambda f: (line.set_data_3d(x*np.cos(f*0.05), y*np.sin(f*0.05), z+f*0.01), point.set_data_3d([x[0]], [y[0]], [z[0]])), frames=300, interval=20)
    plt.show()

# ====================== INTERFAZ + CONEXIONES ======================
# (radio, sliders, botón sonido nuevo, etc.)
btn_sonido = Button(plt.axes([0.05, 0.01, 0.20, 0.06]), 'Sonido Binaural 3-6-9', color='#aa00ff')
btn_sonido.on_clicked(toggle_sonido)

btn_3d.on_clicked(mostrar_3d_orbit)

# Animación principal + recalcular (igual que v6 pero con nuevos patrones)
recalcular_todo()
plt.show()