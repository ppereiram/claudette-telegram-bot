"""
Claudette Knowledge Base
========================
4 tools para búsqueda y gestión del vault de Obsidian indexado en PostgreSQL.

Tools:
  - kb_search   → búsqueda full-text con ranking
  - kb_list     → listar por tag, fecha o estadísticas
  - kb_read     → leer documento completo
  - kb_ingest   → re-indexar vault (manual o programático)

Requiere en env vars:
  - DATABASE_URL        (ya existe en Render)
  - OBSIDIAN_VAULT_PATH (agregar en Render)
"""

import os
import re
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import psycopg2
from psycopg2.extras import Json, RealDictCursor

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CONEXIÓN DB
# ──────────────────────────────────────────────

def _get_conn():
    """Conexión a PostgreSQL desde DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL no configurado")
    if "sslmode" not in db_url:
        db_url += "?sslmode=require"
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


# ──────────────────────────────────────────────
# TOOL 1: kb_search
# ──────────────────────────────────────────────

def kb_search(query: str, limit: int = 5, tag_filter: Optional[str] = None) -> str:
    """
    Búsqueda full-text en el vault con ranking por relevancia.
    
    Args:
        query:      Término(s) de búsqueda en español
        limit:      Máximo de resultados (default: 5)
        tag_filter: Filtrar por tag específico (sin #)
    """
    if not query or not query.strip():
        return "❌ Proporciona un término de búsqueda."

    try:
        conn = _get_conn()
        cur = conn.cursor()

        if tag_filter:
            cur.execute(
                """
                SELECT filepath, title,
                       LEFT(content, 400) AS snippet,
                       tags, word_count,
                       ts_rank_cd(content_vector, plainto_tsquery('spanish', %s)) AS rank
                FROM documents
                WHERE is_active = TRUE
                  AND content_vector @@ plainto_tsquery('spanish', %s)
                  AND %s = ANY(tags)
                ORDER BY rank DESC
                LIMIT %s
                """,
                (query, query, tag_filter, limit)
            )
        else:
            cur.execute(
                """
                SELECT filepath, title,
                       LEFT(content, 400) AS snippet,
                       tags, word_count,
                       ts_rank_cd(content_vector, plainto_tsquery('spanish', %s)) AS rank
                FROM documents
                WHERE is_active = TRUE
                  AND content_vector @@ plainto_tsquery('spanish', %s)
                ORDER BY rank DESC
                LIMIT %s
                """,
                (query, query, limit)
            )

        rows = cur.fetchall()
        conn.close()

        if not rows:
            return f"🔍 Sin resultados para: *{query}*"

        out = [f"🔍 *{len(rows)} resultado(s)* para: _{query}_\n"]
        for i, r in enumerate(rows, 1):
            tags_str = " ".join(f"#{t}" for t in (r["tags"] or []))
            snippet = r["snippet"].replace("\n", " ").strip()[:280]
            out.append(
                f"*{i}. {r['title']}*\n"
                f"   📁 `{r['filepath']}`\n"
                f"   🏷️ {tags_str or '(sin tags)'} · {r['word_count']} palabras\n"
                f"   > {snippet}…\n"
            )
        return "\n".join(out)

    except Exception as e:
        logger.error(f"kb_search error: {e}")
        return f"❌ Error en búsqueda: {e}"


# ──────────────────────────────────────────────
# TOOL 2: kb_list
# ──────────────────────────────────────────────

def kb_list(mode: str = "recent", tag: Optional[str] = None, limit: int = 10) -> str:
    """
    Lista documentos del vault.

    Args:
        mode:  "recent"  → más recientes
               "tags"    → todos los tags disponibles
               "stats"   → estadísticas generales
               "bytag"   → docs con un tag específico (requiere tag=)
        tag:   Tag a filtrar cuando mode="bytag"
        limit: Máximo de resultados
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        if mode == "stats":
            cur.execute("""
                SELECT COUNT(*) AS total_docs,
                       COALESCE(SUM(word_count), 0) AS total_words,
                       MAX(updated_at) AS last_updated
                FROM documents WHERE is_active = TRUE
            """)
            row = cur.fetchone()
            cur.execute("""
                SELECT COUNT(DISTINCT tag) AS unique_tags
                FROM documents, UNNEST(tags) AS tag
                WHERE is_active = TRUE
            """)
            tag_row = cur.fetchone()
            conn.close()
            last = row["last_updated"].strftime("%d/%m/%Y %H:%M") if row["last_updated"] else "N/A"
            return (
                f"📊 *Knowledge Base Stats*\n"
                f"   📄 Documentos: {row['total_docs']:,}\n"
                f"   📝 Palabras totales: {int(row['total_words']):,}\n"
                f"   🏷️ Tags únicos: {tag_row['unique_tags'] or 0}\n"
                f"   🕐 Última actualización: {last}"
            )

        elif mode == "tags":
            cur.execute("""
                SELECT tag, COUNT(*) AS count
                FROM documents, UNNEST(tags) AS tag
                WHERE is_active = TRUE
                GROUP BY tag ORDER BY count DESC LIMIT 30
            """)
            rows = cur.fetchall()
            conn.close()
            if not rows:
                return "🏷️ No hay tags indexados aún."
            lines = ["🏷️ *Tags disponibles:*\n"]
            for r in rows:
                lines.append(f"   `#{r['tag']}` ({r['count']})")
            return "\n".join(lines)

        elif mode == "bytag":
            if not tag:
                return "❌ Especifica un tag con el parámetro `tag=`."
            cur.execute(
                """
                SELECT filepath, title, word_count, updated_at
                FROM documents
                WHERE is_active = TRUE AND %s = ANY(tags)
                ORDER BY updated_at DESC LIMIT %s
                """,
                (tag, limit)
            )
            rows = cur.fetchall()
            conn.close()
            if not rows:
                return f"🏷️ No hay documentos con tag `#{tag}`."
            lines = [f"🏷️ *Documentos con #{tag}:*\n"]
            for r in rows:
                date = r["updated_at"].strftime("%d/%m/%Y")
                lines.append(f"   • *{r['title']}* — {r['word_count']} palabras · {date}")
            return "\n".join(lines)

        else:  # recent
            cur.execute(
                """
                SELECT filepath, title, tags, word_count, updated_at
                FROM documents WHERE is_active = TRUE
                ORDER BY updated_at DESC LIMIT %s
                """,
                (limit,)
            )
            rows = cur.fetchall()
            conn.close()
            if not rows:
                return "📚 Knowledge base vacía. Ejecuta kb_ingest para indexar tu vault."
            lines = [f"📚 *Documentos recientes ({len(rows)}):*\n"]
            for r in rows:
                date = r["updated_at"].strftime("%d/%m")
                tags_str = " ".join(f"#{t}" for t in (r["tags"] or [])[:3])
                lines.append(
                    f"   • *{r['title']}* {tags_str}\n"
                    f"     `{r['filepath']}` · {r['word_count']}p · {date}"
                )
            return "\n".join(lines)

    except Exception as e:
        logger.error(f"kb_list error: {e}")
        return f"❌ Error en listado: {e}"


# ──────────────────────────────────────────────
# TOOL 3: kb_read
# ──────────────────────────────────────────────

def kb_read(filepath: str, max_chars: int = 3000) -> str:
    """
    Lee contenido completo de un documento del vault.

    Args:
        filepath:  Ruta relativa del doc (como aparece en kb_search)
        max_chars: Máx caracteres a retornar (default: 3000)
    """
    if not filepath or not filepath.strip():
        return "❌ Proporciona el filepath del documento."

    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT filepath, title, content, tags, word_count, updated_at
            FROM documents
            WHERE is_active = TRUE AND filepath = %s
            """,
            (filepath.strip(),)
        )
        row = cur.fetchone()

        # Fallback: busca por título parcial
        if not row:
            cur.execute(
                """
                SELECT filepath, title, content, tags, word_count, updated_at
                FROM documents
                WHERE is_active = TRUE AND (filepath ILIKE %s OR title ILIKE %s)
                ORDER BY updated_at DESC LIMIT 1
                """,
                (f"%{filepath}%", f"%{filepath}%")
            )
            row = cur.fetchone()

        conn.close()

        if not row:
            return (
                f"❌ Documento no encontrado: `{filepath}`\n"
                f"Usa `kb_search` para encontrar el filepath correcto."
            )

        tags_str = " ".join(f"#{t}" for t in (row["tags"] or []))
        date = row["updated_at"].strftime("%d/%m/%Y")
        content = row["content"]
        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars]

        out = [
            f"📄 *{row['title']}*",
            f"   📁 `{row['filepath']}`",
            f"   🏷️ {tags_str or '(sin tags)'}",
            f"   📝 {row['word_count']} palabras · {date}",
            "─" * 35,
            content,
        ]
        if truncated:
            out.append(f"\n_[Truncado a {max_chars} chars. Total: {row['word_count']} palabras]_")

        return "\n".join(out)

    except Exception as e:
        logger.error(f"kb_read error: {e}")
        return f"❌ Error leyendo documento: {e}"


# ──────────────────────────────────────────────
# INGESTOR (usado por kb_ingest)
# ──────────────────────────────────────────────

class _ObsidianIngestor:
    def __init__(self, vault_path: str):
        self.vault = Path(vault_path)

    def _frontmatter(self, content: str) -> Tuple[Dict, str]:
        fm, body = {}, content
        if content.startswith("---\n"):
            try:
                end = content.find("\n---\n", 4)
                if end != -1:
                    fm = yaml.safe_load(content[4:end]) or {}
                    body = content[end + 5:]
            except yaml.YAMLError:
                pass
        return fm, body

    def _title(self, filepath: str, content: str, fm: Dict) -> str:
        if "title" in fm:
            return str(fm["title"])
        m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return Path(filepath).stem

    def _tags(self, content: str, fm: Dict) -> List[str]:
        tags = set()
        if "tags" in fm:
            t = fm["tags"]
            if isinstance(t, str):
                tags.add(t)
            elif isinstance(t, list):
                tags.update(str(x) for x in t)
        tags.update(re.findall(r"#([a-zA-Z][a-zA-Z0-9/_-]*)", content))
        return list(tags)

    def _links(self, content: str) -> List[str]:
        return re.findall(r"\[\[([^\]]+)\]\]", content)

    def _process(self, filepath: Path) -> Optional[Dict]:
        try:
            content = filepath.read_text(encoding="utf-8")
            rel = str(filepath.relative_to(self.vault))
            fm, body = self._frontmatter(content)
            return {
                "filepath": rel,
                "title": self._title(rel, body, fm),
                "content": body,
                "tags": self._tags(body, fm),
                "metadata": Json({
                    "frontmatter": fm,
                    "internal_links": self._links(body),
                    "file_size": filepath.stat().st_size,
                }),
                "word_count": len(re.findall(r"\w+", body)),
                "file_modified_at": datetime.fromtimestamp(filepath.stat().st_mtime),
            }
        except Exception as e:
            logger.warning(f"Error procesando {filepath}: {e}")
            return None

    def _upsert(self, conn, doc: Dict) -> str:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, file_modified_at FROM documents WHERE filepath = %s",
            (doc["filepath"],)
        )
        existing = cur.fetchone()
        if existing:
            if doc["file_modified_at"] > existing["file_modified_at"]:
                cur.execute(
                    """UPDATE documents SET title=%s, content=%s, tags=%s,
                       metadata=%s, word_count=%s, file_modified_at=%s, updated_at=NOW()
                       WHERE id=%s""",
                    (doc["title"], doc["content"], doc["tags"], doc["metadata"],
                     doc["word_count"], doc["file_modified_at"], existing["id"])
                )
                self._upsert_links(conn, doc)
                return "updated"
            return "skipped"
        else:
            cur.execute(
                """INSERT INTO documents (filepath, title, content, tags, metadata, word_count, file_modified_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (doc["filepath"], doc["title"], doc["content"], doc["tags"],
                 doc["metadata"], doc["word_count"], doc["file_modified_at"])
            )
            self._upsert_links(conn, doc)
            return "inserted"

    def _upsert_links(self, conn, doc: Dict):
        """Actualiza document_links para este documento."""
        try:
            cur = conn.cursor()
            # Extraer wikilinks del contenido original
            links = self._links(doc["content"])
            if not links:
                return
            # Borrar links previos de este source
            cur.execute("DELETE FROM document_links WHERE source_filepath = %s", (doc["filepath"],))
            for target_title in set(links):
                # Intentar resolver el filepath del target
                cur.execute(
                    "SELECT filepath FROM documents WHERE title ILIKE %s AND is_active = TRUE LIMIT 1",
                    (target_title,)
                )
                row = cur.fetchone()
                target_fp = row["filepath"] if row else None
                cur.execute(
                    """INSERT INTO document_links (source_filepath, target_title, target_filepath)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (source_filepath, target_title) DO UPDATE
                       SET target_filepath = EXCLUDED.target_filepath""",
                    (doc["filepath"], target_title, target_fp)
                )
        except Exception as e:
            logger.warning(f"_upsert_links warning: {e}")

    def run(self, cleanup: bool = False) -> Dict:
        if not self.vault.exists():
            raise FileNotFoundError(f"Vault no encontrado: {self.vault}")

        conn = _get_conn()
        conn.autocommit = True

        md_files = [
            f for f in self.vault.rglob("*.md")
            if not any(p.startswith(".") for p in f.parts)
        ]

        counts = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
        for fp in md_files:
            doc = self._process(fp)
            if doc:
                result = self._upsert(conn, doc)
                counts[result] += 1
            else:
                counts["errors"] += 1

        if cleanup:
            cur = conn.cursor()
            cur.execute("SELECT id, filepath FROM documents WHERE is_active = TRUE")
            deactivated = 0
            for row in cur.fetchall():
                if not (self.vault / row["filepath"]).exists():
                    cur.execute("UPDATE documents SET is_active=FALSE WHERE id=%s", (row["id"],))
                    deactivated += 1
            counts["deactivated"] = deactivated

        conn.close()
        return counts


# ──────────────────────────────────────────────
# TOOL 4: kb_ingest
# ──────────────────────────────────────────────

def kb_ingest(vault_path: Optional[str] = None, cleanup: bool = False) -> str:
    """
    Indexa o re-indexa el vault de Obsidian en PostgreSQL.
    Solo procesa archivos nuevos o modificados.

    Args:
        vault_path: Ruta al vault (usa OBSIDIAN_VAULT_PATH si no se especifica)
        cleanup:    Si True, desactiva docs de archivos eliminados
    """
    path = vault_path or os.environ.get("OBSIDIAN_VAULT_PATH")
    if not path:
        return (
            "❌ No se encontró OBSIDIAN_VAULT_PATH.\n"
            "Configúralo en las variables de entorno de Render."
        )

    try:
        ingestor = _ObsidianIngestor(path)
        counts = ingestor.run(cleanup=cleanup)
        lines = [
            f"✅ *Ingestión completada*",
            f"   📥 Insertados: {counts['inserted']}",
            f"   ✏️ Actualizados: {counts['updated']}",
            f"   ⏭️ Sin cambios: {counts['skipped']}",
            f"   ❌ Errores: {counts['errors']}",
        ]
        if cleanup and "deactivated" in counts:
            lines.append(f"   🗑️ Desactivados: {counts['deactivated']}")
        return "\n".join(lines)

    except FileNotFoundError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.error(f"kb_ingest error: {e}")
        return f"❌ Error durante ingestión: {e}"


# ──────────────────────────────────────────────
# SETUP TABLAS EXTRA (D + E)
# ──────────────────────────────────────────────

def setup_kb_extra_tables():
    """Crea tablas document_links y mental_model_usage si no existen."""
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_links (
                id SERIAL PRIMARY KEY,
                source_filepath TEXT NOT NULL,
                target_title TEXT NOT NULL,
                target_filepath TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_filepath, target_title)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_doclinks_source ON document_links (source_filepath)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_doclinks_target ON document_links (target_filepath)")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS mental_model_usage (
                id SERIAL PRIMARY KEY,
                model_name TEXT NOT NULL,
                context TEXT,
                project TEXT DEFAULT 'General',
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_mm_name ON mental_model_usage (LOWER(model_name))")

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Tablas document_links y mental_model_usage verificadas/creadas")
        return True
    except Exception as e:
        logger.error(f"setup_kb_extra_tables error: {e}")
        return False


# ──────────────────────────────────────────────
# TOOL D: kb_graph
# ──────────────────────────────────────────────

def kb_graph(filepath: str) -> str:
    """
    Muestra el grafo de conexiones de un documento del vault.
    Retorna documentos que enlaza (salientes) y documentos que lo enlazan (entrantes).

    Args:
        filepath: Ruta relativa del documento (como aparece en kb_search)
    """
    if not filepath or not filepath.strip():
        return "❌ Proporciona el filepath del documento."

    try:
        conn = _get_conn()
        cur = conn.cursor()

        # Links salientes: este doc enlaza a otros
        cur.execute(
            """
            SELECT dl.target_title, dl.target_filepath, d.title AS resolved_title
            FROM document_links dl
            LEFT JOIN documents d ON d.filepath = dl.target_filepath
            WHERE dl.source_filepath = %s
            ORDER BY dl.target_title
            """,
            (filepath.strip(),)
        )
        outgoing = cur.fetchall()

        # Links entrantes: otros docs enlazan a este
        cur.execute(
            """
            SELECT dl.source_filepath, d.title AS src_title
            FROM document_links dl
            LEFT JOIN documents d ON d.filepath = dl.source_filepath
            WHERE dl.target_filepath = %s
            ORDER BY dl.source_filepath
            """,
            (filepath.strip(),)
        )
        incoming = cur.fetchall()

        conn.close()

        out = [f"🕸️ *Grafo:* `{filepath}`\n"]

        if outgoing:
            out.append(f"*→ Enlaza a ({len(outgoing)}):*")
            for r in outgoing:
                resolved = r["resolved_title"] or r["target_filepath"] or r["target_title"]
                out.append(f"  • [[{r['target_title']}]] → _{resolved}_")
        else:
            out.append("*→ Sin enlaces salientes*")

        if incoming:
            out.append(f"\n*← Referenciado por ({len(incoming)}):*")
            for r in incoming:
                src_title = r["src_title"] or r["source_filepath"]
                out.append(f"  • `{r['source_filepath']}` — _{src_title}_")
        else:
            out.append("\n*← Sin referencias entrantes*")

        return "\n".join(out)

    except Exception as e:
        logger.error(f"kb_graph error: {e}")
        return f"❌ Error en grafo: {e}"


# ──────────────────────────────────────────────
# TOOL E: track_mental_model + mental_models_stats
# ──────────────────────────────────────────────

def track_mental_model(model_name: str, context: str = "", project: str = "General") -> str:
    """
    Registra que se aplicó un modelo mental en la conversación actual.
    Llamar silenciosamente cuando Claudette aplique uno de los 216 modelos mentales.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO mental_model_usage (model_name, context, project) VALUES (%s, %s, %s)",
            (model_name.strip(), (context or "")[:500], project or "General")
        )
        conn.commit()
        conn.close()
        return f"✓ Modelo mental registrado: {model_name}"
    except Exception as e:
        logger.error(f"track_mental_model error: {e}")
        return f"Error registrando: {e}"


def mental_models_stats(top_n: int = 10) -> str:
    """
    Estadísticas de los modelos mentales más usados por Claudette con Pablo.

    Args:
        top_n: Cuántos modelos mostrar (default: 10)
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS total FROM mental_model_usage")
        total = cur.fetchone()["total"]

        cur.execute(
            """
            SELECT model_name, COUNT(*) AS count,
                   MAX(used_at) AS last_used,
                   array_agg(DISTINCT project ORDER BY project) AS projects
            FROM mental_model_usage
            GROUP BY model_name
            ORDER BY count DESC
            LIMIT %s
            """,
            (top_n,)
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return "🧩 Sin modelos mentales registrados aún. Claudette los registrará al aplicarlos."

        out = [f"🧩 *Modelos Mentales más aplicados* (total: {total} usos)\n"]
        for i, r in enumerate(rows, 1):
            last = r["last_used"].strftime("%d/%m/%Y") if r["last_used"] else "N/A"
            projects = ", ".join(r["projects"] or [])
            out.append(
                f"  *{i}. {r['model_name']}* — {r['count']}x\n"
                f"     Último uso: {last} · Proyectos: _{projects}_"
            )

        return "\n".join(out)

    except Exception as e:
        logger.error(f"mental_models_stats error: {e}")
        return f"❌ Error: {e}"


# ──────────────────────────────────────────────
# SCHEMAS Y DISPATCHER (para bot.py)
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
# TOOL 5: kb_save_insight
# ──────────────────────────────────────────────

MEMORY_FILENAME = "CLAUDETTE_MEMORY.md"

CATEGORY_HEADERS = {
    "decision":       "## Decisiones Importantes",
    "proyecto":       "## Estado de Proyectos",
    "estrategia":     "## Estrategias que Funcionaron",
    "preferencia":    "## Preferencias de Respuesta",
    "claudette_dev":  "## Desarrollo de Claudette",
}


def kb_save_insight(category: str, title: str, content: str, project: str = "General") -> str:
    """
    Guarda un insight/decision/aprendizaje en CLAUDETTE_MEMORY.md del vault.
    Se re-indexa inmediatamente en PostgreSQL para disponibilidad futura.
    """
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault_path:
        return "OBSIDIAN_VAULT_PATH no configurado."

    memory_path = Path(vault_path) / MEMORY_FILENAME
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = CATEGORY_HEADERS.get(category, f"## {category.capitalize()}")
    new_entry = (
        f"\n### {title}\n"
        f"- **Fecha:** {now}\n"
        f"- **Proyecto:** {project}\n"
        f"- **Categoria:** {category}\n\n"
        f"{content}\n\n---\n"
    )

    try:
        if memory_path.exists():
            current = memory_path.read_text(encoding="utf-8")
        else:
            current = (
                "# CLAUDETTE MEMORY\n"
                "*Aprendizajes acumulados automaticamente*\n\n---\n\n"
                "## Decisiones Importantes\n\n"
                "## Estado de Proyectos\n\n"
                "## Estrategias que Funcionaron\n\n"
                "## Preferencias de Respuesta\n"
            )

        if header in current:
            insert_pos = current.find(header) + len(header)
            current = current[:insert_pos] + "\n" + new_entry + current[insert_pos:]
        else:
            current += f"\n{header}\n{new_entry}"

        memory_path.write_text(current, encoding="utf-8")

        # Re-indexar en PostgreSQL inmediatamente
        try:
            conn = _get_conn()
            conn.autocommit = True
            ingestor = _ObsidianIngestor(vault_path)
            doc = ingestor._process(memory_path)
            if doc:
                ingestor._upsert(conn, doc)
            conn.close()
        except Exception as db_err:
            logger.warning(f"No se pudo re-indexar: {db_err}")

        return (
            f"Insight guardado\n"
            f"   {category} - {project}\n"
            f"   {title}"
        )

    except Exception as e:
        logger.error(f"kb_save_insight error: {e}")
        return f"Error guardando insight: {e}"


def search_everything(query: str, limit: int = 5) -> str:
    """
    Búsqueda cruzada simultánea en Vault de Obsidian (KB) Y Biblioteca (2000+ libros).
    Más potente que kb_search o search_library por separado.

    Args:
        query: Términos de búsqueda
        limit: Máximo de resultados por fuente (default: 5)
    """
    if not query or not query.strip():
        return "❌ Proporciona un término de búsqueda."

    try:
        conn = _get_conn()
        cur = conn.cursor()

        # Busca en KB (vault Obsidian)
        cur.execute(
            """
            SELECT 'KB' AS source, filepath AS ref, title,
                   LEFT(content, 300) AS snippet, tags, word_count,
                   ts_rank_cd(content_vector, plainto_tsquery('spanish', %s)) AS rank
            FROM documents
            WHERE is_active = TRUE
              AND content_vector @@ plainto_tsquery('spanish', %s)
            ORDER BY rank DESC
            LIMIT %s
            """,
            (query, query, limit)
        )
        kb_rows = cur.fetchall()

        # Busca en biblioteca (libros)
        cur.execute(
            """
            SELECT 'LIBRO' AS source,
                   COALESCE(filename, CAST(id AS TEXT)) AS ref,
                   title,
                   COALESCE(author, '') AS author,
                   LEFT(COALESCE(summary, content, ''), 300) AS snippet,
                   tags, word_count,
                   ts_rank(fts_vector, plainto_tsquery('spanish', %s)) AS rank
            FROM library
            WHERE fts_vector @@ plainto_tsquery('spanish', %s)
            ORDER BY rank DESC
            LIMIT %s
            """,
            (query, query, limit)
        )
        lib_rows = cur.fetchall()
        conn.close()

        if not kb_rows and not lib_rows:
            return f"🔍 Sin resultados para: *{query}*\n_(buscado en Vault y Biblioteca)_"

        out = [f"🔍 *Búsqueda cruzada:* _{query}_\n"]

        if kb_rows:
            out.append(f"📚 *VAULT — {len(kb_rows)} nota(s):*")
            for i, r in enumerate(kb_rows, 1):
                tags_str = " ".join(f"#{t}" for t in (r["tags"] or [])[:3])
                snippet = (r["snippet"] or "").replace("\n", " ").strip()[:220]
                out.append(
                    f"  *{i}. {r['title']}*  {tags_str}\n"
                    f"     📁 `{r['ref']}`\n"
                    f"     > {snippet}…"
                )

        if lib_rows:
            out.append(f"\n📖 *BIBLIOTECA — {len(lib_rows)} libro(s):*")
            for i, r in enumerate(lib_rows, 1):
                author = r.get("author") or ""
                snippet = (r.get("snippet") or "").replace("\n", " ").strip()[:180]
                author_str = f" · _{author}_" if author else ""
                line = f"  *{i}. {r['title']}*{author_str}"
                if snippet:
                    line += f"\n     > {snippet}…"
                out.append(line)

        return "\n".join(out)

    except Exception as e:
        logger.error(f"search_everything error: {e}")
        return f"❌ Error en búsqueda cruzada: {e}"


KB_TOOLS_SCHEMA = [
    {
        "name": "kb_search",
        "description": (
            "Busca en el knowledge base personal de Pablo (vault de Obsidian). "
            "Usar cuando pregunte sobre sus propias notas, reflexiones, ideas, proyectos, "
            "lecturas, el Camino de Santiago, trading, filosofía u otras cosas que podría "
            "haber escrito. SIEMPRE buscar aquí antes de responder sobre temas personales de Pablo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Términos de búsqueda en español"},
                "limit": {"type": "integer", "description": "Máximo de resultados (default: 5)", "default": 5},
                "tag_filter": {"type": "string", "description": "Filtrar por tag (sin #, ej: 'filosofia', 'trading')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "kb_list",
        "description": (
            "Lista documentos del vault por fecha, tag, o muestra estadísticas. "
            "Usar para explorar qué hay en el vault o cuando Pablo pida ver sus notas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["recent", "tags", "stats", "bytag"],
                    "description": "recent=más nuevos | tags=todos los tags | stats=estadísticas | bytag=por tag específico",
                    "default": "recent"
                },
                "tag": {"type": "string", "description": "Tag a filtrar (requerido si mode='bytag')"},
                "limit": {"type": "integer", "description": "Máximo de resultados", "default": 10}
            },
            "required": []
        }
    },
    {
        "name": "kb_read",
        "description": (
            "Lee el contenido completo de un documento del vault. "
            "Usar después de kb_search para leer el documento completo de un resultado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Ruta relativa del doc (como aparece en kb_search)"},
                "max_chars": {"type": "integer", "description": "Máximo de caracteres a retornar (default: 3000)", "default": 3000}
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "kb_ingest",
        "description": (
            "Indexa o re-indexa el vault de Obsidian en la base de datos. "
            "Usar cuando Pablo diga que actualizó sus notas o quiera refrescar el índice. "
            "Solo procesa archivos nuevos o modificados."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vault_path": {"type": "string", "description": "Ruta al vault (opcional)"},
                "cleanup": {"type": "boolean", "description": "Si true, desactiva docs de archivos eliminados", "default": False}
            },
            "required": []
        }
    },
    {
        "name": "search_everything",
        "description": (
            "Búsqueda cruzada simultánea en el Vault de Obsidian (notas personales de Pablo) "
            "Y en la Biblioteca de 2000+ libros. "
            "USAR como primera opción cuando Pablo busque algo que podría estar en sus notas O en algún libro. "
            "Ej: 'qué tengo sobre estoicismo', 'busca todo sobre Midas', 'qué libros y notas tengo de trading'. "
            "Más potente que kb_search o search_library por separado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Términos de búsqueda en español"},
                "limit": {"type": "integer", "description": "Máximo de resultados por fuente (default: 5)", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "kb_graph",
        "description": (
            "Muestra el grafo de conexiones de un documento del vault: a qué otros documentos enlaza "
            "y qué documentos lo enlazan a él (via [[wikilinks]] de Obsidian). "
            "Usar cuando Pablo quiera explorar conexiones entre notas, o diga 'qué notas se relacionan con X'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Ruta relativa del doc (como aparece en kb_search)"}
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "track_mental_model",
        "description": (
            "Registra silenciosamente que se aplicó un modelo mental en la conversación actual. "
            "LLAMAR AUTOMÁTICAMENTE y sin anunciarlo cuando Claudette aplique uno de los 216 modelos mentales "
            "de su sistema (Navaja de Occam, Ley de Goodhart, Segunda Orden, etc.). "
            "Esto construye estadísticas de qué modelos usa Pablo más."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "model_name": {"type": "string", "description": "Nombre exacto del modelo mental aplicado"},
                "context": {"type": "string", "description": "Breve descripción de cómo se aplicó (1 oración)"},
                "project": {"type": "string", "description": "Proyecto o tema: Midas, Arepartir, General, etc.", "default": "General"}
            },
            "required": ["model_name"]
        }
    },
    {
        "name": "mental_models_stats",
        "description": (
            "Muestra estadísticas de los modelos mentales más usados por Claudette con Pablo. "
            "Usar cuando Pablo pida '/progreso', 'qué modelos usamos más', o quiera ver su perfil de pensamiento."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "Cuántos modelos mostrar (default: 10)", "default": 10}
            },
            "required": []
        }
    },
    {
        "name": "kb_save_insight",
        "description": (
            "Guarda un aprendizaje, decisión importante, insight o contexto de proyecto "
            "en la memoria persistente de Claudette (CLAUDETTE_MEMORY.md). "
            "USAR PROACTIVAMENTE cuando detectes en la conversación: "
            "(1) Una decisión importante que Pablo tomó, "
            "(2) Un insight o estrategia que funcionó en esta sesión, "
            "(3) Cambio de estado relevante en un proyecto activo (Midas, Arepartir, etc.), "
            "(4) Una preferencia de respuesta que Pablo expresó. "
            "NO usar para conversación casual o info ya conocida."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["decision", "proyecto", "estrategia", "preferencia"],
                    "description": "decision | proyecto | estrategia | preferencia"
                },
                "title": {
                    "type": "string",
                    "description": "Título corto descriptivo del insight"
                },
                "content": {
                    "type": "string",
                    "description": "Descripción completa con contexto para entenderlo en el futuro"
                },
                "project": {
                    "type": "string",
                    "description": "Proyecto: Midas, Arepartir, Claudette, General, etc.",
                    "default": "General"
                }
            },
            "required": ["category", "title", "content"]
        }
    }
]


async def execute_kb_tool(name: str, args: dict) -> str:
    """Dispatcher para los KB tools. Llamar desde execute_tool_async()."""
    if name == "search_everything":
        return search_everything(args.get("query", ""), args.get("limit", 5))
    elif name == "kb_search":
        return kb_search(args.get("query", ""), args.get("limit", 5), args.get("tag_filter"))
    elif name == "kb_list":
        return kb_list(args.get("mode", "recent"), args.get("tag"), args.get("limit", 10))
    elif name == "kb_read":
        return kb_read(args.get("filepath", ""), args.get("max_chars", 3000))
    elif name == "kb_ingest":
        return kb_ingest(args.get("vault_path"), args.get("cleanup", False))
    elif name == "kb_graph":
        return kb_graph(args.get("filepath", ""))
    elif name == "track_mental_model":
        return track_mental_model(args.get("model_name", ""), args.get("context", ""), args.get("project", "General"))
    elif name == "mental_models_stats":
        return mental_models_stats(args.get("top_n", 10))
    elif name == "kb_save_insight":
        return kb_save_insight(
            args.get("category", "decision"),
            args.get("title", "Sin título"),
            args.get("content", ""),
            args.get("project", "General")
        )
    return f"❌ KB tool desconocido: {name}"
