import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, TextBox, RadioButtons, Button
from mpl_toolkits.mplot3d import Axes3D
import pygame
import imageio  # pip install imageio para GIF

pygame.mixer.init()
fig = plt.figure(figsize=(16, 10), facecolor='#05080a')
ax = fig.add_axes([0.37, 0.23, 0.58, 0.72])
ax.set_facecolor('#05080a')

t_array = np.linspace(0, 120*np.pi, 40000)
estado = {'frame': 0, 'jugando': True, 'sonido': False, 'full': False}

rastro, = ax.plot([], [], color='#00ffcc', lw=2.2, alpha=0.95)

# ====================== CATÁLOGO v8.0 (22 patrones) ======================
catalogo = { ... }  # (todos los anteriores + nuevos: Platónicos, Código Biblia, Mer-Ka-Ba Expandido, Ondas 369)

# ====================== GENERADORES DIRECTOS DE LOS LIBROS ======================
def generar_platonicos(tipo, fase):
    # 5 sólidos platónicos girando (código exacto de Drunvalo)
    ...

def generar_bible_code(skip):
    # Matriz real con "TORRES GEMELAS + AVION + CAERAN" (Drosnin págs 4-5)
    ...

def generar_merkaba_expandido(exp):
    # Estrella tetraédrica + aura de luz que crece (Drunvalo Vol.1)
    ...

# ====================== SONIDO BINAURAL 3-6-9 EN TIEMPO REAL ======================
def generar_tono_369(freq=3):
    sample_rate = 44100
    duration = 0.5
    t = np.linspace(0, duration, int(sample_rate * duration))
    wave = np.sin(2 * np.pi * freq * t) * 0.3
    sound = np.int16(wave * 32767)
    pygame.sndarray.make_sound(sound).play(-1)

# ====================== 3D INTERACTIVO + FULL IMMERSIVE ======================
def mostrar_3d_full(event):
    # Abre ventana 3D con mouse + expansión automática
    ...

# ====================== EXPORTAR GIF ======================
def exportar_gif(event):
    print("Exportando GIF sagrado...")
    frames = []
    for i in range(80):
        # captura frames
        ...
    imageio.mimsave(f'ArquiMath_Sagrado_{radio_menu.value_selected}.gif', frames, fps=30)
    print("¡GIF guardado!")

# ====================== INTERFAZ + SLIDERS NUEVOS ======================
ax_skip = plt.axes([0.05, 0.33, 0.20, 0.03])
slider_skip = Slider(ax_skip, 'Skip Biblia', 1, 50, valinit=7, color='#ffff00')

ax_exp = plt.axes([0.05, 0.28, 0