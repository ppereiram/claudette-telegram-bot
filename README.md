# claudette-telegram-bot
Bot de Telegram con Claude API para asistencia ejecutiva
# 🧠 CLAUDETTE - Sistema Jarvis de Modelos Mentales

Sistema cognitivo de 216 modelos mentales para análisis profundo y toma de decisiones.

---

## 🎯 ARQUITECTURA DEL SISTEMA

### CAPA 1: ALWAYS-LOADED (Core System)
**Archivo:** `CLAUDETTE_CORE.md` (~12KB)

**Qué contiene:**
- Personalidad y contexto de Pablo
- 40 modelos mentales core
- Protocolo de activación (cuándo usar modelos)
- Reglas de oro y comunicación
- Referencias a documentos especializados

**Cuándo se carga:**
- Siempre activo en el prompt del bot de Telegram
- Base para todas las interacciones

---

### CAPA 2: ON-DEMAND (Deep System)
4 archivos especializados que Claudette lee cuando necesita profundidad:

#### 1️⃣ `MODELS_DEEP.md` (~22KB)
**Los 176 modelos adicionales organizados por dominio:**
- Filosofía Continental (30)
- Trading & Mercados (30)
- Geopolítica (30)
- Arquitectura & Desarrollo (20)
- Biología & Evolución (20)
- Tecnología & AI (20)
- Comunicación (20)
- Meta-Learning (6)

**Cuándo leer:**
- Análisis profundo (Nivel 4-5)
- Necesitas modelos especializados
- Problema requiere 10+ modelos

---

#### 2️⃣ `ANTIPATTERNS.md` (~8KB)
**Cuándo NO usar modelos - Via Negativa:**
- 6 anti-patterns generales
- Errores por modelo específico
- Errores de integración
- Checklist de validación
- Señales de éxito

**Cuándo leer:**
- Sientes que estás forzando un modelo
- Necesitas validar que modelo aplica
- Calibrar uso apropiado

---

#### 3️⃣ `FRAMEWORK.md` (~7KB)
**Metodología paso a paso:**
- Fase 1: Comprensión del problema
- Fase 2: Selección de modelos
- Fase 3: Aplicación sistemática
- Fase 4: Síntesis multinivel
- Fase 5: Comunicación calibrada
- Modos de profundidad (Rápido/Estándar/Profundo)

**Cuándo leer:**
- Primera vez haciendo análisis complejo
- Necesitas estructura paso a paso
- Quieres asegurar rigor metodológico

---

#### 4️⃣ `TEMPLATES.md` (~10KB)
**Plantillas ejecutables para 5 casos:**
1. Decisión Importante (7 modelos)
2. Oportunidad de Negocio (6 modelos)
3. Análisis de Riesgo (6 modelos)
4. Innovación/Creatividad (5 modelos)
5. Dilema Ético (4 modelos)

**Cuándo leer:**
- Tienes problema tipo estándar
- Quieres estructura predefinida
- Necesitas ahorrar tiempo con template

---

## 🚀 CÓMO FUNCIONA

### Flujo Típico:

1. **Usuario hace consulta** → Claudette clasifica nivel (1-5)

2. **Si Nivel 1-3 (Simple):**
   - Usa los 40 modelos CORE
   - Responde directamente sin leer archivos

3. **Si Nivel 4-5 (Complejo):**
   - Lee `MODELS_DEEP.md` para acceso a 216 modelos
   - Lee `FRAMEWORK.md` para metodología rigurosa
   - Aplica modelos en narrativa natural
   - Sintetiza con confianza calibrada

4. **Si necesita validación:**
   - Lee `ANTIPATTERNS.md` para verificar uso apropiado

5. **Si es caso estándar:**
   - Lee `TEMPLATES.md` para usar plantilla predefinida

---

## 📊 VENTAJAS DE ESTA ARQUITECTURA

### Como Jarvis:
✅ **Siempre consciente** - Core cargado permanentemente
✅ **Profundiza cuando necesita** - On-demand loading
✅ **Eficiente en tokens** - No carga todo siempre
✅ **Escalable** - Fácil añadir módulos
✅ **Modular** - Actualizar partes sin tocar todo

### Comparado con "todo en un archivo":
- 🎯 **Menos tokens consumidos** - Solo lee lo necesario
- ⚡ **Más rápido** - No procesa información irrelevante
- 🧩 **Más mantenible** - Editar un archivo no afecta a otros
- 📈 **Más escalable** - Puedes añadir MODELS_CRYPTO.md, etc.

---

## 🛠️ SETUP EN TELEGRAM BOT

### En tu archivo de prompt del bot:

```python
# Cargar CORE (always-loaded)
with open('CLAUDETTE_CORE.md', 'r') as f:
    core_prompt = f.read()

# Indicar ubicación de archivos profundos
deep_files_location = """
Los siguientes archivos están disponibles en /repo/knowledge/:
- MODELS_DEEP.md (216 modelos completos)
- ANTIPATTERNS.md (cuándo NO usar modelos)
- FRAMEWORK.md (metodología paso a paso)
- TEMPLATES.md (plantillas ejecutables)

Úsalos con read_local_file() cuando necesites profundidad.
"""

# Prompt final
system_prompt = core_prompt + "\n\n" + deep_files_location
```

---

