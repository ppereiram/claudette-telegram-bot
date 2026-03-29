# Claudette — Diario de Versiones

---

## V3.5 — Marco Ético-Analítico *(2026-03-29)*

**Tema:** Del asistente inteligente al asistente con carácter

**Qué se agregó:**
- `prompts/virtudes_fundacionales.md` — Las 18 virtudes de Comte-Sponville (*Pequeño tratado de las grandes virtudes*, 1995) traducidas en comportamientos operacionales concretos para Claudette. Always-loaded en el system prompt.
- Sección XIV en `CLAUDETTE_CORE.md` — Modo Análisis Lógico (Copi): 4 pasos para diseccionar argumentos: stripping emotivo, mapeo de premisas, linter de 8 falacias, evaluación de validez por métodos de Mill.

**Filosofía detrás del upgrade:**
Claudette ya respondía bien. Este upgrade le da *carácter*: la diferencia entre un asistente que obedece reglas morales y uno que actúa desde disposiciones éticas. Comte-Sponville: las virtudes no se aplican, se encarnan.

**Archivos modificados:** `brain.py`, `prompts/CLAUDETTE_CORE.md`, `prompts/virtudes_fundacionales.md` (nuevo)

---

## V3.0 — Sistema Asíncrono + Prompt Caching *(2026-03-27)*

**Tema:** Performance y estabilidad de producción

**Qué se agregó:**
- AsyncAnthropic + `asyncio.to_thread` para llamadas no bloqueantes
- Prompt caching en system prompt (reduce costos ~90% en conversaciones largas)
- Fix crítico: `tool_use` sin `tool_result` corrompía el historial de conversación
- Supadata API como fallback para transcripts de YouTube
- NYSE calendar en Midas Monitor

**Archivos modificados:** `brain.py`, `midas_monitor.py`, `tools_registry.py`

---

## V2.5 — Analizador de Contenido 8 Modos *(2026-03-25)*

**Tema:** Profundidad analítica multidimensional

**Qué se agregó:**
- Tool `analyze_content_deep` con 8 modos simultáneos: modelos mentales, detector de humo, ideas de negocio, estructura narrativa, puntos ciegos, plan de acción, subtexto, conexión filosófica
- Transcripts de YouTube hasta 50k caracteres
- Fix encoding mojibake en emojis

**Archivos modificados:** `tools_registry.py`, `brain.py`, `prompts/CLAUDETTE_CORE.md`

---

## V2.0 — Sistema Modular + Biblioteca Viva *(2026-03-20 aprox.)*

**Tema:** Refactor arquitectural — de monolito a módulos

**Qué se agregó:**
- `main.py` como entry point modular (reemplaza `bot.py` monolítico de 904 líneas)
- Biblioteca de 2491 libros en PostgreSQL con búsqueda semántica
- Knowledge Base persistente (`kb_search`, `kb_ingest`, `kb_save_insight`)
- Firecrawl como fallback para páginas bloqueadas
- Scheduler 6am hora Costa Rica para boletín matutino
- Deploy en Render con auto-deploy desde GitHub

**Archivos modificados:** Refactor completo — `main.py`, `brain.py`, `library.py`, `knowledge_base.py`, `midas_monitor.py`

---

## V1.0 — Claudette Original *(2026-02-xx aprox.)*

**Tema:** Bot funcional básico

**Qué había:**
- `bot.py` monolítico
- Respuestas con Claude API
- Sin memoria persistente
- Sin herramientas externas
- System prompt básico

---

## Roadmap (pendientes)

- [ ] Auto-login Windows + NinjaTrader antes del Camino de Santiago (mayo 2026)
- [ ] Analizador Reddit/HN integrado al boletín
- [ ] Memoria episódica: Claudette recuerda conversaciones por tema, no solo hechos
- [ ] V4.0: Integración con vault Obsidian en tiempo real (no solo sync diaria)
