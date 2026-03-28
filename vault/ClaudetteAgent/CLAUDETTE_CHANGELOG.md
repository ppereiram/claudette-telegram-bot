# CLAUDETTE CHANGELOG
*Historial de decisiones de desarrollo — por qué se hizo cada cambio*

---

## 2026-03-27

### fix: YouTube 8 modos — tokens 4096->16000 + transcript 12k->50k chars
- **Commit:** `041e8af`
- **Problema:** El análisis con 8 modos devolvía "He procesado la solicitud" sin contenido real.
- **Causa:** MAX_TOKENS_NORMAL=4096 es insuficiente para 8 secciones de análisis. El bot agotaba las rondas de herramientas sin completar la respuesta.
- **Fix:** Añadir 'youtube', 'youtu', '8 modos', 'transcripcion video' a doc_keywords para triggear 16k tokens. Subir límite de transcript de 12k a 50k chars en utils_security.py y de 6k a 50k en tools_registry.py.

### fix: La Ecuacion Final — conectar SOLO si Pablo lo pide + mojibake CLAUDETTE_CORE
- **Commit:** `89c21f5`
- **Problema:** La instrucción "Si hay avances en IA → conectar con sus proyectos" hacía que Claudette mencionara La Ecuación Final en cualquier tema de tecnología, sin que Pablo lo pidiera.
- **Fix:** Reescribir la regla en CLAUDETTE_CORE.md: prohibido conectar con libros personales (La Ecuación Final, Entre Dos Mundos) a menos que Pablo lo pida explícitamente o el tema CENTRAL sea la trama del libro.

### fix: X.com URL — si fxtwitter falla, devolver error honesto en vez de analizar página JS
- **Commit:** `3153d1d`
- **Problema:** Cuando fxtwitter API fallaba, el código caía al fetch genérico que devuelve la página de error JS de X.com. Claude analizaba esa página de error como si fuera el contenido del tweet.
- **Fix:** Añadir return explícito tras el bloque de X.com: si fxtwitter falla, devolver mensaje "No pude leer el tweet (X.com bloquea bots)."

### fix: transcript YouTube 6k -> 50k chars
- **Commit:** `ead57b2`
- **Problema:** tools_registry.py:fetch_url() cortaba transcripts a 6000 chars. Claude completaba el resto de memoria, produciendo análisis inexactos ("relleno").
- **Fix:** Subir límite a 50000 chars para que el transcript completo esté disponible.

### feat: sync todos los vaults — solo .md, sin archivos de sistema
- **Commit:** `2f02d4a`
- **Problema:** sync_vault.ps1 subía archivos .py, .env, .json y carpetas .obsidian/.claude que podían contener secrets (API keys). GitHub Push Protection bloqueó un push que incluía ANTHROPIC_API_KEY.
- **Fix:** Cambiar xcopy → robocopy con filtro `*.md /XD .obsidian .trash .claude .git /XF *.py *.db *.env *.html *.txt *.js *.ts *.json`.

### feat: agregar Biblioteca Viva, CEREBRO2, Desarrollador Inmobiliario y Libros al sync
- **Commit:** `9d0f42a`
- **Motivo:** Pablo quiere que Claudette tenga acceso a todos sus proyectos activos en Obsidian para responder preguntas de contexto sin necesidad de pegar contenido manualmente.

### fix: mojibake en main.py, brain.py, tools_registry.py (emojis)
- **Commit:** `868b212`
- **Problema:** Emojis y caracteres especiales aparecían como garabatos (ðŸ§˜â€â™€ï¸) en Telegram. Causado por archivos guardados con encoding incorrecto (UTF-8 bytes leídos como latin-1/cp1252).
- **Fix:** Scripts Python con Unicode escapes (\uXXXX) para reemplazar todas las secuencias corruptas. Dos pasadas: latin-1 primero, cp1252 después (em dashes, emojis, signo ♀).

### fix: garabatos + midas vault path + noticias fallback + Byung-Chul Han
- **Commit:** `b620f27`
- **Problema 1:** morning_prompt en brain.py tenía garabatos (mojibake en el archivo fuente).
- **Problema 2:** midas_monitor.py tenía hardcoded `/opt/render/project/src/vault` que no existía en Render → Midas mostraba $0 en todo.
- **Problema 3:** Cuando todos los RSS fallaban, tools_registry.py devolvía string vacío → Claude inventaba noticias.
- **Problema 4:** Han Byung-Chul aparecía en análisis no relacionados con fatiga digital.
- **Fix:** 135+ reemplazos mojibake en brain.py; función _find_vault_path() con candidatos en orden; mensaje explícito "[NOTICIAS NO DISPONIBLES]"; restricción Han a textos que traten EXPLÍCITAMENTE de fatiga digital.

---

## Historial previo

- `58c8c72` — Menú de comandos Telegram + capacidades completas
- `c3020bd` — Grafo KB + Mental Models + Síntesis semanal + Geolocalización inteligente
- `47e90a2` — Escudo de Veracidad + búsqueda cruzada KB+Biblioteca + /progreso
- `97b9799` — Boletín matutino con noticias enriquecidas
- `63e9ca5` — Reddit, HN real-time + analizador de contenido 8 modos
- `9094250` — Claudette corre main.py en Render + Firecrawl + boletín sin límite chars
- `43a2a65` — Fix morning bulletin trigger en handle_text
- `6ce1073` — Noticias via RSS feeds (IA, geopolítica, mercados, ciencia)
- `98a5527` — Boletín matutino: fecha en español, anti-alucinación noticias

---

*Este archivo se actualiza automáticamente al arrancar Claudette (auto-log de commits → KB).*
*Para añadir contexto adicional: `kb_save_insight` con categoría `claudette_dev`.*
