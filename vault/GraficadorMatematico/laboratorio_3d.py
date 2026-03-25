import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button

# 1. Configuración de la figura y el entorno 3D
fig = plt.figure(figsize=(10, 8), facecolor='#111111')
ax = fig.add_subplot(111, projection='3d')
fig.subplots_adjust(left=0.1, bottom=0.3) # Dejar espacio abajo para la interfaz
ax.set_facecolor('#111111')

# Estilo de los ejes para que parezca un plano arquitectónico/matemático
ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
ax.tick_params(colors='white')

# 2. Variables matemáticas iniciales
t_max = 10
t = np.linspace(0, t_max, 1000)
frecuencia_inicial = 1.0

# 3. Dibujar los elementos base
# La espiral 3D (Tiempo, Parte Real, Parte Imaginaria)
linea_3d, = ax.plot([], [], [], color='cyan', lw=2, label='Onda Compleja 3D')
# La proyección 2D (Seno) en la pared del fondo
sombra_y, = ax.plot([], [], [], color='yellow', alpha=0.5, lw=1.5)
# La proyección 2D (Coseno) en el piso
sombra_z, = ax.plot([], [], [], color='blue', alpha=0.5, lw=1.5)

ax.set_xlim(0, t_max)
ax.set_ylim(-1.5, 1.5)
ax.set_zlim(-1.5, 1.5)
ax.set_xlabel('Tiempo (t)', color='white')
ax.set_ylabel('Real (Coseno)', color='white')
ax.set_zlabel('Imaginario (Seno)', color='white')

# 4. Función que actualiza la matemática
def actualizar_grafica(frecuencia):
    x = t
    y = np.cos(frecuencia * t)
    z = np.sin(frecuencia * t)
    
    # Actualizar espiral 3D
    linea_3d.set_data(x, y)
    linea_3d.set_3d_properties(z)
    
    # Actualizar proyección Y (pared Z= -1.5)
    sombra_y.set_data(x, y)
    sombra_y.set_3d_properties(-1.5)
    
    # Actualizar proyección Z (piso Y= 1.5)
    sombra_z.set_data(x, np.full_like(x, 1.5))
    sombra_z.set_3d_properties(z)
    
    fig.canvas.draw_idle()

# 5. --- LA INTERFAZ DE USUARIO (GUI) ---
# Crear el Slider (Deslizador)
ax_frecuencia = fig.add_axes([0.2, 0.15, 0.6, 0.03], facecolor='gray')
slider_frec = Slider(
    ax=ax_frecuencia, label='Frecuencia (ω)', 
    valmin=0.1, valmax=5.0, valinit=frecuencia_inicial, color='cyan'
)

# Qué hacer cuando mueves el slider
def al_mover_slider(val):
    actualizar_grafica(slider_frec.val)
    
slider_frec.on_changed(al_mover_slider)

# Crear el Botón de Exportar
ax_boton = fig.add_axes([0.4, 0.05, 0.2, 0.05])
boton_exportar = Button(ax_boton, 'Exportar MP4', color='darkgray', hovercolor='cyan')

# Qué hacer cuando presionas Exportar (Crear una animación y guardarla)
def exportar_video(event):
    print("Preparando exportación a MP4... por favor espera.")
    frec_actual = slider_frec.val
    
    def frame_export(f):
        # Dibujar progresivamente para el video
        idx = int((f / 150) * len(t))
        if idx == 0: idx = 1
        x, y, z = t[:idx], np.cos(frec_actual * t[:idx]), np.sin(frec_actual * t[:idx])
        
        linea_3d.set_data(x, y)
        linea_3d.set_3d_properties(z)
        sombra_y.set_data(x, y)
        sombra_y.set_3d_properties(-1.5)
        sombra_z.set_data(x, np.full_like(x, 1.5))
        sombra_z.set_3d_properties(z)
        return linea_3d, sombra_y, sombra_z

    ani = animation.FuncAnimation(fig, frame_export, frames=150, blit=False)
    ani.save(f'onda_3d_frec_{frec_actual:.1f}.mp4', writer='ffmpeg', fps=30, dpi=150)
    print("¡Exportación exitosa! Revisa la carpeta.")

boton_exportar.on_clicked(exportar_video)

# Inicializar la gráfica con los valores por defecto
actualizar_grafica(frecuencia_inicial)

# Mostrar la ventana interactiva
plt.show()