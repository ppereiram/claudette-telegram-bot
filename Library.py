"""
Library Manager para Claudette Bot.
Almacena y busca en la biblioteca de 2100+ libros de Pablo.
Los extractos de Obsidian se indexan en PostgreSQL con búsqueda full-text.
"""

import logging
import re

logger = logging.getLogger("claudette")

# --- Conexión PostgreSQL ---
_pg_conn_string = None

try:
    from config import DATABASE_URL
    if DATABASE_URL:
        import psycopg2
        _pg_conn_string = DATABASE_URL
except Exception as e:
    logger.warning(f"Library: No PostgreSQL disponible: {e}")


def _get_conn():
    import psycopg2
    return psycopg2.connect(_pg_conn_string)


# =====================================================
# SETUP DE TABLA
# =====================================================

def setup_library_table():
    """Crea la tabla library con índices de búsqueda full-text."""
    if not _pg_conn_string:
        logger.warning("Library: Sin PostgreSQL, no se puede crear tabla")
        return False
    try:
        conn = _get_conn()
        cur = conn.cursor()

        # Tabla principal
        cur.execute("""
            CREATE TABLE IF NOT EXISTS library (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                category TEXT,
                subcategory TEXT,
                tags TEXT[],
                summary TEXT,
                content TEXT,
                filename TEXT,
                drive_path TEXT,
                word_count INTEGER DEFAULT 0,
                fts_vector TSVECTOR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índice GIN sobre la columna precalculada
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_library_fts 
            ON library USING GIN (fts_vector)
        """)

        # Índices adicionales
        cur.execute("CREATE INDEX IF NOT EXISTS idx_library_author ON library (LOWER(author))")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_library_category ON library (LOWER(category))")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_library_tags ON library USING GIN (tags)")

        conn.commit()
        cur.close()
        conn.close()
        logger.info("📚 Tabla library verificada/creada con índices FTS")
        return True
    except Exception as e:
        logger.error(f"Error creando tabla library: {e}")
        return False


# =====================================================
# PARSING DE ARCHIVOS OBSIDIAN
# =====================================================

def parse_obsidian_md(content, filename=""):
    """
    Parsea un archivo .md de Obsidian extrayendo frontmatter y contenido.
    Soporta tanto YAML frontmatter como properties de Obsidian.
    """
    result = {
        'title': '',
        'author': '',
        'tags': [],
        'content': '',
        'summary': ''
    }

    lines = content.split('\n')
    body_start = 0

    # --- Detectar frontmatter YAML (--- ... ---) ---
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                body_start = i + 1
                frontmatter = '\n'.join(lines[1:i])
                _parse_frontmatter(frontmatter, result)
                break

    # --- Detectar Obsidian properties (key:: value) ---
    elif lines:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if '::' in stripped:
                key, _, val = stripped.partition('::')
                key = key.strip().lower()
                val = val.strip()
                if key == 'tags':
                    result['tags'] = _parse_tags(val)
                elif key == 'author' or key == 'autor':
                    result['author'] = val
                body_start = i + 1
            elif stripped.startswith('#') or stripped == '' or not stripped:
                if any('::' in lines[j] for j in range(i + 1, min(i + 5, len(lines)))):
                    continue
                body_start = i
                break
            else:
                body_start = i
                break

    # --- Extraer contenido ---
    body = '\n'.join(lines[body_start:]).strip()
    result['content'] = body

    # --- Título: del H1, del frontmatter, o del filename ---
    if not result['title']:
        h1_match = re.search(r'^#\s+(.+)', body, re.MULTILINE)
        if h1_match:
            result['title'] = h1_match.group(1).strip()

    if not result['title'] and filename:
        # "0225 - Infocracia.md" → "Infocracia"
        name = filename.replace('.md', '')
        name = re.sub(r'^\d+\s*[-–]\s*', '', name)
        result['title'] = name.strip()

    # --- Summary: primeras ~500 chars del contenido ---
    if body:
        clean_body = re.sub(r'^#+\s+.+\n?', '', body)  # Quitar headings
        clean_body = re.sub(r'\[.*?\]\(.*?\)', '', clean_body)  # Quitar links
        clean_body = clean_body.strip()
        result['summary'] = clean_body[:500] + ('...' if len(clean_body) > 500 else '')

    return result


