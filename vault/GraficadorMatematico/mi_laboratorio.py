import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button, TextBox

# 1. Configuración del Lienzo (Estilo Blueprint Arquitectónico)
fig, ax = plt.subplots(figsize=(9, 9), facecolor='#050e14')
plt.subplots_adjust(left=0.1, bottom=0.35, right=0.9, top=0.95)
ax.set_facecolor('#050e14')
ax.grid(color='#142938', linestyle='--', linewidth=0.5)
ax.tick_params(colors='#142938')

# 2. Variables de Tiempo y Estado
t_max = 50 * np.pi 
t_array = np.linspace(0, t_max, 15000) # Alta resolución
estado = {'frame': 0, 'jugando': True}

# Elementos gráficos
rastro, = ax.plot([], [], color='#00ffcc', lw=1.0, alpha=0.8)
puntero, = ax.plot([], [], 'o', color='white', markersize=4)
brazo, = ax.plot([], [], color='#ff0055', lw=1.5, alpha=0.5)

ax.set_xlim(-3, 3)
ax.set_ylim(-3, 3)

# 3. Función Evaluadora de Fórmulas (El cerebro del laboratorio)
def evaluar_formula(texto, t, v1, v2):
    # Traducir símbolos para que Python los entienda
    texto = texto.replace('^', '**') 
    
    # Diccionario de palabras matemáticas permitidas
    diccionario_matematico = {
        't': t, 'v1': v1, 'v2': v2,
        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'pi': np.pi, 'e': np.e, 'exp': np.exp,
        'sqrt': np.sqrt, 'abs': np.abs
    }
    
    try:
        # Intenta calcular la fórmula
        resultado = eval(texto, {"__builtins__": None}, diccionario_matematico)
        # Si la fórmula da un solo número, lo convierte en un array para que no falle
        if isinstance(resultado, (int, float)):
            resultado = np.full_like(t, resultado)
        return resultado
    except Exception:
        # Si la fórmula está incompleta mientras escribes, dibuja un punto en cero
        return np.zeros_like(t)

# 4. --- INTERFAZ DE USUARIO (GUI) ---
color_ui = '#0a1924'

# Cajas de Texto para X e Y
ax_box_x = plt.axes([0.2, 0.25, 0.6, 0.04])
box_x = TextBox(ax_box_x, 'Eje X(t): ', initial='cos(v1 * t) + cos(v2 * pi * t)', color=color_ui, hovercolor='#112a3d')
box_x.label.set_color('white'); box_x.text_disp.set_color('#00ffcc')

ax_box_y = plt.axes([0.2, 0.20, 0.6, 0.04])
box_y = TextBox(ax_box_y, 'Eje Y(t): ', initial='sin(v1 * t) + sin(v2 * pi * t)', color=color_ui, hovercolor='#112a3d')
box_y.label.set_color('white'); box_y.text_disp.set_color('#00ffcc')

# Sliders para v1 y v2
ax_v1 = plt.axes([0.2, 0.12, 0.6, 0.03], facecolor=color_ui)
slider_v1 = Slider(ax_v1, 'Variable v1', 0.1, 10.0, valinit=1.0, color='#ff0055')
slider_v1.label.set_color('white'); slider_v1.valtext.set_color('white')

ax_v2 = plt.axes([0.2, 0.07, 0.6, 0.03], facecolor=color_ui)
slider_v2 = Slider(ax_v2, 'Variable v2', 0.1, 10.0, valinit=1.0, color='#ff0055')
slider_v2.label.set_color('white'); slider_v2.valtext.set_color('white')

# Vectores de datos globales
x_data = np.zeros_like(t_array)
y_data = np.zeros_like(t_array)

def recalcular_todo(val=None):
    global x_data, y_data
    v1_val = slider_v1.val
    v2_val = slider_v2.val
    
    # Evaluar las fórmulas escritas por ti
    x_data = evaluar_formula(box_x.text, t_array, v1_val, v2_val)
    y_data = evaluar_formula(box_y.text, t_array, v1_val, v2_val)
    
    # Auto-ajustar la cámara para que la figura siempre quepa en pantalla
    max_val = max(np.max(np.abs(x_data)), np.max(np.abs(y_data)))
    limite = max_val * 1.1 if max_val > 0 else 1
    ax.set_xlim(-limite, limite)
    ax.set_ylim(-limite, limite)
    
    # Reiniciar la animación
    estado['frame'] = 0

# Conectar los cambios a la función de recálculo
box_x.on_submit(recalcular_todo)
box_y.on_submit(recalcular_todo)
slider_v1.on_changed(recalcular_todo)
slider_v2.on_changed(recalcular_todo)

# 5. Motor de Animación Continua
def actualizar_grafica(frame_dummy):
    if estado['jugando']:
        estado['frame'] += 15  # Velocidad de dibujo
        
    idx = estado['frame']
    if idx >= len(t_array):
        idx = len(t_array) - 1
        
    if idx > 0:
        rastro.set_data(x_data[:idx], y_data[:idx])
        puntero.set_data([x_data[idx]], [y_data[idx]])
        brazo.set_data([0, x_data[idx]], [0, y_data[idx]])
        
    return rastro, puntero, brazo

ani = animation.FuncAnimation(fig, actualizar_grafica, interval=20, blit=True, cache_frame_data=False)

# Calcular por primera vez
recalcular_todo()
plt.show()