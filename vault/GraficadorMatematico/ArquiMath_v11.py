#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   ArquiMath Studio  v11.0  —  Laboratorio Visual Matemático     ║
║   Paramétrico · Sagrado · Fractal · Arquitectónico              ║
║   Para arquitectos que piensan con los ojos.                    ║
║   pip install numpy matplotlib imageio                          ║
╚══════════════════════════════════════════════════════════════════╝
"""
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import matplotlib.collections as mc
from matplotlib.widgets import Slider, TextBox, RadioButtons, Button
from mpl_toolkits.mplot3d import Axes3D
import warnings, os, sys
warnings.filterwarnings('ignore')

try:
    import imageio
    HAS_IMAGEIO = True
except ImportError:
    HAS_IMAGEIO = False

matplotlib.rcParams['toolbar'] = 'None'

# ═══════════════════════ CONSTANTES ════════════════════════════════
PHI = (1 + np.sqrt(5)) / 2
BG  = '#04080c'
PAN = '#0b1520'
CYN = '#00ffcc'
RED = '#ff2255'
GLD = '#ffcc00'
BLU = '#0099ff'
PRP = '#bb44ff'
ORG = '#ff8800'
WHT = '#e8f4f8'
T_MAX   = 120 * np.pi
T_ARRAY = np.linspace(0, T_MAX, 50000)

# ═══════════════════════ CATÁLOGO ══════════════════════════════════
# (nombre, fx, fy, modo)
CATALOG = [
    # ── A: CURVAS PARAMÉTRICAS ──────────────────────────────────
    ('A01 Mandala Vorticial',
     'cos(t)+(v2/v1)*cos(v1*t)', 'sin(t)-(v2/v1)*sin(v1*t)', 'curva'),
    ('A02 Espiral Nautilus Phi',
     'exp(0.12*v1*t)*cos(v2*t)', 'exp(0.12*v1*t)*sin(v2*t)', 'curva'),
    ('A03 Lissajous',
     'sin(v1*t+v3*pi/180)', 'sin(v2*t)', 'curva'),
    ('A04 Roseta Polar',
     'cos(v1*t)*cos(t)', 'cos(v1*t)*sin(t)', 'curva'),
    ('A05 Hipotrocoide',
     '(v1-v2)*cos(t)+v2*cos(((v1-v2)/v2)*t)',
     '(v1-v2)*sin(t)-v2*sin(((v1-v2)/v2)*t)', 'curva'),
    ('A06 Epicicloide',
     '(v1+v2)*cos(t)-v2*cos((v1/v2+1)*t)',
     '(v1+v2)*sin(t)-v2*sin((v1/v2+1)*t)', 'curva'),
    ('A07 Toroide 2D',
     '(v1+cos(v2*t))*cos(t)', '(v1+cos(v2*t))*sin(t)', 'curva'),
    ('A08 Espiral Galáctica',
     'v1*t*cos(t+v2*sin(3*t))', 'v1*t*sin(t+v2*sin(3*t))', 'curva'),
    ('A09 Pi Irracional',
     'cos(v1*t)+cos(pi*t)', 'sin(v1*t)+sin(pi*t)', 'curva'),
    ('A10 Mariposa (Butterfly)',
     'sin(t)*(exp(cos(t))-2*cos(v1*t))',
     'cos(t)*(exp(cos(t))-2*cos(v1*t))', 'curva'),
    ('A11 Lemniscata de Bernoulli',
     'v1*cos(t)/(1+sin(t)**2)', 'v1*sin(t)*cos(t)/(1+sin(t)**2)', 'curva'),
    ('A12 Formula Libre',
     'sin(v1*t)*cos(v2*t)', 'sin(v2*t)*cos(v1*t)', 'curva'),
    # ── B: GEOMETRÍA SAGRADA ────────────────────────────────────
    ('B01 Flor de la Vida',      '0','0','especial'),
    ('B02 Semilla de la Vida',   '0','0','especial'),
    ('B03 Fruto + Metatron',     '0','0','especial'),
    ('B04 Cubo de Metatron',     '0','0','especial'),
    ('B05 Merkaba Expandible',   '0','0','especial'),
    ('B06 Vortex Math 3-6-9',    '0','0','especial'),
    ('B07 Yin-Yang Tesla',       '0','0','especial'),
    ('B08 Espiral Fibonacci',    '0','0','especial'),
    ('B09 Genesis Rotaciones',   '0','0','especial'),
    ('B10 Solidos Platonicos',   '0','0','especial'),
    # ── C: FRACTALES ────────────────────────────────────────────
    ('C01 Mandelbrot',     '0','0','fractal'),
    ('C02 Julia Set',      '0','0','fractal'),
    ('C03 Newton z3-1',    '0','0','fractal'),
    ('C04 Sierpinski',     '0','0','especial'),
    ('C05 Copo de Koch',   '0','0','especial'),
    ('C06 Arbol Fractal',  '0','0','especial'),
    # ── D: ARQUITECTONICO PARAMETRICO ───────────────────────────
    ('D01 Arco Parabolico',      '0','0','especial'),
    ('D02 Catenaria',            '0','0','especial'),
    ('D03 Trama Estructural',    '0','0','especial'),
    ('D04 Boveda Nervada',       '0','0','especial'),
    ('D05 Cercha Triangulada',   '0','0','especial'),
    ('D06 Espiral Voronoi',      '0','0','especial'),
]

NOMBRES = [c[0] for c in CATALOG]
FX_DEF  = {c[0]: c[1] for c in CATALOG}
FY_DEF  = {c[0]: c[2] for c in CATALOG}
MODO    = {c[0]: c[3] for c in CATALOG}

# ═══════════════════════ INFO PANEL ════════════════════════════════
INFO = {
    'A01 Mandala Vorticial':
        "Hipotrociode. v1=velocidad angular, v2=pétalos.\n"
        "v1=7 v2=3 → flor 7 pétalos\nv1=11 v2=5 → estrella compleja",
    'A02 Espiral Nautilus Phi':
        "Espiral logarítmica. Base: e^(0.12·v1·t).\n"
        "v1 controla la tasa de crecimiento.\nv2 controla los giros.",
    'A03 Lissajous':
        "Figuras de Bowditch/Lissajous.\n"
        "v1/v2 = razón de frecuencias.\nv3 = desfase en grados.",
    'A04 Roseta Polar':
        "Curva rosa: r = cos(v1·t).\n"
        "v1 entero par → 2·v1 pétalos\nv1 entero impar → v1 pétalos",
    'A05 Hipotrocoide':
        "Spirograph interior. v1=radio exterior,\n"
        "v2=radio rodillo. v1/v2 racional → cierra.",
    'A06 Epicicloide':
        "Spirograph exterior. v1=radio base,\n"
        "v2=radio rodillo. v1=5 v2=1 → pentágono punteado.",
    'A07 Toroide 2D':
        "Proyección de toro. v1=radio mayor (tubo),\n"
        "v2=frecuencia ondulación.",
    'A08 Espiral Galáctica':
        "Espiral de Arquímedes modulada.\n"
        "v1=expansión radial, v2=ondulación espiral.",
    'A09 Pi Irracional':
        "e^(iθ) + e^(iπθ). Pi es irracional:\n"
        "¡la curva nunca se cierra!\nv1 cambia la frecuencia interna.",
    'A10 Mariposa (Butterfly)':
        "Temple H. Fay, 1989.\nv1=lóbulos (usar 4).\n"
        "Una de las curvas más bellas de la matemática.",
    'A11 Lemniscata de Bernoulli':
        "∞ matemático. x=a·cos(t)/(1+sin²t)\n"
        "v1 controla el tamaño del infinito.",
    'A12 Formula Libre':
        "Edita las fórmulas X e Y directamente.\n"
        "Variables: t, v1, v2, v3, v4, sin, cos, exp, pi, sqrt, log",
    'B01 Flor de la Vida':
        "Drunvalo Melchizedek: 'El patrón de la creación'.\n"
        "v1=zoom, v2=capas (1-4). 1→Semilla, 2→19 círculos,\n"
        "3→37 círculos. v3=rotación.",
    'B02 Semilla de la Vida':
        "7 círculos: el origen. Génesis de la Creación.\n"
        "v1=zoom, v3=rotación.",
    'B03 Fruto + Metatron':
        "13 círculos del Fruto de la Vida.\n"
        "v1=zoom, v3=rotación.",
    'B04 Cubo de Metatron':
        "13 centros del Fruto conectados. Contiene\n"
        "los 5 sólidos platónicos. v1=zoom.",
    'B05 Merkaba Expandible':
        "Dos tetraedros inter-rotando. v1=expansión,\n"
        "v2=aura (capas), v3=rotación del tetraedro inferior.",
    'B06 Vortex Math 3-6-9':
        "Rodin/Tesla: 1-2-4-8-7-5 (azul) + triángulo 3-6-9 (rojo).\n"
        "v1=radio. La secuencia forma un circuito cerrado.",
    'B07 Yin-Yang Tesla':
        "Símbolo yin-yang + marcas 3-6-9.\n"
        "v1=radio, v2=anillos concéntricos, v3=rotación.",
    'B08 Espiral Fibonacci':
        "Espiral dorada. v1=escala, v2=vueltas.\n"
        "Crece por factor PHI (1.618) cada cuarto de giro.",
    'B09 Genesis Rotaciones':
        "Círculos generativos de la creación (Drunvalo).\n"
        "v1=radio base, v2=capas de rotación.",
    'B10 Solidos Platonicos':
        "Proyección ortogonal. v2=sólido: 0=Tetraedro,\n"
        "1=Cubo, 2=Octaedro, 3=Dodecaedro, 4=Icosaedro.\n"
        "v3=rotación. Usa '3D Orbit' para verlos girar.",
    'C01 Mandelbrot':
        "z → z^p + c. v1=zoom, v2=iteraciones.\n"
        "v3=potencia (2=clásico, 3=Mandelbulb-like).\n"
        "CLIC en el fractal para centrar el zoom.",
    'C02 Julia Set':
        "z → z² + c fijo. v1=zoom, v2=iteraciones.\n"
        "v3=c_real, v4=c_imag. CLIC para mover c.",
    'C03 Newton z3-1':
        "Cuencas de atracción de z³=1.\n"
        "3 raíces → 3 colores. v1=zoom, v2=iteraciones.",
    'C04 Sierpinski':
        "Triángulo de Sierpiński. v2=profundidad (1-7).\n"
        "Dimensión fractal ≈ 1.585.",
    'C05 Copo de Koch':
        "Copo de nieve de Koch. v2=iteraciones (1-6).\n"
        "Perímetro→∞, área→finita. v1=escala.",
    'C06 Arbol Fractal':
        "Árbol auto-similar. v1=altura, v2=ángulo de apertura.\n"
        "v3=asimetría L/R, v4=profundidad (1-12).",
    'D01 Arco Parabolico':
        "y = h(1-(2x/w)²). v1=altura, v2=ancho.\n"
        "v3=número de arcos. Usado en puentes modernos.",
    'D02 Catenaria':
        "y = a·cosh(x/a). La forma natural del cable colgante.\n"
        "v1=parámetro 'a' (flecha), v2=semi-luz.\n"
        "v3=número de arcos. Sagrada Familia → catenarias.",
    'D03 Trama Estructural':
        "v1=módulo, v2=filas, v3=columnas.\n"
        "v4: 0=reticular, 1=triangulada, 2=hexagonal.",
    'D04 Boveda Nervada':
        "Vista axonométrica de bóveda de crucería.\n"
        "v1=radio, v2=nervios, v3=altura relativa.",
    'D05 Cercha Triangulada':
        "Cercha Pratt. v1=altura, v2=módulos.\n"
        "v3=tipo: 0=Pratt, 1=Warren, 2=Howe.",
    'D06 Espiral Voronoi':
        "Puntos en espiral dorada + Delaunay approx.\n"
        "v1=escala, v2=puntos, v3=semilla aleatoria.",
}

# ═══════════════════════ HELPERS ═══════════════════════════════════
def eval_formula(text, t, v1, v2, v3, v4):
    text = text.replace('^', '**').replace('√','sqrt')
    ns = {
        't': t, 'v1': v1, 'v2': v2, 'v3': v3, 'v4': v4,
        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt,
        'pi': np.pi, 'e': np.e, 'phi': PHI,
        'abs': np.abs, 'sign': np.sign,
        'sinh': np.sinh, 'cosh': np.cosh,
        'arcsin': np.arcsin, 'arccos': np.arccos, 'arctan': np.arctan,
        '__builtins__': None,
    }
    try:
        result = eval(text, ns)
        if np.isscalar(result):
            return np.full_like(t, float(result))
        return np.asarray(result, dtype=float)
    except Exception:
        return np.zeros_like(t)

def rot2d(x, y, angle_deg):
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return c*x - s*y, s*x + c*y

def project3d(verts, azim_deg, elev_deg=25):
    a = np.deg2rad(azim_deg)
    e = np.deg2rad(elev_deg)
    Ry = np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
    Rx = np.array([[1,0,0],[0,np.cos(e),-np.sin(e)],[0,np.sin(e),np.cos(e)]])
    R = Rx @ Ry
    v = (R @ verts.T).T
    return v[:, 0], v[:, 1]

def hex_centers(layers, r=1.0):
    seen = set(); pts = []
    for q in range(-layers, layers+1):
        for s in range(-layers, layers+1):
            rr = -q-s
            if abs(rr) <= layers:
                x = r*(q + s*0.5)
                y = r*(s*np.sqrt(3)/2)
                k = (round(x,4), round(y,4))
                if k not in seen:
                    seen.add(k); pts.append((x,y))
    return pts

def draw_circles(ax, centers, r, color=CYN, lw=0.9, alpha=0.75):
    th = np.linspace(0, 2*np.pi, 300)
    for cx, cy in centers:
        ax.plot(cx + r*np.cos(th), cy + r*np.sin(th),
                color=color, lw=lw, alpha=alpha)

# ═══════════════════════ GEOMETRÍA SAGRADA ═════════════════════════
def draw_flower(ax, v1=1.0, v2=2, v3=0):
    layers = max(1, min(4, int(v2)))
    r = v1
    centers = hex_centers(layers, r)
    cx_all = [c[0] for c in centers]
    cy_all = [c[1] for c in centers]
    cx_r, cy_r = rot2d(np.array(cx_all), np.array(cy_all), v3)
    draw_circles(ax, list(zip(cx_r, cy_r)), r)
    m = max(abs(np.max(cx_r)+r), abs(np.max(cy_r)+r)) * 1.1
    ax.set_xlim(-m, m); ax.set_ylim(-m, m)
    ax.set_aspect('equal')

def draw_seed(ax, v1=1.0, v3=0):
    r = v1
    centers = [(0,0)] + [(r*np.cos(i*np.pi/3), r*np.sin(i*np.pi/3)) for i in range(6)]
    cx_r, cy_r = rot2d(np.array([c[0] for c in centers]),
                       np.array([c[1] for c in centers]), v3)
    draw_circles(ax, list(zip(cx_r, cy_r)), r)
    ax.set_xlim(-2.2*r, 2.2*r); ax.set_ylim(-2.2*r, 2.2*r)
    ax.set_aspect('equal')

def fruit_centers_fn(r=1.0):
    c = [(0,0)]
    for i in range(6):
        c.append((r*np.cos(i*np.pi/3), r*np.sin(i*np.pi/3)))
    for i in range(6):
        c.append((2*r*np.cos(i*np.pi/3), 2*r*np.sin(i*np.pi/3)))
    return c

def draw_fruit(ax, v1=1.0, v3=0):
    r = v1
    centers = fruit_centers_fn(r)
    cx_r, cy_r = rot2d(np.array([c[0] for c in centers]),
                       np.array([c[1] for c in centers]), v3)
    draw_circles(ax, list(zip(cx_r, cy_r)), r)
    ax.set_xlim(-3.2*r, 3.2*r); ax.set_ylim(-3.2*r, 3.2*r)
    ax.set_aspect('equal')

def draw_metatron(ax, v1=1.0, v3=0):
    r = v1
    centers = fruit_centers_fn(r)
    cx_r, cy_r = rot2d(np.array([c[0] for c in centers]),
                       np.array([c[1] for c in centers]), v3)
    draw_circles(ax, list(zip(cx_r, cy_r)), r, alpha=0.35)
    n = len(cx_r)
    for i in range(n):
        for j in range(i+1, n):
            ax.plot([cx_r[i], cx_r[j]], [cy_r[i], cy_r[j]],
                    color=GLD, lw=0.5, alpha=0.55)
    ax.set_xlim(-3.2*r, 3.2*r); ax.set_ylim(-3.2*r, 3.2*r)
    ax.set_aspect('equal')

def draw_merkaba(ax, v1=1.5, v2=3, v3=0):
    r = v1
    th = np.linspace(0, 2*np.pi, 400)
    # Outer circle
    ax.plot(r*np.cos(th), r*np.sin(th), color=CYN, lw=0.8, alpha=0.4)
    # Triangle up
    a1 = np.array([np.pi/2 + i*2*np.pi/3 for i in range(3)])
    x1 = r*np.cos(a1); y1 = r*np.sin(a1)
    x1r, y1r = rot2d(x1, y1, 0)
    ax.fill(np.append(x1r, x1r[0]), np.append(y1r, y1r[0]),
            alpha=0.12, color=BLU)
    ax.plot(np.append(x1r, x1r[0]), np.append(y1r, y1r[0]),
            color=BLU, lw=2)
    # Triangle down (rotated 60°+v3)
    a2 = a1 + np.pi/3
    x2 = r*np.cos(a2); y2 = r*np.sin(a2)
    x2r, y2r = rot2d(x2, y2, v3)
    ax.fill(np.append(x2r, x2r[0]), np.append(y2r, y2r[0]),
            alpha=0.12, color=RED)
    ax.plot(np.append(x2r, x2r[0]), np.append(y2r, y2r[0]),
            color=RED, lw=2)
    # Aura rings
    for k in range(1, int(v2)+1):
        rk = r * (1 + k*0.25)
        ax.plot(rk*np.cos(th), rk*np.sin(th), color=GLD, lw=0.4, alpha=0.3)
    m = r*(1 + int(v2)*0.25) * 1.15
    ax.set_xlim(-m, m); ax.set_ylim(-m, m)
    ax.set_aspect('equal')

def draw_vortex369(ax, v1=2.0, v3=0):
    r = v1
    N = 9
    angles = [np.pi/2 - i*2*np.pi/N + np.deg2rad(v3) for i in range(N)]
    pts = {i+1: (r*np.cos(angles[i]), r*np.sin(angles[i])) for i in range(N)}
    th = np.linspace(0, 2*np.pi, 500)
    ax.plot(r*np.cos(th), r*np.sin(th), color=CYN, lw=1.2, alpha=0.4)
    seq = [1, 2, 4, 8, 7, 5]
    for i in range(len(seq)):
        a, b = seq[i], seq[(i+1)%len(seq)]
        ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]],
                color=BLU, lw=1.8, alpha=0.9)
    tri = [pts[3], pts[6], pts[9], pts[3]]
    ax.plot([p[0] for p in tri], [p[1] for p in tri],
            color=RED, lw=2.5)
    for i in range(1, 10):
        x, y = pts[i]
        color = RED if i in [3,6,9] else GLD
        ax.plot(x, y, 'o', color=color, markersize=9, zorder=5)
        ax.text(x*1.15, y*1.15, str(i), color=color, fontsize=11,
                ha='center', va='center', fontweight='bold')
    ax.set_xlim(-r*1.4, r*1.4); ax.set_ylim(-r*1.4, r*1.4)
    ax.set_aspect('equal')

def draw_yinyang(ax, v1=2.0, v2=3, v3=0):
    r = v1
    th = np.linspace(0, 2*np.pi, 600)
    # Outer
    ax.plot(r*np.cos(th), r*np.sin(th), color=WHT, lw=2.5)
    # Yin (dark) half
    th_h = np.linspace(np.deg2rad(v3), np.pi+np.deg2rad(v3), 300)
    xd = np.concatenate([r*np.cos(th_h),
                         (r/2)*np.cos(np.pi+th_h[::-1]),
                         (r/2)*np.cos(th_h)])
    yd = np.concatenate([r*np.sin(th_h),
                         (r/2)*np.sin(np.pi+th_h[::-1]),
                         (r/2)*np.sin(th_h)])
    ax.fill(xd, yd, color='#1a1a2e', alpha=0.8)
    # Yang (light) half
    th_h2 = np.linspace(np.pi+np.deg2rad(v3), 2*np.pi+np.deg2rad(v3), 300)
    xl = np.concatenate([r*np.cos(th_h2),
                         (r/2)*np.cos(np.pi+th_h2[::-1]),
                         (r/2)*np.cos(th_h2)])
    yl = np.concatenate([r*np.sin(th_h2),
                         (r/2)*np.sin(np.pi+th_h2[::-1]),
                         (r/2)*np.sin(th_h2)])
    ax.fill(xl, yl, color=WHT, alpha=0.8)
    # Small circles
    ax.plot(r/2*np.cos(np.deg2rad(v3)+np.pi/2) + (r/4)*np.cos(th),
            r/2*np.sin(np.deg2rad(v3)+np.pi/2) + (r/4)*np.sin(th),
            color='#1a1a2e', lw=0); \
    ax.fill(r/2*np.cos(np.deg2rad(v3)+np.pi/2) + (r/4)*np.cos(th),
            r/2*np.sin(np.deg2rad(v3)+np.pi/2) + (r/4)*np.sin(th),
            color='#1a1a2e')
    ax.fill(r/2*np.cos(np.deg2rad(v3)-np.pi/2) + (r/4)*np.cos(th),
            r/2*np.sin(np.deg2rad(v3)-np.pi/2) + (r/4)*np.sin(th),
            color=WHT)
    # 3-6-9 markers
    for i, n in enumerate([3, 6, 9]):
        a = np.deg2rad(v3) + i * 2*np.pi/3
        ax.text(r*1.1*np.cos(a), r*1.1*np.sin(a), str(n),
                color=RED, fontsize=13, ha='center', va='center', fontweight='bold')
    # Concentric rings
    for k in range(1, int(v2)+1):
        rk = r * (1 + k*0.2)
        ax.plot(rk*np.cos(th), rk*np.sin(th), color=GLD, lw=0.5, alpha=0.4)
    m = r*(1 + int(v2)*0.2)*1.2
    ax.set_xlim(-m, m); ax.set_ylim(-m, m)
    ax.set_aspect('equal')

def draw_fibonacci(ax, v1=1.0, v2=4):
    vueltas = max(1, min(8, int(v2)))
    th = np.linspace(0, vueltas*2*np.pi, 3000)
    r = v1 * PHI**(th/np.pi)
    x = r*np.cos(th); y = r*np.sin(th)
    # Color gradient
    from matplotlib.collections import LineCollection
    pts = np.array([x, y]).T.reshape(-1, 1, 2)
    segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
    lc = LineCollection(segs, cmap='plasma', lw=2, alpha=0.9)
    lc.set_array(th)
    ax.add_collection(lc)
    # Golden rectangles (simplified)
    r_max = v1 * PHI**(vueltas*2)
    ax.set_xlim(-r_max*1.1, r_max*1.1)
    ax.set_ylim(-r_max*1.1, r_max*1.1)
    ax.set_aspect('equal')

def draw_genesis(ax, v1=1.5, v2=3, v3=0):
    r = v1
    th = np.linspace(0, 2*np.pi, 500)
    for layer in range(1, int(v2)+1):
        n_circles = layer * 6
        for i in range(n_circles):
            a = i * 2*np.pi / n_circles + np.deg2rad(v3) * layer
            cx = layer * r * np.cos(a)
            cy = layer * r * np.sin(a)
            rc = r * (1 - layer*0.08)
            if rc > 0.05:
                ax.plot(cx + rc*np.cos(th), cy + rc*np.sin(th),
                        color=CYN, lw=0.6, alpha=0.5)
    ax.plot(r*np.cos(th), r*np.sin(th), color=GLD, lw=1.5, alpha=0.6)
    m = (int(v2)+1)*r*1.15
    ax.set_xlim(-m, m); ax.set_ylim(-m, m)
    ax.set_aspect('equal')

# ─── Platonic solids ───────────────────────────────────────────────
def _platonic_data():
    phi = PHI
    solidos = {
        0: ('Tetraedro', np.array([[1,1,1],[-1,-1,1],[-1,1,-1],[1,-1,-1]], float),
            [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]),
        1: ('Cubo', np.array([(x,y,z) for x in [-1,1] for y in [-1,1] for z in [-1,1]], float),
            [(0,1),(2,3),(4,5),(6,7),(0,2),(1,3),(4,6),(5,7),(0,4),(1,5),(2,6),(3,7)]),
        2: ('Octaedro', np.array([[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]], float),
            [(0,2),(0,3),(0,4),(0,5),(1,2),(1,3),(1,4),(1,5),(2,4),(2,5),(3,4),(3,5)]),
        3: ('Dodecaedro',
            np.array([[s1,s2,s3] for s1 in[1,-1] for s2 in[1,-1] for s3 in[1,-1]] +
                     [[0,s/phi,s2*phi] for s in[1,-1] for s2 in[1,-1]] +
                     [[s/phi,s2*phi,0] for s in[1,-1] for s2 in[1,-1]] +
                     [[s*phi,0,s2/phi] for s in[1,-1] for s2 in[1,-1]], float),
            None),
        4: ('Icosaedro',
            np.array([[0,s1,s2*phi] for s1 in[1,-1] for s2 in[1,-1]] +
                     [[s1,s2*phi,0] for s1 in[1,-1] for s2 in[1,-1]] +
                     [[s2*phi,0,s1] for s1 in[1,-1] for s2 in[1,-1]], float),
            None),
    }
    # Auto-generate edges for dodecahedron and icosahedron
    for k in [3, 4]:
        name, verts, _ = solidos[k]
        target = 2/phi if k==3 else 2.0
        edges = []
        dists = np.array([[np.linalg.norm(verts[i]-verts[j])
                           for j in range(len(verts))]
                          for i in range(len(verts))])
        min_d = np.partition(dists[dists>0.01].ravel(), 0)[0]
        for i in range(len(verts)):
            for j in range(i+1, len(verts)):
                if abs(dists[i,j] - min_d) < 0.2:
                    edges.append((i,j))
        solidos[k] = (name, verts, edges)
    return solidos

PLATONIC_DATA = _platonic_data()

def draw_platonic(ax, v1=2.0, v2=0, v3=0):
    idx = int(v2) % 5
    name, verts, edges = PLATONIC_DATA[idx]
    scale = v1
    xp, yp = project3d(verts * scale, v3)
    for e in edges:
        ax.plot([xp[e[0]], xp[e[1]]], [yp[e[0]], yp[e[1]]],
                color=CYN, lw=1.8, alpha=0.85)
    ax.plot(xp, yp, 'o', color=GLD, markersize=5, zorder=5)
    m = scale * 2.2
    ax.set_xlim(-m, m); ax.set_ylim(-m, m)
    ax.set_aspect('equal')
    ax.set_title(f'  {name}  (v2={idx})', color=GLD, fontsize=10, pad=4)

# ═══════════════════════ FRACTALES ═════════════════════════════════
def compute_mandelbrot(cx, cy, zoom, iters, power=2.0):
    w = h = 480
    r = 1.8 / zoom
    x = np.linspace(cx-r, cx+r, w)
    y = np.linspace(cy-r, cy+r, h)
    X, Y = np.meshgrid(x, y)
    C = X + 1j*Y
    Z = np.zeros_like(C)
    M = np.zeros(C.shape, dtype=int)
    for i in range(int(iters)):
        mask = np.abs(Z) <= 2
        Z[mask] = Z[mask]**power + C[mask]
        M[mask] += 1
    return M

def compute_julia(zoom, iters, cr=-0.7, ci=0.27):
    w = h = 480
    r = 1.8 / zoom
    x = np.linspace(-r, r, w)
    y = np.linspace(-r, r, h)
    X, Y = np.meshgrid(x, y)
    Z = X + 1j*Y
    c = complex(cr, ci)
    M = np.zeros(Z.shape, dtype=int)
    for i in range(int(iters)):
        mask = np.abs(Z) <= 2
        Z[mask] = Z[mask]**2 + c
        M[mask] += 1
    return M

def compute_newton(zoom, iters):
    w = h = 480
    r = 2.0 / zoom
    x = np.linspace(-r, r, w)
    y = np.linspace(-r, r, h)
    X, Y = np.meshgrid(x, y)
    Z = X + 1j*Y
    roots = [1.0, np.exp(2j*np.pi/3), np.exp(4j*np.pi/3)]
    basin = np.zeros(Z.shape, dtype=float)
    for _ in range(int(iters)):
        with np.errstate(divide='ignore', invalid='ignore'):
            Z = Z - (Z**3 - 1) / (3*Z**2 + 1e-10)
    for k, root in enumerate(roots):
        basin[np.abs(Z - root) < 0.01] = k + 1
    # shade by convergence speed
    return basin

def sierpinski_tris(pts, depth):
    if depth == 0:
        return [pts]
    a, b, c = pts
    ab = ((a[0]+b[0])/2, (a[1]+b[1])/2)
    bc = ((b[0]+c[0])/2, (b[1]+c[1])/2)
    ca = ((c[0]+a[0])/2, (c[1]+a[1])/2)
    return (sierpinski_tris((a, ab, ca), depth-1) +
            sierpinski_tris((ab, b, bc), depth-1) +
            sierpinski_tris((ca, bc, c), depth-1))

def draw_sierpinski(ax, v1=2.0, depth=4):
    depth = max(0, min(7, int(depth)))
    r = v1
    base = [(0, r), (-r*np.sqrt(3)/2, -r/2), (r*np.sqrt(3)/2, -r/2)]
    tris = sierpinski_tris(base, depth)
    for tri in tris:
        xs = [p[0] for p in tri] + [tri[0][0]]
        ys = [p[1] for p in tri] + [tri[0][1]]
        ax.fill(xs, ys, color=CYN, alpha=0.7)
        ax.plot(xs, ys, color=BG, lw=0.3)
    ax.set_xlim(-r*1.1, r*1.1); ax.set_ylim(-r*1.2, r*1.2)
    ax.set_aspect('equal')

def koch_edge(p1, p2, depth):
    if depth == 0:
        return [p1, p2]
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
    p3 = (p1[0]+dx/3, p1[1]+dy/3)
    p5 = (p1[0]+2*dx/3, p1[1]+2*dy/3)
    a = np.pi/3
    px = p3[0] + (dx/3)*np.cos(a) - (dy/3)*np.sin(a)
    py = p3[1] + (dx/3)*np.sin(a) + (dy/3)*np.cos(a)
    p4 = (px, py)
    return (koch_edge(p1, p3, depth-1)[:-1] +
            koch_edge(p3, p4, depth-1)[:-1] +
            koch_edge(p4, p5, depth-1)[:-1] +
            koch_edge(p5, p2, depth-1))

def draw_koch(ax, v1=2.0, depth=4):
    depth = max(0, min(6, int(depth)))
    r = v1
    init = [(r*np.cos(np.pi/2+i*2*np.pi/3), r*np.sin(np.pi/2+i*2*np.pi/3))
            for i in range(3)]
    all_pts = []
    for i in range(3):
        all_pts.extend(koch_edge(init[i], init[(i+1)%3], depth)[:-1])
    all_pts.append(all_pts[0])
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    ax.fill(xs, ys, color=CYN, alpha=0.25)
    ax.plot(xs, ys, color=CYN, lw=1.2)
    ax.set_xlim(-r*1.3, r*1.3); ax.set_ylim(-r*1.3, r*1.3)
    ax.set_aspect('equal')

def draw_tree(ax, length=2.0, spread=28, depth=8, asym=0):
    depth = max(1, min(12, int(depth)))
    def branch(x, y, angle, length, d):
        if d == 0 or length < 0.05:
            return
        rad = np.deg2rad(angle)
        x2 = x + length*np.cos(rad)
        y2 = y + length*np.sin(rad)
        colors = [ORG, RED, GLD, CYN, BLU, PRP]
        color = colors[min(d-1, len(colors)-1)]
        ax.plot([x, x2], [y, y2], color=color,
                lw=max(0.4, d*0.35), alpha=min(1.0, d*0.13+0.1))
        branch(x2, y2, angle+spread+asym, length*0.68, d-1)
        branch(x2, y2, angle-spread+asym, length*0.68, d-1)
    branch(0, -length*0.3, 90, length, depth)
    m = length * 1.5
    ax.set_xlim(-m, m); ax.set_ylim(-length*0.4, length*1.6)
    ax.set_aspect('equal')

# ═══════════════════════ ARQUITECTÓNICO ════════════════════════════
def draw_parabolic_arch(ax, h=3.0, w=4.0, n=1):
    x = np.linspace(-w/2, w/2, 500)
    y = h*(1 - (2*x/w)**2)
    n = max(1, int(n))
    for i in range(n):
        dx = i*(w + w*0.35)
        ax.plot(x+dx, y, color=GLD, lw=2.5)
        ax.plot([-w/2+dx, w/2+dx], [0, 0], color=GLD, lw=1.5, alpha=0.5)
        ax.plot([-w/2+dx, -w/2+dx], [0, -0.2], color=GLD, lw=3)
        ax.plot([w/2+dx, w/2+dx], [0, -0.2], color=GLD, lw=3)
        ax.plot([0+dx], [h], 'o', color=RED, markersize=8, zorder=5)
    total_w = (n-1)*(w+w*0.35) + w
    ax.set_xlim(-w*0.6, total_w + w*0.1)
    ax.set_ylim(-h*0.3, h*1.25)
    ax.set_aspect('equal')

def draw_catenary(ax, a=1.5, w=4.0, n=1):
    a = max(0.2, a)
    x = np.linspace(-w/2, w/2, 500)
    y_cat = a*np.cosh(x/a)
    y0 = a*np.cosh(w/(2*a))
    y = -(y_cat - y0)   # arch goes up
    n = max(1, int(n))
    for i in range(n):
        dx = i*(w + w*0.3)
        ax.plot(x+dx, y, color=GLD, lw=2.5)
        ax.plot([-w/2+dx, w/2+dx], [0, 0], color=GLD, lw=1.5, alpha=0.5)
        ax.plot([-w/2+dx, -w/2+dx], [0, -0.15], color=GLD, lw=3)
        ax.plot([w/2+dx, w/2+dx], [0, -0.15], color=GLD, lw=3)
    total_w = (n-1)*(w+w*0.3) + w
    y_max = abs(min(y))
    ax.set_xlim(-w*0.6, total_w + w*0.1)
    ax.set_ylim(-y_max*0.35, y_max*1.3)
    ax.set_aspect('equal')

def draw_grid(ax, mod=1.0, rows=5, cols=5, tipo=0):
    rows = max(1, int(rows)); cols = max(1, int(cols))
    tipo = int(tipo) % 3
    mod = max(0.1, mod)
    if tipo == 0:  # rectangular
        for r in range(rows+1):
            ax.plot([0, cols*mod], [r*mod, r*mod], color=CYN, lw=0.9, alpha=0.8)
        for c in range(cols+1):
            ax.plot([c*mod, c*mod], [0, rows*mod], color=CYN, lw=0.9, alpha=0.8)
        for r in range(rows):
            for c in range(cols):
                ax.plot([c*mod, (c+1)*mod], [r*mod, (r+1)*mod],
                        color=RED, lw=0.45, alpha=0.45)
    elif tipo == 1:  # triangular
        h = mod * np.sqrt(3)/2
        for r in range(rows+1):
            off = (r%2)*mod*0.5
            ax.plot([off, off + cols*mod], [r*h, r*h], color=CYN, lw=0.9, alpha=0.8)
        for r in range(rows):
            for c in range(cols):
                off = (r%2)*mod*0.5
                x0 = c*mod + off
                ax.plot([x0, x0+mod/2, x0+mod, x0],
                        [r*h, (r+1)*h, r*h, r*h],
                        color=GLD, lw=0.8, alpha=0.7)
    else:  # hexagonal
        th60 = np.linspace(0, 2*np.pi, 7)
        hw = mod * np.sqrt(3)
        for r in range(rows):
            for c in range(cols):
                cx = c*hw + (r%2)*hw/2
                cy = r*mod*1.5
                hx = cx + mod*np.cos(th60)
                hy = cy + mod*np.sin(th60)
                ax.plot(hx, hy, color=CYN, lw=0.9, alpha=0.8)
    ax.set_aspect('equal')
    ax.autoscale_view()

def draw_vault(ax, r=2.0, n_nerv=8, h=0.5):
    th = np.linspace(0, 2*np.pi, 500)
    ax.plot(r*np.cos(th), r*np.sin(th), color=GLD, lw=2)
    n = max(4, int(n_nerv))
    angles = np.linspace(0, 2*np.pi, n+1)[:-1]
    for a in angles:
        ax.plot([0, r*np.cos(a)], [0, r*np.sin(a)],
                color=CYN, lw=1.6, alpha=0.85)
    inner_r = r * max(0.1, min(0.9, h))
    ax.plot(inner_r*np.cos(th), inner_r*np.sin(th), color=GLD, lw=1.2, alpha=0.5)
    if n >= 8:
        for a in angles + np.pi/n:
            ax.plot([0, inner_r*np.cos(a)], [0, inner_r*np.sin(a)],
                    color=PRP, lw=0.9, alpha=0.6)
    ax.plot(0, 0, 'o', color=RED, markersize=12, zorder=5)
    ax.plot(r*np.cos(angles), r*np.sin(angles), 'o',
            color=GLD, markersize=7, zorder=5)
    ax.set_xlim(-r*1.15, r*1.15); ax.set_ylim(-r*1.15, r*1.15)
    ax.set_aspect('equal')

def draw_truss(ax, h=1.5, n=8, tipo=0):
    n = max(2, int(n)); tipo = int(tipo) % 3
    L = n
    bot = [(i, 0) for i in range(n+1)]
    top = [(i, h) for i in range(n+1)]
    colors = {'chord': GLD, 'vert': CYN, 'diag': RED}
    ax.plot([p[0] for p in bot], [p[1] for p in bot],
            color=colors['chord'], lw=3.5, solid_capstyle='round')
    ax.plot([p[0] for p in top], [p[1] for p in top],
            color=colors['chord'], lw=3.5, solid_capstyle='round')
    for i in range(n+1):
        ax.plot([bot[i][0], top[i][0]], [bot[i][1], top[i][1]],
                color=colors['vert'], lw=1.6)
    for i in range(n):
        if tipo == 0:    # Pratt: diagonals from top to bot
            ax.plot([top[i][0], bot[i+1][0]], [h, 0], color=colors['diag'], lw=1.4)
        elif tipo == 1:  # Warren: alternating
            if i % 2 == 0:
                ax.plot([bot[i][0], top[i+1][0]], [0, h], color=colors['diag'], lw=1.4)
            else:
                ax.plot([top[i][0], bot[i+1][0]], [h, 0], color=colors['diag'], lw=1.4)
        else:            # Howe: diagonals from bot to top
            ax.plot([bot[i][0], top[i+1][0]], [0, h], color=colors['diag'], lw=1.4)
    for p in bot + top:
        ax.plot(p[0], p[1], 'o', color=ORG, markersize=6, zorder=5)
    ax.plot(0, 0, '^', color=GLD, markersize=14, zorder=6)
    ax.plot(L, 0, 'o', color=GLD, markersize=10, zorder=6)
    ax.set_xlim(-0.5, n+0.5); ax.set_ylim(-h*0.6, h*1.7)
    ax.set_aspect('equal')

def draw_voronoi_spiral(ax, v1=2.0, n_pts=60, seed=0):
    rng = np.random.RandomState(int(seed) % 9999)
    n = max(5, min(300, int(n_pts)))
    ga = 2*np.pi / PHI**2
    radii = v1 * np.sqrt(np.arange(n) / n)
    angles = np.arange(n) * ga
    xs = radii*np.cos(angles)
    ys = radii*np.sin(angles)
    sc = ax.scatter(xs, ys, c=radii, cmap='plasma', s=18, alpha=0.9, zorder=4)
    for i in range(n):
        d2 = (xs - xs[i])**2 + (ys - ys[i])**2
        d2[i] = np.inf
        nearest = np.argsort(d2)[:3]
        for j in nearest:
            if d2[j] < (v1*0.55)**2:
                ax.plot([xs[i], xs[j]], [ys[i], ys[j]],
                        color=CYN, lw=0.5, alpha=0.35)
    ax.set_xlim(-v1*1.1, v1*1.1); ax.set_ylim(-v1*1.1, v1*1.1)
    ax.set_aspect('equal')

# ═══════════════════════ FIGURA Y UI ═══════════════════════════════
fig = plt.figure(figsize=(19.5, 11.0), facecolor=BG)
fig.canvas.manager.set_window_title('ArquiMath Studio v11.0')

# Main plot area
ax = fig.add_axes([0.335, 0.22, 0.655, 0.75])
ax.set_facecolor(BG)
ax.grid(color='#112233', linestyle='-', linewidth=0.4, alpha=0.7)
ax.tick_params(colors='#223344', labelsize=7)
for spine in ax.spines.values():
    spine.set_color('#112233')

rastro,  = ax.plot([], [], color=CYN, lw=2.0, alpha=0.92)
puntero, = ax.plot([], [], 'o', color=WHT, markersize=5.5)
brazo,   = ax.plot([], [], color=RED, lw=1.0, alpha=0.55)

# Title text inside plot
titulo_ax = ax.text(0.5, 0.97, 'ArquiMath Studio v11.0',
                    transform=ax.transAxes, ha='center', va='top',
                    color=GLD, fontsize=11, alpha=0.5,
                    fontfamily='monospace')

# ── Radio buttons (left panel, full height) ─────────────────────────
ax_radio = fig.add_axes([0.002, 0.015, 0.325, 0.975], facecolor=PAN)
ax_radio.set_title('PATRONES', color=CYN, fontsize=8, pad=3, fontweight='bold')
radio_menu = RadioButtons(ax_radio, NOMBRES, activecolor=RED)
for lbl in radio_menu.labels:
    lbl.set_color(WHT)
    lbl.set_fontsize(7.3)

# ── Info panel (bottom right of control area) ───────────────────────
ax_info = fig.add_axes([0.335, 0.025, 0.44, 0.175], facecolor=PAN)
ax_info.set_xticks([]); ax_info.set_yticks([])
for s in ax_info.spines.values(): s.set_color('#223344')
info_text = ax_info.text(0.015, 0.97, '', va='top', ha='left',
                          color='#aaffee', fontsize=8.5, wrap=False,
                          transform=ax_info.transAxes,
                          fontfamily='monospace')

# ── Fórmulas editables ──────────────────────────────────────────────
ax_bx = fig.add_axes([0.335, 0.200, 0.44, 0.028])
box_x = TextBox(ax_bx, 'X: ', initial='')
box_x.label.set_color(CYN); box_x.text_disp.set_color(GLD)
box_x.ax.set_facecolor('#060e14')

ax_by = fig.add_axes([0.335, 0.165, 0.44, 0.028])
box_y = TextBox(ax_by, 'Y: ', initial='')
box_y.label.set_color(CYN); box_y.text_disp.set_color(GLD)
box_y.ax.set_facecolor('#060e14')

# ── Sliders ─────────────────────────────────────────────────────────
def make_slider(rect, label, vmin, vmax, vinit, color):
    a = fig.add_axes(rect)
    s = Slider(a, label, vmin, vmax, valinit=vinit, color=color)
    s.label.set_color(WHT); s.label.set_fontsize(8)
    s.valtext.set_color(GLD); s.valtext.set_fontsize(8)
    return s

sl_v1   = make_slider([0.782, 0.195, 0.20, 0.022], 'v1', 0.01, 20.0, 1.0,   RED)
sl_v2   = make_slider([0.782, 0.165, 0.20, 0.022], 'v2', 0.01, 15.0, 1.0,   RED)
sl_v3   = make_slider([0.782, 0.135, 0.20, 0.022], 'v3 Fase', 0,   360, 0,   BLU)
sl_v4   = make_slider([0.782, 0.105, 0.20, 0.022], 'v4 Iter', 10,  500, 150, ORG)
sl_spd  = make_slider([0.782, 0.075, 0.20, 0.022], 'Velocidad', 1, 200, 45,  '#446644')

# ── Botones ──────────────────────────────────────────────────────────
def make_btn(rect, label, bg):
    a = fig.add_axes(rect)
    b = Button(a, label, color=bg, hovercolor='#ffffff')
    b.label.set_fontsize(8); b.label.set_color(BG)
    return b

btn_3d  = make_btn([0.782, 0.040, 0.095, 0.030], '3D Orbit',    CYN)
btn_gif = make_btn([0.882, 0.040, 0.095, 0.030], 'Exportar GIF', GLD)
btn_rst = make_btn([0.782, 0.008, 0.095, 0.028], 'Reset',        '#334455')
btn_pp  = make_btn([0.882, 0.008, 0.095, 0.028], 'Play/Pause',   '#334455')

# ═══════════════════════ ESTADO GLOBAL ═════════════════════════════
estado = {
    'frame': 0,
    'jugando': True,
    'modo': 'curva',          # 'curva' | 'especial' | 'fractal'
    'nombre': NOMBRES[0],
    'mandel_cx': -0.5, 'mandel_cy': 0.0,
    'julia_cr': -0.7,  'julia_ci':  0.27,
}
x_data = y_data = np.zeros(2)

def set_info(nombre):
    txt = INFO.get(nombre, 'v1 · v2 · v3 · v4 para explorar la forma')
    info_text.set_text(txt)

def update_slider_labels(nombre):
    labels = {
        'A03 Lissajous':       ('v1 Frec X', 'v2 Frec Y', 'v3 Fase°', 'v4 Iter'),
        'A05 Hipotrocoide':    ('v1 R.ext',  'v2 R.int',  'v3 Fase°', 'v4 Iter'),
        'B01 Flor de la Vida': ('v1 Zoom',   'v2 Capas',  'v3 Rot°',  'v4 -'),
        'B05 Merkaba Expandible':('v1 Exp',  'v2 Aura',   'v3 Rot°',  'v4 -'),
        'B06 Vortex Math 3-6-9':('v1 Radio', 'v2 -',      'v3 Fase°', 'v4 -'),
        'B10 Solidos Platonicos':('v1 Zoom',  'v2 Sólido', 'v3 Rot°',  'v4 -'),
        'C01 Mandelbrot':      ('v1 Zoom',   'v2 Iter',   'v3 Power', 'v4 -'),
        'C02 Julia Set':       ('v1 Zoom',   'v2 Iter',   'v3 c_real','v4 c_imag'),
        'C03 Newton z3-1':     ('v1 Zoom',   'v2 Iter',   'v3 -',     'v4 -'),
        'C06 Arbol Fractal':   ('v1 Altura', 'v2 Ángulo', 'v3 Asim.', 'v4 Profund'),
        'D01 Arco Parabolico': ('v1 Altura', 'v2 Ancho',  'v3 N.Arcos','v4 -'),
        'D02 Catenaria':       ('v1 Flecha', 'v2 Semi-luz','v3 N.Arcos','v4 -'),
        'D03 Trama Estructural':('v1 Módulo','v2 Filas',  'v3 Cols',  'v4 Tipo'),
        'D04 Boveda Nervada':  ('v1 Radio',  'v2 Nervios','v3 Inner%','v4 -'),
        'D05 Cercha Triangulada':('v1 Altura','v2 Módulos','v3 Tipo', 'v4 -'),
        'D06 Espiral Voronoi': ('v1 Escala', 'v2 Puntos', 'v3 Semilla','v4 -'),
    }
    lbl = labels.get(nombre, ('v1', 'v2', 'v3 Fase', 'v4 Iter'))
    sl_v1.label.set_text(lbl[0])
    sl_v2.label.set_text(lbl[1])
    sl_v3.label.set_text(lbl[2])
    sl_v4.label.set_text(lbl[3])

def clear_draw():
    """Clear ax and prepare for static drawing."""
    ax.cla()
    ax.set_facecolor(BG)
    ax.grid(color='#112233', linestyle='-', linewidth=0.4, alpha=0.6)
    ax.tick_params(colors='#223344', labelsize=7)
    for spine in ax.spines.values(): spine.set_color('#112233')

def recalcular(val=None):
    global x_data, y_data
    nombre = estado['nombre']
    modo   = MODO[nombre]
    estado['modo'] = modo

    v1 = max(1e-9, sl_v1.val)
    v2 = max(1e-9, sl_v2.val)
    v3 = sl_v3.val
    v4 = sl_v4.val

    if modo == 'curva':
        fx = box_x.text; fy = box_y.text
        t  = T_ARRAY
        xd = eval_formula(fx, t, v1, v2, v3, v4)
        yd = eval_formula(fy, t, v1, v2, v3, v4)
        valid = np.isfinite(xd) & np.isfinite(yd)
        x_data = xd[valid]; y_data = yd[valid]
        if len(x_data) < 2:
            x_data = y_data = np.zeros(2)
        mx = max(np.max(np.abs(x_data)), np.max(np.abs(y_data)), 0.1) * 1.25
        ax.set_xlim(-mx, mx); ax.set_ylim(-mx, mx)
        estado['frame'] = 0

    elif modo == 'especial':
        clear_draw()
        _dispatch_especial(nombre, v1, v2, v3, v4)
        fig.canvas.draw_idle()

    elif modo == 'fractal':
        clear_draw()
        _dispatch_fractal(nombre, v1, v2, v3, v4)
        fig.canvas.draw_idle()

    set_info(nombre)
    fig.canvas.draw_idle()

def _dispatch_especial(nombre, v1, v2, v3, v4):
    if nombre == 'B01 Flor de la Vida':    draw_flower(ax, v1, v2, v3)
    elif nombre == 'B02 Semilla de la Vida': draw_seed(ax, v1, v3)
    elif nombre == 'B03 Fruto + Metatron':   draw_fruit(ax, v1, v3)
    elif nombre == 'B04 Cubo de Metatron':   draw_metatron(ax, v1, v3)
    elif nombre == 'B05 Merkaba Expandible': draw_merkaba(ax, v1, v2, v3)
    elif nombre == 'B06 Vortex Math 3-6-9': draw_vortex369(ax, v1, v3)
    elif nombre == 'B07 Yin-Yang Tesla':     draw_yinyang(ax, v1, v2, v3)
    elif nombre == 'B08 Espiral Fibonacci':  draw_fibonacci(ax, v1, v2)
    elif nombre == 'B09 Genesis Rotaciones': draw_genesis(ax, v1, v2, v3)
    elif nombre == 'B10 Solidos Platonicos': draw_platonic(ax, v1, v2, v3)
    elif nombre == 'C04 Sierpinski':         draw_sierpinski(ax, v1, v2)
    elif nombre == 'C05 Copo de Koch':       draw_koch(ax, v1, v2)
    elif nombre == 'C06 Arbol Fractal':      draw_tree(ax, v1, v2, v4, v3)
    elif nombre == 'D01 Arco Parabolico':    draw_parabolic_arch(ax, v1, v2, v3)
    elif nombre == 'D02 Catenaria':          draw_catenary(ax, v1, v2, v3)
    elif nombre == 'D03 Trama Estructural':  draw_grid(ax, v1, v2, v3, v4)
    elif nombre == 'D04 Boveda Nervada':     draw_vault(ax, v1, v2, v3)
    elif nombre == 'D05 Cercha Triangulada': draw_truss(ax, v1, v2, v3)
    elif nombre == 'D06 Espiral Voronoi':    draw_voronoi_spiral(ax, v1, v2, v3)

def _dispatch_fractal(nombre, v1, v2, v3, v4):
    zoom  = max(0.05, v1)
    iters = max(10, int(v2))
    ax.set_aspect('equal')
    if nombre == 'C01 Mandelbrot':
        power = max(1.5, min(5.0, v3))
        img = compute_mandelbrot(estado['mandel_cx'], estado['mandel_cy'],
                                 zoom, iters, power)
        ax.imshow(img, origin='lower', cmap='inferno',
                  extent=[estado['mandel_cx']-1.8/zoom, estado['mandel_cx']+1.8/zoom,
                          estado['mandel_cy']-1.8/zoom, estado['mandel_cy']+1.8/zoom],
                  aspect='equal')
        ax.set_title(f'Mandelbrot  zoom={zoom:.1f}  iter={iters}  p={power:.1f}',
                     color=GLD, fontsize=8, pad=3)
    elif nombre == 'C02 Julia Set':
        estado['julia_cr'] = v3 if v3 != 0 else estado['julia_cr']
        estado['julia_ci'] = v4 if v4 != 0 else estado['julia_ci']
        img = compute_julia(zoom, iters, estado['julia_cr'], estado['julia_ci'])
        ax.imshow(img, origin='lower', cmap='twilight',
                  extent=[-1.8/zoom, 1.8/zoom, -1.8/zoom, 1.8/zoom], aspect='equal')
        ax.set_title(f'Julia  c={estado["julia_cr"]:.3f}+{estado["julia_ci"]:.3f}j',
                     color=GLD, fontsize=8, pad=3)
    elif nombre == 'C03 Newton z3-1':
        img = compute_newton(zoom, iters)
        ax.imshow(img, origin='lower', cmap='Spectral',
                  extent=[-2/zoom, 2/zoom, -2/zoom, 2/zoom], aspect='equal')
        ax.set_title('Newton  z³ − 1 = 0  (3 cuencas de atracción)',
                     color=GLD, fontsize=8, pad=3)

def al_cambiar_menu(label):
    estado['nombre'] = label
    modo = MODO[label]
    if modo == 'curva':
        box_x.set_val(FX_DEF[label])
        box_y.set_val(FY_DEF[label])
    elif modo in ('especial', 'fractal'):
        box_x.set_val('— especial —')
        box_y.set_val('— usa sliders —')
    # Reset fractal zoom
    if label == 'C01 Mandelbrot':
        estado['mandel_cx'] = -0.5; estado['mandel_cy'] = 0.0
    update_slider_labels(label)
    recalcular()

# ─── Mouse click para fractales ─────────────────────────────────────
def on_click(event):
    if event.inaxes != ax or event.xdata is None:
        return
    nombre = estado['nombre']
    if nombre == 'C01 Mandelbrot':
        estado['mandel_cx'] = event.xdata
        estado['mandel_cy'] = event.ydata
        recalcular()
    elif nombre == 'C02 Julia Set':
        estado['julia_cr'] = event.xdata
        estado['julia_ci'] = event.ydata
        recalcular()

fig.canvas.mpl_connect('button_press_event', on_click)

# ═══════════════════════ 3D ORBIT ══════════════════════════════════
def mostrar_3d(event):
    nombre = estado['nombre']
    modo   = MODO[nombre]
    fig3d  = plt.figure(figsize=(11, 11), facecolor=BG)
    fig3d.canvas.manager.set_window_title('ArquiMath 3D Orbit')
    ax3d = fig3d.add_subplot(111, projection='3d')
    ax3d.set_facecolor(BG)
    ax3d.xaxis.set_pane_color((0,0,0,0))
    ax3d.yaxis.set_pane_color((0,0,0,0))
    ax3d.zaxis.set_pane_color((0,0,0,0))
    ax3d.tick_params(colors='#334455', labelsize=7)

    v1, v2, v3 = sl_v1.val, sl_v2.val, sl_v3.val

    if nombre == 'B10 Solidos Platonicos':
        idx = int(v2) % 5
        name, verts, edges = PLATONIC_DATA[idx]
        verts_s = verts * v1
        ax3d.set_title(name, color=GLD, fontsize=12)
        def upd3d(f):
            ax3d.cla()
            ax3d.set_facecolor(BG)
            xp, yp, zp = (verts_s @ np.array([[np.cos(np.deg2rad(f)),0,np.sin(np.deg2rad(f))],
                                               [0,1,0],
                                               [-np.sin(np.deg2rad(f)),0,np.cos(np.deg2rad(f))]])).T
            for e in edges:
                ax3d.plot([xp[e[0]], xp[e[1]]], [yp[e[0]], yp[e[1]]], [zp[e[0]], zp[e[1]]],
                          color=CYN, lw=1.8, alpha=0.85)
            ax3d.scatter(xp, yp, zp, color=GLD, s=30, zorder=5)
        ani3d = animation.FuncAnimation(fig3d, upd3d, frames=360,
                                        interval=25, blit=False)
    elif modo == 'curva' and len(x_data) > 1:
        z3d = np.linspace(0, 12, len(x_data))
        line3d, = ax3d.plot([], [], [], color=CYN, lw=2)
        pt3d,   = ax3d.plot([], [], [], 'o', color=WHT, markersize=8)
        ax3d.set_xlim(x_data.min(), x_data.max())
        ax3d.set_ylim(y_data.min(), y_data.max())
        ax3d.set_zlim(0, 12)
        def upd3d(f):
            idx = min(f*50, len(x_data)-1)
            line3d.set_data_3d(x_data[:idx], y_data[:idx], z3d[:idx])
            if idx > 0:
                pt3d.set_data_3d([x_data[idx]], [y_data[idx]], [z3d[idx]])
            ax3d.view_init(elev=28, azim=f*1.8)
            return line3d, pt3d
        ani3d = animation.FuncAnimation(fig3d, upd3d, frames=400,
                                        interval=22, blit=False)
    else:
        th = np.linspace(0, 4*np.pi, 800)
        ax3d.plot(np.cos(th), np.sin(th), th/4, color=CYN, lw=2)
        ax3d.set_title('Vista 3D general', color=GLD)
        def upd3d(f):
            ax3d.view_init(elev=28, azim=f*2)
        ani3d = animation.FuncAnimation(fig3d, upd3d, frames=180,
                                        interval=30, blit=False)
    plt.show()

# ═══════════════════════ EXPORTAR GIF ══════════════════════════════
def exportar_gif(event):
    if not HAS_IMAGEIO:
        print("[ArquiMath] Instala imageio: pip install imageio")
        return
    nombre = estado['nombre'].replace(' ','_')
    path   = f'ArquiMath_v11_{nombre}.gif'
    print(f'[ArquiMath] Generando GIF → {path} ...')
    frames = []
    old_frame = estado['frame']
    estado['jugando'] = False
    n_frames = 80
    for i in range(n_frames):
        idx = int(i * len(x_data) / n_frames)
        if len(x_data) > 1:
            rastro.set_data(x_data[:idx], y_data[:idx])
        fig.canvas.draw()
        buf = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        buf = buf.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        frames.append(buf)
    imageio.mimsave(path, frames, fps=25, loop=0)
    estado['frame'] = old_frame
    estado['jugando'] = True
    print(f'[ArquiMath] GIF guardado: {path}')

# ═══════════════════════ ANIMACIÓN ═════════════════════════════════
def actualizar(frame):
    if estado['modo'] != 'curva':
        return rastro, puntero, brazo
    if estado['jugando']:
        estado['frame'] += int(sl_spd.val)
    idx = min(estado['frame'], len(x_data)-1)
    if idx < 1:
        return rastro, puntero, brazo
    rastro.set_data(x_data[:idx], y_data[:idx])
    puntero.set_data([x_data[idx]], [y_data[idx]])
    brazo.set_data([0, x_data[idx]], [0, y_data[idx]])
    return rastro, puntero, brazo

ani = animation.FuncAnimation(fig, actualizar, interval=16,
                               blit=True, cache_frame_data=False)

# ═══════════════════════ CONEXIONES ════════════════════════════════
radio_menu.on_clicked(al_cambiar_menu)
sl_v1.on_changed(recalcular)
sl_v2.on_changed(recalcular)
sl_v3.on_changed(recalcular)
sl_v4.on_changed(recalcular)
box_x.on_submit(recalcular)
box_y.on_submit(recalcular)
btn_3d.on_clicked(mostrar_3d)
btn_gif.on_clicked(exportar_gif)
btn_pp.on_clicked(lambda e: estado.update({'jugando': not estado['jugando']}))
btn_rst.on_clicked(lambda e: estado.update({'frame': 0}))

# ═══════════════════════ STARTUP ═══════════════════════════════════
al_cambiar_menu(NOMBRES[0])
plt.show()