def _parse_frontmatter(fm_text, result):
    """Parsea YAML frontmatter simple."""
    for line in fm_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, _, val = line.partition(':')
            key = key.strip().lower()
            val = val.strip().strip('"').strip("'")

            if key == 'title' or key == 'titulo':
                result['title'] = val
            elif key == 'author' or key == 'autor':
                result['author'] = val
            elif key == 'tags':
                result['tags'] = _parse_tags(val)


def _parse_tags(val):
    """Parsea tags en varios formatos: [tag1, tag2], tag1 tag2, #tag1 #tag2."""
    val = val.strip('[]')
    # Separar por comas o espacios
    tags = re.split(r'[,\s]+', val)
    # Limpiar
    return [t.strip().strip('#').strip('"').strip("'").lower()
            for t in tags if t.strip() and t.strip() not in ('×', 'x', '-')]


# =====================================================
# CRUD
# =====================================================

def add_book(title, author, category, subcategory, tags, content, summary="",
             filename="", drive_path=""):
    """Agrega un libro a la biblioteca."""
    if not _pg_conn_string:
        return None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        word_count = len(content.split()) if content else 0
        cur.execute("""
            INSERT INTO library (title, author, category, subcategory, tags, content, 
                                 summary, filename, drive_path, word_count, fts_vector)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    to_tsvector('spanish',
                        COALESCE(%s, '') || ' ' || COALESCE(%s, '') || ' ' ||
                        COALESCE(%s, '') || ' ' || COALESCE(%s, '')
                    ))
            RETURNING id
        """, (title, author, category, subcategory, tags, content,
              summary, filename, drive_path, word_count,
              title, author, content, ' '.join(tags) if tags else ''))
        book_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return book_id
    except Exception as e:
        logger.error(f"Error adding book: {e}")
        return None


def get_library_stats():
    """Estadísticas de la biblioteca."""
    if not _pg_conn_string:
        return "Biblioteca no disponible (sin PostgreSQL)"
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM library")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT author) FROM library WHERE author IS NOT NULL AND author != ''")
        authors = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT category) FROM library WHERE category IS NOT NULL AND category != ''")
        categories = cur.fetchone()[0]
        cur.execute("SELECT SUM(word_count) FROM library")
        total_words = cur.fetchone()[0] or 0
        cur.close()
        conn.close()
        return (f"📚 Biblioteca: {total} libros, {authors} autores, "
                f"{categories} categorías, ~{total_words:,} palabras totales")
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return f"Error: {e}"


# =====================================================
# BÚSQUEDA
# =====================================================

def search_library(query, limit=5):
    """
    Búsqueda inteligente en la biblioteca usando full-text search de PostgreSQL.
    Busca en título, autor, contenido y tags simultáneamente.
    Retorna los extractos más relevantes.
    """
    if not _pg_conn_string:
        return "Biblioteca no disponible."
    try:
        conn = _get_conn()
        cur = conn.cursor()

        # Full-text search con ranking
        cur.execute("""
            SELECT title, author, category, tags, summary, content,
                   ts_rank(fts_vector, plainto_tsquery('spanish', %s)) AS rank
            FROM library
            WHERE fts_vector @@ plainto_tsquery('spanish', %s)
            ORDER BY rank DESC
            LIMIT %s
        """, (query, query, limit))

        results = cur.fetchall()
        cur.close()
        conn.close()

        if not results:
            # Fallback: búsqueda ILIKE más tolerante
            return _search_fallback(query, limit)

        output = []
        for row in results:
            title, author, category, tags, summary, content, rank = row
            tags_str = ', '.join(tags) if tags else ''

            # Extracto relevante: buscar párrafo que contenga la query
            excerpt = _find_relevant_excerpt(content, query)

            entry = f"📖 **{title}**"
            if author:
                entry += f" — {author}"
            if category:
                entry += f" [{category}]"
            if tags_str:
                entry += f"\n🏷️ {tags_str}"
            entry += f"\n{excerpt}"

            output.append(entry)

        return "\n\n---\n\n".join(output)

    except Exception as e:
        logger.error(f"Library search error: {e}")
        return f"Error buscando en biblioteca: {e}"


