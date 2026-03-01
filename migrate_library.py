#!/usr/bin/env python3
"""
migrate_library.py — Carga la biblioteca de Obsidian a PostgreSQL de Claudette.

USO:
  python migrate_library.py /ruta/a/tu/vault/Biblioteca

  O con DATABASE_URL explícito:
  DATABASE_URL="postgresql://user:pass@host/db" python migrate_library.py /ruta/vault/Biblioteca

ESTRUCTURA ESPERADA DEL VAULT:
  Biblioteca/
  ├── Filosofía/            ← categoría
  │   ├── Byung-Chul Han/  ← autor
  │   │   ├── 0225 - Infocracia.md  ← libro
  │   │   └── 0226 - La agonia del Eros.md
  │   ├── Carl Gustav Jung/
  │   │   └── ...
  ├── Ciencias-Sociales/
  ├── Esoterismo/
  └── Humanidades/

Cada .md se parsea para extraer tags, contenido, y se indexa en PostgreSQL
con búsqueda full-text en español.
"""

import os
import sys
import re
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("migrate")

# --- PostgreSQL ---
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # Intentar cargar de .env o config
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_URL = os.environ.get('DATABASE_URL')
    except ImportError:
        pass

if not DATABASE_URL:
    print("❌ Necesitás DATABASE_URL como variable de entorno.")
    print("   Ejemplo: DATABASE_URL='postgresql://user:pass@host/db' python migrate_library.py ./Biblioteca")
    sys.exit(1)

import psycopg2


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def setup_table():
    """Crea la tabla library si no existe."""
    conn = get_conn()
    cur = conn.cursor()

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Índice full-text en español
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_library_fts 
        ON library 
        USING GIN (
            to_tsvector('spanish', 
                COALESCE(title, '') || ' ' || 
                COALESCE(author, '') || ' ' || 
                COALESCE(content, '') || ' ' ||
                COALESCE(array_to_string(tags, ' '), '')
            )
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_author ON library (LOWER(author))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_category ON library (LOWER(category))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_library_tags ON library USING GIN (tags)")

    conn.commit()
    cur.close()
    conn.close()
    logger.info("✅ Tabla library creada/verificada con índices FTS")


def parse_tags(val):
    """Parsea tags de Obsidian en varios formatos."""
    if not val:
        return []
    val = val.strip('[]')
    tags = re.split(r'[,\s]+', val)
    return [t.strip().strip('#').strip('"').strip("'").lower()
            for t in tags if t.strip() and len(t.strip()) > 1]


def parse_obsidian_properties(lines):
    """Extrae properties de Obsidian (tags, etc) del inicio del archivo."""
    tags = []
    properties_end = 0

    # YAML frontmatter (--- ... ---)
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                properties_end = i + 1
                # Parsear YAML simple
                for line in lines[1:i]:
                    line = line.strip()
                    if line.lower().startswith('tags'):
                        _, _, val = line.partition(':')
                        tags = parse_tags(val.strip())
                break
        return tags, properties_end

    # Obsidian properties inline (--- con properties)
    # O properties tipo "tags: x, y, z" al inicio
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('tags') and ('::' in stripped or ':' in stripped):
            sep = '::' if '::' in stripped else ':'
            _, _, val = stripped.partition(sep)
            tags = parse_tags(val.strip())
            properties_end = i + 1
        elif stripped == '---' and i > 0:
            properties_end = i + 1
            break
        elif stripped.startswith('#') or (stripped and not any(c in stripped for c in ['::', ':'])):
            # Ya empezó el contenido
            properties_end = i
            break

    return tags, properties_end


def parse_md_file(filepath, filename, category, author):
    """Parsea un archivo .md de Obsidian."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        logger.warning(f"  ⚠️ No pude leer {filepath}: {e}")
        return None

    if not content.strip():
        return None

    lines = content.split('\n')

    # Extraer tags y propiedades
    tags, body_start = parse_obsidian_properties(lines)

    # Contenido limpio (sin propiedades)
    body = '\n'.join(lines[body_start:]).strip()

    # Título: del H1 o del filename
    title = ''
    h1_match = re.search(r'^#\s+(.+)', body, re.MULTILINE)
    if h1_match:
        title = h1_match.group(1).strip()
        # Limpiar markdown del título
        title = re.sub(r'\*+', '', title).strip()
        title = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', title).strip()

    if not title:
        # "0225 - Infocracia.md" → "Infocracia"
        name = filename.replace('.md', '')
        name = re.sub(r'^\d+\s*[-–—]\s*', '', name)
        title = name.strip()

    # Summary: primeras ~500 chars del cuerpo
    clean_body = re.sub(r'^#+\s+.+\n?', '', body, count=1)  # Quitar primer heading
    clean_body = clean_body.strip()
    summary = clean_body[:500] + ('...' if len(clean_body) > 500 else '')

    word_count = len(body.split())

    return {
        'title': title,
        'author': author,
        'category': category,
        'tags': tags,
        'summary': summary,
        'content': body,
        'filename': filename,
        'word_count': word_count
    }


def scan_vault(vault_path):
    """
    Escanea la estructura del vault:
    vault_path/Categoría/Autor/libro.md
    
    También soporta:
    vault_path/Categoría/libro.md (sin subcarpeta de autor)
    """
    books = []

    for category_name in sorted(os.listdir(vault_path)):
        category_path = os.path.join(vault_path, category_name)
        if not os.path.isdir(category_path):
            continue
        if category_name.startswith('.') or category_name.startswith('_'):
            continue

        logger.info(f"📂 Categoría: {category_name}")

        for item in sorted(os.listdir(category_path)):
            item_path = os.path.join(category_path, item)

            if os.path.isdir(item_path):
                # Es una subcarpeta de autor
                author_name = item
                md_count = 0

                for md_file in sorted(os.listdir(item_path)):
                    if not md_file.endswith('.md'):
                        continue
                    md_path = os.path.join(item_path, md_file)
                    book = parse_md_file(md_path, md_file, category_name, author_name)
                    if book:
                        books.append(book)
                        md_count += 1

                if md_count:
                    logger.info(f"  👤 {author_name}: {md_count} libros")

            elif item.endswith('.md'):
                # Archivo .md directo en la categoría (sin autor)
                book = parse_md_file(item_path, item, category_name, '')
                if book:
                    books.append(book)

    return books


def insert_books(books, batch_size=50):
    """Inserta libros en PostgreSQL en batches."""
    conn = get_conn()
    cur = conn.cursor()

    # Limpiar tabla existente (migración completa)
    cur.execute("DELETE FROM library")
    conn.commit()
    logger.info(f"🗑️ Tabla limpiada. Insertando {len(books)} libros...")

    inserted = 0
    errors = 0

    for i in range(0, len(books), batch_size):
        batch = books[i:i + batch_size]
        for book in batch:
            try:
                cur.execute("""
                    INSERT INTO library (title, author, category, tags, summary, content, 
                                         filename, word_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    book['title'],
                    book['author'],
                    book['category'],
                    book['tags'],
                    book['summary'],
                    book['content'],
                    book['filename'],
                    book['word_count']
                ))
                inserted += 1
            except Exception as e:
                logger.warning(f"  ⚠️ Error insertando '{book['title']}': {e}")
                conn.rollback()
                errors += 1

        conn.commit()
        logger.info(f"  ✅ {min(i + batch_size, len(books))}/{len(books)} procesados...")

    cur.close()
    conn.close()

    return inserted, errors


