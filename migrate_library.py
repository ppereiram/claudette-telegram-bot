#!/usr/bin/env python3
"""
migrate_library.py — Carga la biblioteca completa a PostgreSQL de Claudette.

FUENTES:
  1. Fichas Obsidian (.md) con análisis completo — ~300 libros
  2. biblioteca.db (SQLite local) — catálogo completo ~2052 libros

USO:
  python migrate_library.py /ruta/a/vault/Biblioteca [/ruta/a/biblioteca.db]

  O con DATABASE_URL explícito:
  DATABASE_URL="postgresql://user:pass@host/db" python migrate_library.py ./Biblioteca ./biblioteca.db

ESTRUCTURA REAL DEL VAULT (soporte multi-nivel):
  Biblioteca/
  ├── Filosofia/                   ← sección
  │   ├── Byung-Chul Han/          ← autor
  │   │   └── 0225 - Infocracia.md
  ├── Humanidades/                 ← sección
  │   ├── Filosofia/               ← sub-sección
  │   │   ├── Jean Baudrillard/    ← autor
  │   │   │   └── 0571 - Contrasenas.md
  │   ├── Steven Pinker/           ← autor directo en sección
  │   │   └── 0300 - Enlightenment Now.md
  │   ├── Ciencias-Sociales/       ← sub-sección
  │   │   └── Nassim Taleb/
  │   │       └── 0100 - El Cisne Negro.md
"""

import os
import sys
import re
import logging
import time
import sqlite3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("migrate")

# --- PostgreSQL ---
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_URL = os.environ.get('DATABASE_URL')
    except ImportError:
        pass

if not DATABASE_URL:
    print("ERROR: Necesitas DATABASE_URL como variable de entorno.")
    print("   Ejemplo: DATABASE_URL='postgresql://user:pass@host/db' python migrate_library.py ./Biblioteca")
    sys.exit(1)

