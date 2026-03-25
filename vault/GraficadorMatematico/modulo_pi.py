import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button

# 1. Configuración del lienzo y colores
fig, ax = plt.subplots(figsize=(8, 9), facecolor='#0d1117')
fig.subplots_adjust(bottom=0.25, top=0.85) # Espacio para controles y título
ax.set_facecolor('#0d1117')
ax.axis('off')

# Mostrar la ecuación en la pantalla
fig.text(0.5, 0.92, "Laboratorio: Pi Irracional", 
         color='cyan', fontsize=16, ha='center', fontweight='bold')
fig.text(0.5, 0.86, r'$z(\theta) = e^{\theta i} + e^{\pi\theta i}$', 
         color='white', fontsize=22, ha='center')

# 2. Parámetros Matemáticos
theta_max = 20 * np.pi 
total_frames = 1000
theta_fine = np.linspace(0, theta_max, 20000)

# Calculamos la trayectoria completa de antemano
x_fine = np.cos(theta_fine) + np.cos(np.pi * theta_fine)
y_fine = np.sin(theta_fine) + np.sin(np.pi * theta_fine)

# Elementos gráficos (Añadimos colores como pediste)
trail, = ax.plot([], [], color='cyan', lw=1.2, alpha=0.6)
arm_line, = ax.plot([], [], color='magenta', lw=1.5)
dots, = ax.plot([], [], 'o', color='white', markersize=5, markerfacecolor='magenta')

ax.set_xlim(-2.5, 2.5)
ax.set_ylim(-2.5, 2.5)

# 3. Variables de estado para el reproductor
estado = {'reproduciendo': True, 'frame_actual': 0}

# 4. --- INTERFAZ DE USUARIO (GUI) ---
# Barra de tiempo
ax_slider = plt.axes([0.15, 0.12, 0.7, 0.03], facecolor='#21262d')
slider_tiempo = Slider(
    ax=ax_slider, label='Tiempo', valmin=0, valmax=total_frames, 
    valinit=0, valstep=1, color='cyan'
)

# Botón Play / Pause
ax_play = plt.axes([0.3, 0.04, 0.15, 0.05])
btn_play = Button(ax_play, 'Play / Pause', color='#21262d', hovercolor='magenta')
btn_play.label.set_color('white')

# Botón Exportar
ax_export = plt.axes([0.55, 0.04, 0.15, 0.05])
btn_export = Button(ax_export, 'Exportar MP4', color='#21262d', hovercolor='cyan')
btn_export.label.set_color('white')

# 5. Lógica de los controles
def actualizar_grafica(frame):
    # Proteger contra el frame 0 para evitar errores de Matplotlib
    idx = int((frame / total_frames) * len(theta_fine))
    if idx == 0: idx = 1 
    
    # Dibuja la estela
    trail.set_data(x_fine[:idx], y_fine[:idx])
    
    # Calcula la posición actual de los brazos
    t_val = (frame / total_frames) * theta_max
    x1, y1 = np.cos(t_val), np.sin(t_val)
    x2, y2 = x1 + np.cos(np.pi * t_val), y1 + np.sin(np.pi * t_val)
    
    arm_line.set_data([0, x1, x2], [0, y1, y2])
    dots.set_data([0, x1, x2], [0, y1, y2])
    fig.canvas.draw_idle()

def al_mover_slider(val):
    estado['frame_actual'] = int(val)
    actualizar_grafica(estado['frame_actual'])

slider_tiempo.on_changed(al_mover_slider)

def toggle_play(event):
    estado['reproduciendo'] = not estado['reproduciendo']

btn_play.on_clicked(toggle_play)

# 6. El motor de animación en tiempo real
def loop_animacion(frame_dummy):
    if estado['reproduciendo']:
        estado['frame_actual'] += 2 # Velocidad de reproducción
        if estado['frame_actual'] >= total_frames:
            estado['frame_actual'] = 0 # Reiniciar al llegar al final
        # Al mover el slider mediante código, se llama a actualizar_grafica automáticamente
        slider_tiempo.set_val(estado['frame_actual'])
    return trail, arm_line, dots

ani = animation.FuncAnimation(fig, loop_animacion, interval=30, blit=False, cache_frame_data=False)

# 7. Lógica de Exportación
def exportar_video(event):
    print("Pausando motor en tiempo real y preparando exportación a MP4...")
    estado_previo = estado['reproduciendo']
    estado['reproduciendo'] = False # Pausar mientras exporta
    
    def frame_export(f):
        actualizar_grafica(f)
        return trail, arm_line, dots

    # Creamos una animación dedicada solo para el guardado
    ani_export = animation.FuncAnimation(fig, frame_export, frames=total_frames, blit=True)
    nombre_archivo = 'modulo_pi_interactivo.mp4'
    ani_export.save(nombre_archivo, writer='ffmpeg', fps=30, dpi=150)
    print(f"¡Exportación exitosa! Guardado como {nombre_archivo}")
    estado['reproduciendo'] = estado_previo # Reanudar estado anterior

btn_export.on_clicked(exportar_video)

plt.show()