def print_stats():
    """Muestra estadísticas post-migración."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM library")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT author) FROM library WHERE author != ''")
    authors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT category) FROM library WHERE category != ''")
    categories = cur.fetchone()[0]

    cur.execute("SELECT SUM(word_count) FROM library")
    words = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(array_length(tags, 1)) FROM library WHERE tags IS NOT NULL")
    total_tags = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT category, COUNT(*) as cnt 
        FROM library 
        WHERE category != '' 
        GROUP BY category 
        ORDER BY cnt DESC
    """)
    cats = cur.fetchall()

    cur.execute("""
        SELECT author, COUNT(*) as cnt 
        FROM library 
        WHERE author != '' 
        GROUP BY author 
        ORDER BY cnt DESC 
        LIMIT 10
    """)
    top_authors = cur.fetchall()

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print(f"📚 MIGRACIÓN COMPLETA")
    print("=" * 60)
    print(f"  Total libros:      {total:,}")
    print(f"  Autores únicos:    {authors:,}")
    print(f"  Categorías:        {categories}")
    print(f"  Palabras totales:  {words:,}")
    print(f"  Tags totales:      {total_tags:,}")

    print(f"\n📂 Por categoría:")
    for cat, cnt in cats:
        print(f"  {cat}: {cnt}")

    print(f"\n👤 Top 10 autores:")
    for author, cnt in top_authors:
        print(f"  {author}: {cnt} libros")

    # Test de búsqueda
    print("\n🔍 Test de búsqueda full-text:")
    conn = get_conn()
    cur = conn.cursor()

    test_queries = ["nihilismo", "democracia", "atención", "zen"]
    for q in test_queries:
        cur.execute("""
            SELECT COUNT(*) FROM library
            WHERE to_tsvector('spanish', 
                      COALESCE(title, '') || ' ' || 
                      COALESCE(author, '') || ' ' || 
                      COALESCE(content, '') || ' ' ||
                      COALESCE(array_to_string(tags, ' '), '')
                  ) @@ plainto_tsquery('spanish', %s)
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
        print("Uso: python migrate_library.py /ruta/a/vault/Biblioteca")
        print("")
        print("La ruta debe apuntar a la carpeta que contiene las categorías")
        print("(Filosofía, Ciencias-Sociales, Esoterismo, etc.)")
        print("")
        print("Variable requerida: DATABASE_URL (la de tu Render PostgreSQL)")
        sys.exit(1)

    vault_path = sys.argv[1]

    if not os.path.isdir(vault_path):
        print(f"❌ No encontré la carpeta: {vault_path}")
        sys.exit(1)

    print(f"📚 Escaneando vault: {vault_path}")
    print(f"🗄️ Database: {DATABASE_URL[:30]}...")
    print("")

    start = time.time()

    # 1. Crear tabla
    setup_table()

    # 2. Escanear vault
    books = scan_vault(vault_path)
    logger.info(f"📖 Encontrados: {len(books)} libros")

    if not books:
        print("❌ No encontré archivos .md en la estructura esperada.")
        print("   Verificá que la estructura sea: Categoría/Autor/libro.md")
        sys.exit(1)

    # 3. Insertar en PostgreSQL
    inserted, errors = insert_books(books)

    elapsed = time.time() - start
    logger.info(f"⏱️ Tiempo: {elapsed:.1f}s")

    if errors:
        logger.warning(f"⚠️ {errors} errores durante la inserción")

    # 4. Estadísticas
    print_stats()
