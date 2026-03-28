---
name: Continuidad de sesión y foco en contexto
description: Al reanudar una sesión interrumpida, retomar el hilo inmediato — no ejecutar tareas pendientes del resumen fuera de contexto
type: feedback
---

Al reanudar una conversación interrumpida, NO priorizar la lista de "pending tasks" del resumen sobre el hilo activo de la conversación.

**Why:** El 27/03/2026, la sesión se interrumpió mientras se discutía Quantum Vol-Delta. Al reanudar, en vez de continuar ese hilo, empecé a hacer fixes de EntryHandling que estaban listados como pendientes pero eran fuera de contexto. Pablo lo detectó y lo corrigió.

**How to apply:** Cuando el usuario dice "continua" o "algo pasó" después de una interrupción, identificar el hilo inmediato de la conversación (el último tema activo) y retomarlo. Las tareas pendientes del resumen se ejecutan solo si son la continuación natural del hilo activo, o si el usuario las pide explícitamente.
