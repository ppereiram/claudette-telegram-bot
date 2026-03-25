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
                return "updated"
            return "skipped"
        else:
            cur.execute(
                """INSERT INTO documents (filepath, title, content, tags, metadata, word_count, file_modified_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (doc["filepath"], doc["title"], doc["content"], doc["tags"],
                 doc["metadata"], doc["word_count"], doc["file_modified_at"])
            )
            return "inserted"

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
# SCHEMAS Y DISPATCHER (para bot.py)
# ──────────────────────────────────────────────

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
    }
]


async def execute_kb_tool(name: str, args: dict) -> str:
    """Dispatcher para los 4 KB tools. Llamar desde execute_tool_async()."""
    if name == "kb_search":
        return kb_search(args.get("query", ""), args.get("limit", 5), args.get("tag_filter"))
    elif name == "kb_list":
        return kb_list(args.get("mode", "recent"), args.get("tag"), args.get("limit", 10))
    elif name == "kb_read":
        return kb_read(args.get("filepath", ""), args.get("max_chars", 3000))
    elif name == "kb_ingest":
        return kb_ingest(args.get("vault_path"), args.get("cleanup", False))
    return f"❌ KB tool desconocido: {name}"