def search_by_author(author_name, limit=10):
    """Buscar todos los libros de un autor."""
    if not _pg_conn_string:
        return "Biblioteca no disponible."
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT title, author, category, tags, summary
            FROM library
            WHERE LOWER(author) LIKE LOWER(%s)
            ORDER BY title
            LIMIT %s
        """, (f'%{author_name}%', limit))

        results = cur.fetchall()
        cur.close()
        conn.close()

        if not results:
            return f"No encontré libros de '{author_name}' en la biblioteca."

        output = [f"📚 Libros de {results[0][1]}:\n"]
        for title, author, category, tags, summary in results:
            tags_str = ', '.join(tags[:5]) if tags else ''
            output.append(f"• **{title}** [{category}] — {tags_str}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Author search error: {e}")
        return f"Error: {e}"


def search_by_tag(tag, limit=10):
    """Buscar libros por tag."""
    if not _pg_conn_string:
        return "Biblioteca no disponible."
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT title, author, category, tags, summary
            FROM library
            WHERE %s = ANY(tags)
            ORDER BY title
            LIMIT %s
        """, (tag.lower().strip(), limit))

        results = cur.fetchall()
        cur.close()
        conn.close()

        if not results:
            return f"No encontré libros con tag '{tag}'."

        output = [f"🏷️ Libros con tag '{tag}' ({len(results)} encontrados):\n"]
        for title, author, category, tags, summary in results:
            output.append(f"• **{title}** — {author or 'S/A'} [{category}]")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Tag search error: {e}")
        return f"Error: {e}"


def get_book_content(title_query):
    """Obtener el contenido completo de un libro específico."""
    if not _pg_conn_string:
        return "Biblioteca no disponible."
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT title, author, category, tags, content
            FROM library
            WHERE LOWER(title) LIKE LOWER(%s)
            ORDER BY title
            LIMIT 1
        """, (f'%{title_query}%',))

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return f"No encontré '{title_query}' en la biblioteca."

        title, author, category, tags, content = row
        tags_str = ', '.join(tags) if tags else ''

        header = f"📖 {title}"
        if author:
            header += f" — {author}"
        if tags_str:
            header += f"\n🏷️ {tags_str}"

        # Limitar contenido para no explotar el contexto
        if len(content) > 8000:
            content = content[:8000] + "\n\n[... Contenido truncado. Pedí una sección específica.]"

        return f"{header}\n\n{content}"

    except Exception as e:
        logger.error(f"Get book error: {e}")
        return f"Error: {e}"


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def _find_relevant_excerpt(content, query, max_chars=600):
    """Encuentra el párrafo más relevante del contenido para la query."""
    if not content:
        return ""

    query_words = query.lower().split()
    paragraphs = content.split('\n\n')

    best_para = ""
    best_score = 0

    for para in paragraphs:
        para_clean = para.strip()
        if len(para_clean) < 30:
            continue
        para_lower = para_clean.lower()
        score = sum(1 for w in query_words if w in para_lower)
        if score > best_score:
            best_score = score
            best_para = para_clean

    if not best_para and paragraphs:
        # Si no hay match, tomar el primer párrafo sustancial
        for para in paragraphs:
            if len(para.strip()) > 50:
                best_para = para.strip()
                break

    if len(best_para) > max_chars:
        best_para = best_para[:max_chars] + "..."

    return best_para


def _search_fallback(query, limit):
    """Búsqueda fallback con ILIKE cuando full-text no encuentra nada."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT title, author, category, tags, summary, content
            FROM library
            WHERE LOWER(title) LIKE LOWER(%s)
               OR LOWER(author) LIKE LOWER(%s)
               OR LOWER(content) LIKE LOWER(%s)
               OR LOWER(array_to_string(tags, ' ')) LIKE LOWER(%s)
            ORDER BY title
            LIMIT %s
        """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit))

        results = cur.fetchall()
        cur.close()
        conn.close()

        if not results:
            return f"No encontré nada sobre '{query}' en la biblioteca de 2100 libros."

        output = []
        for title, author, category, tags, summary, content in results:
            tags_str = ', '.join(tags) if tags else ''
            excerpt = _find_relevant_excerpt(content, query)
            entry = f"📖 **{title}**"
            if author:
                entry += f" — {author}"
            if tags_str:
                entry += f"\n🏷️ {tags_str}"
            entry += f"\n{excerpt}"
            output.append(entry)

        return "\n\n---\n\n".join(output)

    except Exception as e:
        return f"Error en búsqueda: {e}"


# --- Auto-crear tabla al importar ---
if _pg_conn_string:
    setup_library_table()
