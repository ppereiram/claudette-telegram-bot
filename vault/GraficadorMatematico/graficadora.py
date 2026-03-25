import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# 1. Configuración de la figura
fig, ax = plt.subplots(figsize=(7, 8), facecolor='black')
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
ax.set_facecolor('black')
ax.axis('off')

ax.text(0.5, 0.90, "Visualization of Pi being Irrational", 
        color='white', fontsize=14, ha='center', va='center', transform=ax.transAxes, fontweight='bold')
ax.text(0.5, 0.15, r'$z(\theta) = e^{\theta i} + e^{\pi\theta i}$', 
        color='white', fontsize=20, ha='center', va='center', transform=ax.transAxes)

# 2. Parámetros de la animación a gran escala
# 60*pi son suficientes vueltas para crear una figura densa y gruesa
theta_max = 60 * np.pi  
total_frames = 1800     # 60 segundos de video a 30fps

# Alta resolución para que no se faceten las curvas (80,000 puntos de cálculo)
high_res_points = 80000
theta_fine = np.linspace(0, theta_max, high_res_points)
x_fine = np.cos(theta_fine) + np.cos(np.pi * theta_fine)
y_fine = np.sin(theta_fine) + np.sin(np.pi * theta_fine)

# 3. Elementos gráficos (Línea con alpha=0.3 para lograr el efecto de "engrosamiento" por capas)
trail, = ax.plot([], [], color='white', lw=0.7, alpha=0.3, zorder=1)
arm_line, = ax.plot([], [], color='gray', lw=1.5, zorder=2)
dots, = ax.plot([], [], 'o', color='white', markersize=4, markerfacecolor='black', zorder=3)

def init():
    ax.set_xlim(-2.5, 2.5)
    ax.set_ylim(-2.5, 2.5)
    trail.set_data([], [])
    arm_line.set_data([], [])
    dots.set_data([], [])
    return trail, arm_line, dots

def update(frame):
    # --- ACCIÓN 1: DIBUJO CONTINUO ---
    current_theta = (frame / total_frames) * theta_max
    
    idx = int((frame / total_frames) * high_res_points)
    if idx == 0: idx = 1
    trail.set_data(x_fine[:idx], y_fine[:idx])
    
    x1, y1 = np.cos(current_theta), np.sin(current_theta)
    x2, y2 = x1 + np.cos(np.pi * current_theta), y1 + np.sin(np.pi * current_theta)
    
    arm_line.set_data([0, x1, x2], [0, y1, y2])
    dots.set_data([0, x1, x2], [0, y1, y2])

    # --- ACCIÓN 2: COREOGRAFÍA DE LA CÁMARA ---
    # La "brecha" de Pi ocurre maravillosamente cerca de theta = 14*pi (fotograma 420)
    zoom_in_start = 300
    zoom_in_end = 400
    zoom_out_start = 480
    zoom_out_end = 580
    
    orig_w = 5.0
    orig_cx, orig_cy = 0.0, 0.0
    target_cx, target_cy = 1.99, -0.05 
    target_width = 0.35 
    
    if frame < zoom_in_start:
        # Fase 1: Panorámica inicial
        current_w, current_cx, current_cy = orig_w, orig_cx, orig_cy
        
    elif frame <= zoom_in_end:
        # Fase 2: Acercando la cámara
        progress = (frame - zoom_in_start) / (zoom_in_end - zoom_in_start)
        ease = 0.5 - 0.5 * np.cos(np.pi * progress) 
        
        current_w = orig_w - (orig_w - target_width) * ease
        current_cx = orig_cx - (orig_cx - target_cx) * ease
        current_cy = orig_cy - (orig_cy - target_cy) * ease
        
    elif frame < zoom_out_start:
        # Fase 3: Cámara estática en el zoom viendo el traslape
        current_w, current_cx, current_cy = target_width, target_cx, target_cy
        
    elif frame <= zoom_out_end:
        # Fase 4: Alejando la cámara (Zoom Out)
        progress = (frame - zoom_out_start) / (zoom_out_end - zoom_out_start)
        ease = 0.5 - 0.5 * np.cos(np.pi * progress)
        
        # Invertimos la lógica: arrancamos en 'target' y vamos hacia 'orig'
        current_w = target_width - (target_width - orig_w) * ease
        current_cx = target_cx - (target_cx - orig_cx) * ease
        current_cy = target_cy - (target_cy - orig_cy) * ease
        
    else:
        # Fase 5: Panorámica final observando cómo se engrosa el toroide
        current_w, current_cx, current_cy = orig_w, orig_cx, orig_cy

    # Aplicar cámara
    ax.set_xlim(current_cx - current_w/2, current_cx + current_w/2)
    ax.set_ylim(current_cy - current_w/2, current_cy + current_w/2)
        
    return trail, arm_line, dots

ani = animation.FuncAnimation(fig, update, frames=total_frames, init_func=init, blit=False)

print("Renderizando película completa (60 segundos). ¡Ve por un café, tomará un par de minutos!...")
ani.save('pi_obra_maestra.mp4', writer='ffmpeg', fps=30, dpi=200)
print("¡Terminado! Revisa tu archivo 'pi_obra_maestra.mp4'")