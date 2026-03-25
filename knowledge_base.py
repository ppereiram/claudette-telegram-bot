"""
Claudette Knowledge Base
========================
4 tools para bÃºsqueda y gestiÃ³n del vault de Obsidian indexado en PostgreSQL.

Tools:
  - kb_search   â†’ bÃºsqueda full-text con ranking
  - kb_list     â†’ listar por tag, fecha o estadÃ­sticas
  - kb_read     â†’ leer documento completo
  - kb_ingest   â†’ re-indexar vault (manual o programÃ¡tico)

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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONEXIÃ“N DB
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_conn():
    """ConexiÃ³n a PostgreSQL desde DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL no configurado")
    if "sslmode" not in db_url:
        db_url += "?sslmode=require"
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TOOL 1: kb_search
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def kb_search(query: str, limit: int = 5, tag_filter: Optional[str] = None) -> str:
    """
    BÃºsqueda full-text en el vault con ranking por relevancia.
    
    Args:
        query:      TÃ©rmino(s) de bÃºsqueda en espaÃ±ol
        limit:      MÃ¡ximo de resultados (default: 5)
        tag_filter: Filtrar por tag especÃ­fico (sin #)
    """
    if not query or not query.strip():
        return "âŒ Proporciona un tÃ©rmino de bÃºsqueda."

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
            return f"ðŸ” Sin resultados para: *{query}*"

        out = [f"ðŸ” *{len(rows)} resultado(s)* para: _{query}_\n"]
        for i, r in enumerate(rows, 1):
            tags_str = " ".join(f"#{t}" for t in (r["tags"] or []))
            snippet = r["snippet"].replace("\n", " ").strip()[:280]
            out.append(
                f"*{i}. {r['title']}*\n"
                f"   ðŸ“ `{r['filepath']}`\n"
                f"   ðŸ·ï¸ {tags_str or '(sin tags)'} Â· {r['word_count']} palabras\n"
                f"   > {snippet}â€¦\n"
            )
        return "\n".join(out)

    except Exception as e:
        logger.error(f"kb_search error: {e}")
        return f"âŒ Error en bÃºsqueda: {e}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TOOL 2: kb_list
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def kb_list(mode: str = "recent", tag: Optional[str] = None, limit: int = 10) -> str:
    """
    Lista documentos del vault.

    Args:
        mode:  "recent"  â†’ mÃ¡s recientes
               "tags"    â†’ todos los tags disponibles
               "stats"   â†’ estadÃ­sticas generales
               "bytag"   â†’ docs con un tag especÃ­fico (requiere tag=)
        tag:   Tag a filtrar cuando mode="bytag"
        limit: MÃ¡ximo de resultados
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
                f"ðŸ“Š *Knowledge Base Stats*\n"
                f"   ðŸ“„ Documentos: {row['total_docs']:,}\n"
                f"   ðŸ“ Palabras totales: {int(row['total_words']):,}\n"
                f"   ðŸ·ï¸ Tags Ãºnicos: {tag_row['unique_tags'] or 0}\n"
                f"   ðŸ• Ãšltima actualizaciÃ³n: {last}"
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
                return "ðŸ·ï¸ No hay tags indexados aÃºn."
            lines = ["ðŸ·ï¸ *Tags disponibles:*\n"]
            for r in rows:
                lines.append(f"   `#{r['tag']}` ({r['count']})")
            return "\n".join(lines)

        elif mode == "bytag":
            if not tag:
                return "âŒ Especifica un tag con el parÃ¡metro `tag=`."
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
                return f"ðŸ·ï¸ No hay documentos con tag `#{tag}`."
            lines = [f"ðŸ·ï¸ *Documentos con #{tag}:*\n"]
            for r in rows:
                date = r["updated_at"].strftime("%d/%m/%Y")
                lines.append(f"   â€¢ *{r['title']}* â€” {r['word_count']} palabras Â· {date}")
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
                return "ðŸ“š Knowledge base vacÃ­a. Ejecuta kb_ingest para indexar tu vault."
            lines = [f"ðŸ“š *Documentos recientes ({len(rows)}):*\n"]
            for r in rows:
                date = r["updated_at"].strftime("%d/%m")
                tags_str = " ".join(f"#{t}" for t in (r["tags"] or [])[:3])
                lines.append(
                    f"   â€¢ *{r['title']}* {tags_str}\n"
                    f"     `{r['filepath']}` Â· {r['word_count']}p Â· {date}"
                )
            return "\n".join(lines)

    except Exception as e:
        logger.error(f"kb_list error: {e}")
        return f"âŒ Error en listado: {e}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TOOL 3: kb_read
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def kb_read(filepath: str, max_chars: int = 3000) -> str:
    """
    Lee contenido completo de un documento del vault.

    Args:
        filepath:  Ruta relativa del doc (como aparece en kb_search)
        max_chars: MÃ¡x caracteres a retornar (default: 3000)
    """
    if not filepath or not filepath.strip():
        return "âŒ Proporciona el filepath del documento."

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

        # Fallback: busca por tÃ­tulo parcial
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
                f"âŒ Documento no encontrado: `{filepath}`\n"
                f"Usa `kb_search` para encontrar el filepath correcto."
            )

        tags_str = " ".join(f"#{t}" for t in (row["tags"] or []))
        date = row["updated_at"].strftime("%d/%m/%Y")
        content = row["content"]
        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars]

        out = [
            f"ðŸ“„ *{row['title']}*",
            f"   ðŸ“ `{row['filepath']}`",
            f"   ðŸ·ï¸ {tags_str or '(sin tags)'}",
            f"   ðŸ“ {row['word_count']} palabras Â· {date}",
            "â”€" * 35,
            content,
        ]
        if truncated:
            out.append(f"\n_[Truncado a {max_chars} chars. Total: {row['word_count']} palabras]_")

        return "\n".join(out)

    except Exception as e:
        logger.error(f"kb_read error: {e}")
        return f"âŒ Error leyendo documento: {e}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# INGESTOR (usado por kb_ingest)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TOOL 4: kb_ingest
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
            "âŒ No se encontrÃ³ OBSIDIAN_VAULT_PATH.\n"
            "ConfigÃºralo en las variables de entorno de Render."
        )

    try:
        ingestor = _ObsidianIngestor(path)
        counts = ingestor.run(cleanup=cleanup)
        lines = [
            f"âœ… *IngestiÃ³n completada*",
            f"   ðŸ“¥ Insertados: {counts['inserted']}",
            f"   âœï¸ Actualizados: {counts['updated']}",
            f"   â­ï¸ Sin cambios: {counts['skipped']}",
            f"   âŒ Errores: {counts['errors']}",
        ]
        if cleanup and "deactivated" in counts:
            lines.append(f"   ðŸ—‘ï¸ Desactivados: {counts['deactivated']}")
        return "\n".join(lines)

    except FileNotFoundError as e:
        return f"âŒ {e}"
    except Exception as e:
        logger.error(f"kb_ingest error: {e}")
        return f"âŒ Error durante ingestiÃ³n: {e}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SCHEMAS Y DISPATCHER (para bot.py)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

KB_TOOLS_SCHEMA = [
    {
        "name": "kb_search",
        "description": (
            "Busca en el knowledge base personal de Pablo (vault de Obsidian). "
            "Usar cuando pregunte sobre sus propias notas, reflexiones, ideas, proyectos, "
            "lecturas, el Camino de Santiago, trading, filosofÃ­a u otras cosas que podrÃ­a "
            "haber escrito. SIEMPRE buscar aquÃ­ antes de responder sobre temas personales de Pablo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "TÃ©rminos de bÃºsqueda en espaÃ±ol"},
                "limit": {"type": "integer", "description": "MÃ¡ximo de resultados (default: 5)", "default": 5},
                "tag_filter": {"type": "string", "description": "Filtrar por tag (sin #, ej: 'filosofia', 'trading')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "kb_list",
        "description": (
            "Lista documentos del vault por fecha, tag, o muestra estadÃ­sticas. "
            "Usar para explorar quÃ© hay en el vault o cuando Pablo pida ver sus notas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["recent", "tags", "stats", "bytag"],
                    "description": "recent=mÃ¡s nuevos | tags=todos los tags | stats=estadÃ­sticas | bytag=por tag especÃ­fico",
                    "default": "recent"
                },
                "tag": {"type": "string", "description": "Tag a filtrar (requerido si mode='bytag')"},
                "limit": {"type": "integer", "description": "MÃ¡ximo de resultados", "default": 10}
            },
            "required": []
        }
    },
    {
        "name": "kb_read",
        "description": (
            "Lee el contenido completo de un documento del vault. "
            "Usar despuÃ©s de kb_search para leer el documento completo de un resultado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Ruta relativa del doc (como aparece en kb_search)"},
                "max_chars": {"type": "integer", "description": "MÃ¡ximo de caracteres a retornar (default: 3000)", "default": 3000}
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "kb_ingest",
        "description": (
            "Indexa o re-indexa el vault de Obsidian en la base de datos. "
            "Usar cuando Pablo diga que actualizÃ³ sus notas o quiera refrescar el Ã­ndice. "
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
    return f"âŒ KB tool desconocido: {name}"