## 📝 NIVELES DE PROFUNDIDAD

### Nivel 1: CASUAL (0 modelos)
**Trigger:** "Hola", "¿Cómo estás?"
**Acción:** Respuesta natural sin modelos

### Nivel 2: FACTUAL (1-2 modelos)
**Trigger:** Pregunta factual simple
**Acción:** Respuesta + mención sutil de modelo si enriquece

### Nivel 3: DECISIÓN SIMPLE (3-5 modelos)
**Trigger:** Decisión con contexto claro
**Acción:** Aplicar modelos CORE automáticamente
**Archivos:** Solo CORE (no lee archivos adicionales)

### Nivel 4: ANÁLISIS PROFUNDO (10-15 modelos)
**Trigger:** "Analiza...", "Qué harías...", dilemas complejos
**Acción:** Leer MODELS_DEEP + FRAMEWORK
**Archivos:** `MODELS_DEEP.md`, `FRAMEWORK.md`

### Nivel 5: SÍNTESIS FILOSÓFICA (20+ modelos)
**Trigger:** Preguntas existenciales, geopolítica profunda
**Acción:** Sistema completo + múltiples dominios
**Archivos:** `MODELS_DEEP.md`, `FRAMEWORK.md`, `ANTIPATTERNS.md`

---

## 🎓 EJEMPLOS DE USO

### Ejemplo 1: Decisión Simple (Nivel 3)
```
Usuario: "¿Debería aceptar este trabajo que paga 20% más?"

Claudette (usando solo CORE):
- Costo de Oportunidad
- Segundo Orden
- Reversibilidad
→ Respuesta en 2 minutos
```

### Ejemplo 2: Análisis Profundo (Nivel 4)
```
Usuario: "Analiza si Milei puede cambiar Argentina estructuralmente"

Claudette:
1. Lee MODELS_DEEP.md
2. Lee FRAMEWORK.md
3. Aplica 12 modelos:
   - Geopolítica: Heartland, Incentivos
   - Economía: Destrucción Creativa, Path Dependence
   - Filosofía: Realismo Capitalista
   - etc.
→ Análisis completo en 30 minutos
```

### Ejemplo 3: Template (Nivel 4)
```
Usuario: "Evalúa si debería invertir en este startup"

Claudette:
1. Lee TEMPLATES.md
2. Usa plantilla "Oportunidad de Negocio"
3. Aplica 6 modelos pre-seleccionados
→ Evaluación estructurada en 15 minutos
```

---

## 🔄 ACTUALIZACIÓN Y MANTENIMIENTO

### Para añadir modelos:
1. Editar `MODELS_DEEP.md`
2. Añadir modelo en sección apropiada
3. Subir a GitHub
4. Claudette automáticamente usa nuevo modelo

### Para añadir plantilla:
1. Editar `TEMPLATES.md`
2. Crear nueva plantilla con modelos pre-seleccionados
3. Subir a GitHub

### Para modificar personalidad:
1. Editar `CLAUDETTE_CORE.md`
2. Actualizar sección "Quién Eres" o "Contexto de Pablo"
3. Subir a GitHub

---

## 📚 FILOSOFÍA DEL SISTEMA

### Inspiración:
- **Jarvis** (Iron Man) - Asistente que piensa, no solo ejecuta
- **Via Negativa** (Taleb) - Saber qué NO hacer es tan valioso
- **Latticework of Mental Models** (Munger) - Pensar multi-dimensional
- **Slowness** (Pablo) - Profundidad > velocidad

### Principios:
1. **Pensar CON modelos, no pedir permiso**
2. **Síntesis multinivel > checklist académico**
3. **Honestidad calibrada > confianza ciega**
4. **Narrativa fluida > bullets técnicos**
5. **Acción > análisis parálisis**

---

## 🎯 MÉTRICAS DE ÉXITO

**Claudette está funcionando bien cuando:**

✅ Aplica modelos automáticamente (no pregunta "¿quieres que use X?")
✅ Encuentra contradicciones entre modelos y las resuelve
✅ Calibra confianza apropiadamente (no siempre 100% o 0%)
✅ Insights van más allá de lo obvio
✅ Usuario puede tomar mejor decisión después
✅ Comunicación clara sin jerga innecesaria
✅ Admite "no sé" cuando apropiado

---

## 🚨 TROUBLESHOOTING

### Problema: Claudette usa demasiados modelos
**Solución:** Revisar ANTIPATTERNS.md - probablemente "Análisis Parálisis"

### Problema: Claudette siempre usa los mismos modelos
**Solución:** Revisar ANTIPATTERNS.md - probablemente "Martillo de Maslow"

### Problema: Respuestas muy técnicas/académicas
**Solución:** Revisar sección "Tono y Comunicación" en CORE

### Problema: No lee archivos profundos cuando debería
**Solución:** Verificar que instrucción "Lee X cuando..." esté clara en CORE

---

## 📞 CONTACTO

**Creador:** Pablo Pereira Magnere (Costa Rica) Celular: +(506)8375-5404 email: ppereiram@gmail.com 
**Fecha:** Febrero 2026
**Versión:** 1.0

---

*Este sistema es mi segundo cerebro. Claudette lo usa para pensar profundamente sobre decisiones complejas, combinando rigor analítico con sabiduría filosófica.*

