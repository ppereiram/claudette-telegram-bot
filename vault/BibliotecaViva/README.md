# 📚 BIBLIOTECA VIVA
### Sistema de extracción de conocimiento para 2,053 obras
> Pablo Pereira Magnere | Costa Rica | Febrero 2026

---

## Estructura del proyecto

```
biblioteca-viva/
├── biblioteca.py          ← Motor principal (Claude Code)
├── tags-master.md         ← Ontología controlada — NO modificar sin actualizar aquí
├── template-libro.md      ← Template MD para Obsidian
├── prompts-maestros.md    ← 3 prompts por nivel + 2 especiales
├── biblioteca.db          ← SQLite (se crea automático)
└── README.md              ← Este archivo

vault-obsidian/
├── biblioteca/
│   ├── filosofia/         ← 895 libros
│   ├── literatura/        ← 423 libros
│   ├── ciencias/          ← 42 libros
│   ├── ciencias-sociales/ ← 100 libros
│   ├── interesantes/      ← 523 libros
│   └── self-help/         ← 46 libros
├── conexiones/            ← Mapas temáticos cruzados
└── autores/               ← Fichas de autor (corpus grandes)
```

---

## Instalación

```bash
# 1. Instalar dependencias
pip install anthropic pypdf ebooklib beautifulsoup4

# 2. Configurar variables de entorno
export ANTHROPIC_API_KEY="tu-clave"
export OBSIDIAN_VAULT="/ruta/a/tu/vault"
export BOOKS_PATH="/ruta/a/tus/libros"

# 3. Inicializar DB con el índice
python biblioteca.py init --indice "indice-biblioteca.md"

# 4. Ver estadísticas
python biblioteca.py stats
```

---

## Uso

### Procesar un libro específico
```bash
python biblioteca.py libro --id 42
python biblioteca.py libro --id 42 --nivel A   # forzar nivel A
```

### Ver qué se procesaría (sin ejecutar)
```bash
python biblioteca.py batch --nivel C --limite 50 --dry-run
```

### Batch por nivel
```bash
# Primero los núcleo (A) — ~150 libros, supervisar
python biblioteca.py batch --nivel A --limite 10

# Luego importantes (B) — ~700 libros, semi-automático
python biblioteca.py batch --nivel B --limite 50

# Finalmente el resto (C) — 1000+, automático
python biblioteca.py batch --nivel C --limite 100
```

---

## Estrategia de procesamiento recomendada

### Semana 1: Validación (manual en claude.ai)
Procesar 3-5 libros Nivel A manualmente aquí para validar que el template y los prompts dan la calidad esperada. Candidatos:
- *Psicopolítica* — Byung-Chul Han (tu autor más central)
- *La era del capitalismo de la vigilancia* — Zuboff
- *Vidas desperdiciadas* — Bauman
- *Realismo capitalista* — Mark Fisher
- *La gravedad y la gracia* — Simone Weil

### Semana 2: Nivel A completo con Claude Code
~150 libros núcleo. Supervisar los primeros 20, luego dejar correr.

### Semana 3-4: Nivel B
~700 libros. Batch de 50 por sesión. Revisar muestra aleatoria.

### Mes 2: Nivel C masivo
~1,000 libros. Batch de 100. Automático con revisión de stats.

### Mes 3: Fichas de autor + mapas de conexiones
Usar prompts especiales para corpus grandes (Jung, Dick, Clarke, Zweig, Mann).

---

## Integración con Claudette

Una vez procesados 200+ libros, agregar a Claudette este sistema:

```python
# En el sistema de Claudette
def buscar_en_biblioteca(query: str) -> list[dict]:
    """Busca libros relevantes en la biblioteca de Pablo."""
    conn = sqlite3.connect("biblioteca.db")
    # Búsqueda por tags, autor, o texto en notas
    results = conn.execute("""
        SELECT title, author, md_path, tags
        FROM books 
        WHERE processed=1 
        AND (tags LIKE ? OR title LIKE ? OR author LIKE ?)
        LIMIT 5
    """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
    
    # Leer los MDs relevantes para contexto
    context = []
    for title, author, md_path, tags in results:
        if md_path and Path(md_path).exists():
            content = Path(md_path).read_text()[:2000]  # Primeras 2000 chars
            context.append({"title": title, "author": author, "content": content})
    
    return context
```

---

## Preguntas que Claudette podrá responder

Una vez con la biblioteca procesada:

- *"¿Qué libros de mi biblioteca hablan de biopoder?"* → query por `#biopoder`
- *"Construye una conversación entre Baudrillard y Philip K. Dick sobre la simulación"*
- *"¿Qué pensaría Simone Weil sobre el capitalismo de vigilancia de Zuboff?"*
- *"Dame los 5 libros más críticos del neoliberalismo que tengo"*
- *"¿Dónde están las tensiones no resueltas entre Han y Bauman?"*
- *"Recomiéndame el próximo libro a leer dado que acabo de terminar Psicopolítica"*

---

## Mantenimiento

- **Agregar tags nuevos**: editar `tags-master.md` primero, luego usar en MDs
- **Actualizar un MD**: editar directamente en Obsidian, marcar en DB si cambia
- **Nuevos libros**: `INSERT INTO books (title, author, ...)` + `python biblioteca.py libro --id nuevo_id`

---

*Sistema diseñado por Pablo Pereira Magnere + Claude | Biblioteca Viva v1.0*