import psycopg2


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def setup_table():
    """Crea la tabla library con esquema ampliado."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS library")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS library (
            id SERIAL PRIMARY KEY,
            biblioteca_id INTEGER,          -- ID en biblioteca.db (si existe)
            title TEXT NOT NULL,
            author TEXT,
            year INTEGER,
            genre TEXT,
            category TEXT,                  -- seccion top-level (Filosofia, Humanidades...)
            subcategory TEXT,               -- sub-seccion (Ciencias-Sociales, Filosofia...)
            nivel CHAR(1),                  -- A, B, C, D
            has_ficha BOOLEAN DEFAULT FALSE, -- tiene ficha MD detallada
            pablo_rating INTEGER,           -- rating personal 1-10
            tags TEXT[],
            summary TEXT,
            content TEXT,                   -- contenido completo de la ficha MD
            filename TEXT,
            file_path TEXT,                 -- ruta al epub/pdf original
            word_count INTEGER DEFAULT 0,
            fts_vector TSVECTOR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_fts ON library USING GIN (fts_vector)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_author ON library (LOWER(author))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_category ON library (LOWER(category))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_tags ON library USING GIN (tags)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_nivel ON library (nivel)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_has_ficha ON library (has_ficha)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_biblioteca_id ON library (biblioteca_id)")

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Tabla library creada con indices FTS ampliados")


# =====================================================
# PARSEO DE FICHAS OBSIDIAN (.md)
# =====================================================

def parse_tags(val):
    """Parsea tags de Obsidian en varios formatos."""
    if not val:
        return []
    val = val.strip('[]')
    tags = re.split(r'[,\s]+', val)
    return [t.strip().strip('#').strip('"').strip("'").lower()
            for t in tags if t.strip() and len(t.strip()) > 1]


def parse_yaml_frontmatter(content):
    """Extrae YAML frontmatter completo del archivo .md."""
    meta = {}
    tags = []
    body_start = 0

    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return meta, tags, 0

    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            body_start = i + 1
            break

    yaml_block = '\n'.join(lines[1:body_start - 1])

    # Extraer campos clave
    for line in yaml_block.split('\n'):
        line = line.strip()
        if ':' not in line:
            continue
        key, _, val = line.partition(':')
        key = key.strip().lower()
        val = val.strip()

        if key == 'title':
            meta['title'] = val.strip('"\'')
        elif key == 'author':
            meta['author'] = val.strip('"\'')
        elif key == 'year':
            try:
                meta['year'] = int(val)
            except ValueError:
                pass
        elif key == 'genre':
            meta['genre'] = val.strip('"\'')
        elif key == 'pablo_rating':
            try:
                meta['pablo_rating'] = int(val)
            except ValueError:
                pass
        elif key == 'tags':
            tags = parse_tags(val)

    # Tags en formato YAML lista (- #tag)
    if not tags:
        tag_matches = re.findall(r'^\s+-\s+#?(\S+)', yaml_block, re.MULTILINE)
        tags = [t.lower().strip('#') for t in tag_matches if len(t) > 1]

    return meta, tags, body_start


def path_to_category_info(filepath, vault_root):
    """
    Extrae categoria, subcategoria y autor de la ruta del archivo.

    Soporta:
      vault/Filosofia/Autor/libro.md        -> cat=Filosofia, sub='', author=Autor
      vault/Humanidades/Filosofia/Autor/libro.md -> cat=Humanidades, sub=Filosofia, author=Autor
      vault/Humanidades/Autor/libro.md      -> cat=Humanidades, sub='', author=Autor
    """
    rel = os.path.relpath(filepath, vault_root)
    parts = rel.replace('\\', '/').split('/')

    if len(parts) == 2:
        # categoria/libro.md — sin autor
        return parts[0], '', ''
    elif len(parts) == 3:
        # categoria/autor/libro.md
        return parts[0], '', parts[1]
    elif len(parts) == 4:
        # categoria/subcategoria/autor/libro.md
        return parts[0], parts[1], parts[2]
    else:
        # mas profundo — tomar los ultimos 3 antes del archivo
        return parts[-4], parts[-3], parts[-2]


def scan_vault(vault_path):
    """
    Escanea el vault recursivamente, soportando estructura multi-nivel.
    Retorna lista de dicts con metadata de cada ficha.
    """
    books = []

    for root, dirs, files in os.walk(vault_path):
        # Ignorar carpetas ocultas y especiales
        dirs[:] = [d for d in sorted(dirs)
                   if not d.startswith('.') and not d.startswith('_')
                   and d not in ('mapas', 'varios', 'desktop.ini')]

        for filename in sorted(files):
            if not filename.endswith('.md'):
                continue

            filepath = os.path.join(root, filename)
            category, subcategory, author = path_to_category_info(filepath, vault_path)

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"  No pude leer {filepath}: {e}")
                continue

            if not content.strip():
                continue

            meta, tags, body_start = parse_yaml_frontmatter(content)
            lines = content.split('\n')
            body = '\n'.join(lines[body_start:]).strip()

            # Titulo: del YAML, del H1, o del nombre de archivo
            title = meta.get('title', '')
            if not title:
                h1_match = re.search(r'^#\s+(.+)', body, re.MULTILINE)
                if h1_match:
                    title = re.sub(r'\*+', '', h1_match.group(1)).strip()
                    title = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', title).strip()
            if not title:
                name = filename.replace('.md', '')
                title = re.sub(r'^\d+\s*[-–—]\s*', '', name).strip()

            # Author: del YAML o de la carpeta
            book_author = meta.get('author', '') or author

            # Summary: primeros 500 chars del cuerpo sin el primer heading
            clean_body = re.sub(r'^#+\s+.+\n?', '', body, count=1).strip()
            summary = clean_body[:500] + ('...' if len(clean_body) > 500 else '')

            # Nivel del tag
            nivel = None
            for t in tags:
                if t in ('nivel-a', 'nivel_a'):
                    nivel = 'A'
                elif t in ('nivel-b', 'nivel_b'):
                    nivel = 'B'
                elif t in ('nivel-c', 'nivel_c'):
                    nivel = 'C'

            books.append({
                'title': title,
                'author': book_author,
                'year': meta.get('year'),
                'genre': meta.get('genre', ''),
                'category': category,
                'subcategory': subcategory,
                'nivel': nivel,
                'pablo_rating': meta.get('pablo_rating'),
                'has_ficha': True,
                'tags': tags,
                'summary': summary,
                'content': body,
                'filename': filename,
                'word_count': len(body.split()),
            })

    logger.info(f"Fichas encontradas en vault: {len(books)}")
    return books


# =====================================================
# IMPORTAR DESDE biblioteca.db (catalogo completo)
# =====================================================

def load_from_sqlite(db_path, ficha_titles):
    """
    Carga libros de biblioteca.db que NO tienen ficha MD todavia.
    ficha_titles: set de titulos ya cargados desde el vault.
    """
    if not os.path.exists(db_path):
        logger.warning(f"biblioteca.db no encontrado en: {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, title, author, year, genre, section, file_path,
                   level, pablo_rating, tags, notes
            FROM books
        """)
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        logger.warning(f"Error leyendo biblioteca.db: {e}")
        conn.close()
        return []

    conn.close()

    books = []
    skipped = 0

    for row in rows:
        title = (row['title'] or '').strip()
        author = (row['author'] or '').strip()

        # Si ya tenemos ficha, saltear (se cargo desde vault)
        key = f"{title.lower()}|{author.lower()}"
        if key in ficha_titles:
            skipped += 1
            continue

        # Parsear tags (guardados como string separado por comas o JSON)
        tags_raw = row['tags'] or ''
        tags = []
        if tags_raw:
            # Puede ser "tag1, tag2" o "#tag1 #tag2"
            tags = [t.strip().strip('#').lower()
                    for t in re.split(r'[,\s]+', tags_raw)
                    if t.strip() and len(t.strip()) > 1]

        nivel = (row['level'] or '').upper() or None
        if nivel and nivel not in ('A', 'B', 'C', 'D'):
            nivel = None

        # Seccion del path en biblioteca.db
        section = row['section'] or ''
        category = section
        subcategory = ''

        # Summary minimo desde notes
        notes = row['notes'] or ''
        summary = notes[:500] if notes else f"{title} — {author}"

        books.append({
            'biblioteca_id': row['id'],
            'title': title,
            'author': author,
            'year': row['year'],
            'genre': row['genre'] or '',
            'category': category,
            'subcategory': subcategory,
            'nivel': nivel,
            'pablo_rating': row['pablo_rating'],
            'has_ficha': False,
            'tags': tags,
            'summary': summary,
            'content': '',
            'filename': os.path.basename(row['file_path'] or ''),
            'file_path': row['file_path'] or '',
            'word_count': 0,
        })

    logger.info(f"Libros de biblioteca.db sin ficha: {len(books)} (omitidos por ficha existente: {skipped})")
    return books


# =====================================================
# INSERCION EN POSTGRESQL
# =====================================================

def insert_books(books, batch_size=50):
    """Inserta libros en PostgreSQL en batches."""
    conn = get_conn()
    cur = conn.cursor()

    logger.info(f"Insertando {len(books)} libros...")

    inserted = 0
    errors = 0

    for i in range(0, len(books), batch_size):
        batch = books[i:i + batch_size]
        for book in batch:
            try:
                # Construir texto para FTS
                fts_text = ' '.join(filter(None, [
                    book.get('title', ''),
                    book.get('author', ''),
                    book.get('genre', ''),
                    book.get('content', ''),
                    ' '.join(book.get('tags', [])),
                    book.get('summary', ''),
                ]))

                cur.execute("""
                    INSERT INTO library (
                        biblioteca_id, title, author, year, genre,
                        category, subcategory, nivel, has_ficha, pablo_rating,
                        tags, summary, content, filename, file_path,
                        word_count, fts_vector
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, to_tsvector('spanish', %s)
                    )
                """, (
                    book.get('biblioteca_id'),
                    book['title'],
                    book.get('author', ''),
                    book.get('year'),
                    book.get('genre', ''),
                    book.get('category', ''),
                    book.get('subcategory', ''),
                    book.get('nivel'),
                    book.get('has_ficha', False),
                    book.get('pablo_rating'),
                    book.get('tags', []),
                    book.get('summary', ''),
                    book.get('content', ''),
                    book.get('filename', ''),
                    book.get('file_path', ''),
                    book.get('word_count', 0),
                    fts_text[:100000],  # limitar para no exceder columna tsvector
>>>>>>> 4953c00 (Migración ampliada: vault multi-nivel + catálogo completo biblioteca.db)
                ))
                inserted += 1
            except Exception as e:
                logger.warning(f"  Error insertando '{book.get('title', '?')}': {e}")
                conn.rollback()
                errors += 1

        conn.commit()
        if (i // batch_size + 1) % 5 == 0 or i + batch_size >= len(books):
            logger.info(f"  {min(i + batch_size, len(books))}/{len(books)} procesados...")

    cur.close()
    conn.close()
    return inserted, errors


def print_stats():
    """Muestra estadisticas post-migracion."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM library")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM library WHERE has_ficha = TRUE")
    with_ficha = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT LOWER(author)) FROM library WHERE author != ''")
    authors = cur.fetchone()[0]
    cur.execute("SELECT SUM(word_count) FROM library")
    words = cur.fetchone()[0] or 0
    cur.execute("SELECT nivel, COUNT(*) FROM library WHERE nivel IS NOT NULL GROUP BY nivel ORDER BY nivel")
    niveles = cur.fetchall()
    cur.execute("""
        SELECT category, COUNT(*) as cnt
        FROM library
        WHERE category != ''
        GROUP BY category ORDER BY cnt DESC
    """)
    cats = cur.fetchall()
    cur.execute("""
        SELECT LOWER(author), COUNT(*) as cnt
        FROM library
        WHERE author != ''
        GROUP BY LOWER(author)
        ORDER BY cnt DESC LIMIT 10
    """)
    top_authors = cur.fetchall()

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("MIGRACION COMPLETA")
    print("=" * 60)
    print(f"  Total libros:         {total:,}")
    print(f"  Con ficha MD:         {with_ficha:,}")
    print(f"  Solo catalogo:        {total - with_ficha:,}")
    print(f"  Autores unicos:       {authors:,}")
    print(f"  Palabras totales:     {words:,}")

    print(f"\nPor nivel:")
    for nivel, cnt in niveles:
        print(f"  Nivel {nivel}: {cnt}")

    print(f"\nPor categoria:")
    for cat, cnt in cats:
        print(f"  {cat}: {cnt}")

    print(f"\nTop 10 autores:")
    for author, cnt in top_authors:
        print(f"  {author}: {cnt} libros")

    # Test FTS
    print("\nTest busqueda full-text:")
    conn = get_conn()
    cur = conn.cursor()
    for q in ["nihilismo", "democracia", "atencion", "poder"]:
        cur.execute("""
            SELECT COUNT(*) FROM library
            WHERE fts_vector @@ plainto_tsquery('spanish', %s)
        """, (q,))
        cnt = cur.fetchone()[0]
        print(f"  '{q}': {cnt} resultados")
    cur.close()
    conn.close()
    print("=" * 60)


# =====================================================
# MAIN
# =====================================================

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python migrate_library.py /ruta/vault/Biblioteca [/ruta/biblioteca.db]")
        print("")
        print("  arg1 — carpeta Biblioteca del vault (con Filosofia/, Humanidades/, etc.)")
        print("  arg2 — (opcional) ruta a biblioteca.db para importar catalogo completo")
        print("")
        print("Variable requerida: DATABASE_URL (PostgreSQL de Render)")
        sys.exit(1)

    vault_path = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.isdir(vault_path):
        print(f"ERROR: No encontre la carpeta: {vault_path}")
        sys.exit(1)

    url_preview = DATABASE_URL[:40] + '...' if len(DATABASE_URL) > 40 else DATABASE_URL
    print(f"Vault: {vault_path}")
    print(f"DB:    {url_preview}")
    if db_path:
        print(f"SQLite: {db_path}")
    print("")

    start = time.time()

    # 1. Crear tabla
    setup_table()

    # 2. Escanear fichas del vault
    ficha_books = scan_vault(vault_path)

    # Indice para deduplicar con biblioteca.db
    ficha_titles = {f"{b['title'].lower()}|{b['author'].lower()}" for b in ficha_books}

    # 3. Cargar catalogo completo de biblioteca.db (si se pasa)
    db_books = []
    if db_path:
        db_books = load_from_sqlite(db_path, ficha_titles)

    all_books = ficha_books + db_books
    logger.info(f"Total a insertar: {len(all_books)} ({len(ficha_books)} fichas + {len(db_books)} catalogo)")

    if not all_books:
        print("ERROR: No encontre ningun libro.")
        sys.exit(1)

    # 4. Insertar en PostgreSQL
    inserted, errors = insert_books(all_books)

    elapsed = time.time() - start
    logger.info(f"Tiempo: {elapsed:.1f}s — Insertados: {inserted}, Errores: {errors}")

    # 5. Estadisticas
    print_stats()
