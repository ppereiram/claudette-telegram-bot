# FRAMEWORK DE ANÁLISIS CON MODELOS MENTALES
## Metodología Paso-a-Paso para IA

---

## PROPÓSITO DE ESTE DOCUMENTO

Este framework define **exactamente cómo debe pensar un agente IA** al usar el sistema de modelos mentales para producir análisis de máxima calidad.

No es teoría - es **protocolo ejecutable**.

---

# PARTE I: PROCESO CENTRAL DE ANÁLISIS

## FASE 1: INTAKE Y COMPRENSIÓN

### PASO 1.1: RECEPCIÓN DE CONSULTA

**Acción:** Recibir input del usuario

**Checklist inicial:**
- [ ] ¿Es una pregunta, problema o decisión?
- [ ] ¿Qué nivel de profundidad requiere?
- [ ] ¿Hay restricciones de tiempo/recursos?
- [ ] ¿Contexto suficiente o necesito más información?

**Output:** Clasificación preliminar del tipo de consulta

---

### PASO 1.2: DESCOMPOSICIÓN DEL PROBLEMA

**Acción:** Romper el problema en componentes fundamentales

**Preguntas estructurantes:**
1. **¿Cuál es el problema REAL vs. el problema declarado?**
   - A menudo el usuario presenta síntoma, no causa raíz
   - Usar "5 Whys" para llegar al núcleo

2. **¿Qué tipo(s) de problema es?**
   - [ ] Epistemológico (¿cómo saber si es verdad?)
   - [ ] Sistémico (interacciones complejas)
   - [ ] Económico (asignación de recursos)
   - [ ] Psicológico (comportamiento, sesgos)
   - [ ] Estratégico (competencia, posicionamiento)
   - [ ] Científico (hipótesis, evidencia)
   - [ ] Ético/Filosófico (valores, significado)

3. **¿Qué dominios están involucrados?**
   - Listar todas las disciplinas relevantes
   - No asumir problema uni-dimensional

4. **¿Cuáles son los stakeholders?**
   - ¿Quién está involucrado?
   - ¿Qué incentivos tienen?
   - ¿Qué información poseen?

5. **¿Cuál es el horizonte temporal?**
   - Corto plazo vs. largo plazo
   - ¿Decisión urgente o planificación?

**Output:** 
```
PROBLEMA DESCOMPUESTO:
- Problema raíz: [X]
- Tipo(s): [Y]
- Dominios: [A, B, C]
- Stakeholders: [P1, P2, P3]
- Horizonte: [corto/medio/largo]
```

---

### PASO 1.3: IDENTIFICACIÓN DE CONOCIDO VS. DESCONOCIDO

**Acción:** Mapear qué sabemos y qué no sabemos

**Framework de Rumsfeld:**
- **Known knowns:** ¿Qué sabemos que sabemos?
- **Known unknowns:** ¿Qué sabemos que NO sabemos?
- **Unknown unknowns:** ¿Qué ni siquiera sabemos que no sabemos?

**Preguntas críticas:**
1. ¿Tengo información suficiente?
2. ¿Qué supuestos estoy haciendo?
3. ¿Qué datos críticos faltan?
4. ¿Dónde podría estar cometiendo errores?

**Output:** 
```
MAPA DE CONOCIMIENTO:
- Known knowns: [lista]
- Known unknowns: [lista]
- Supuestos críticos: [lista]
- Unknown unknowns potenciales: [hipótesis]
```

---

## FASE 2: SELECCIÓN DE MODELOS

### PASO 2.1: ACTIVACIÓN DE METAMODELO(S)

**Acción:** Seleccionar sistema(s) completo(s) de pensamiento apropiado(s)

**Criterios de selección:**

**SI el problema es:**
- Requiere rigor científico → **Método Científico, Popper, Feynman**
- Toma de decisión bajo incertidumbre → **Taleb, Kahneman, Pensamiento Probabilístico**
- Estrategia competitiva → **Munger, Sun Tzu, Game Theory**
- Análisis sistémico complejo → **Pensamiento Sistémico, Complejidad**
- Dilema ético → **Kant, Rawls, Utilitarismo**
- Búsqueda de significado → **Existencialismo, Fenomenología**
- Innovación/creatividad → **Primeros Principios (Musk), Kauffman**
- Análisis económico → **Smith, Hayek, Keynes** (según contexto)

**Proceso de selección:**
1. Revisar naturaleza del problema (Fase 1)
2. Identificar 1-3 metamodelos más apropiados
3. Justificar selección explícitamente

**Output:**
```
METAMODELO(S) SELECCIONADO(S):
1. [Metamodelo]: [Razón por qué es apropiado]
2. [Metamodelo]: [Razón]
```

---

### PASO 2.2: ESCANEO DE MODELOS INDIVIDUALES

**Acción:** Activar modelos específicos mediante preguntas gatillo

**Metodología:**

1. **Escaneo primario - Preguntas de activación:**
   - Leer rápidamente las "preguntas de activación" de cada modelo
   - Identificar cuáles resuenan con el problema
   - Marcar como candidatos

2. **Escaneo secundario - Dominios:**
   - Revisar modelos de cada dominio relevante identificado en Paso 1.2
   - Asegurar cobertura multidisciplinaria (Latticework de Munger)

3. **Escaneo terciario - Modelos complementarios:**
   - Para cada modelo seleccionado, revisar "Relación con otros modelos"
   - Añadir modelos complementarios que enriquezcan análisis

**Reglas cuantitativas:**
- **Mínimo:** 3 modelos (para evitar pensamiento unidimensional)
- **Óptimo:** 5-7 modelos (balance profundidad-manejabilidad)
- **Máximo:** 12 modelos (más allá dificulta síntesis)

**Diversidad obligatoria:**
- Al menos 2 dominios diferentes
- Al menos 1 modelo de epistemología/ciencia (para rigurosidad)
- Al menos 1 modelo de psicología (para considerar sesgos humanos)

**Output:**
```
MODELOS SELECCIONADOS:
1. [Modelo] - Dominio: [X] - Por qué: [Razón]
2. [Modelo] - Dominio: [Y] - Por qué: [Razón]
...
[Total: N modelos de M dominios]
```

---

### PASO 2.3: VALIDACIÓN DE SELECCIÓN

**Acción:** Verificar que selección es apropiada antes de proceder

**Checklist de validación:**

- [ ] ¿He considerado múltiples dominios? (no solo mi dominio "cómodo")
- [ ] ¿He incluido modelos que podrían CONTRADECIR mi intuición inicial?
- [ ] ¿Algún modelo obvio está faltando?
- [ ] ¿Estoy sobre-complicando con demasiados modelos?
- [ ] ¿He consultado sección "Anti-patterns" para verificar que es apropiado usar estos modelos aquí?

**Decisión:** PROCEDER o REVISAR selección

**Output:** Confirmación de modelos a usar

---

## FASE 3: APLICACIÓN DE MODELOS

### PASO 3.1: ANÁLISIS POR MODELO INDIVIDUAL

**Acción:** Aplicar cada modelo sistemáticamente

**Para CADA modelo seleccionado, ejecutar:**

#### A. ACTIVACIÓN
- Leer definición completa del modelo
- Revisar "aplicaciones" y "pregunta de activación"
- Mentalizar el modelo (adoptar su "lente")

#### B. INTERROGACIÓN DIRIGIDA
Responder estas preguntas desde el modelo:

1. **¿Qué revela este modelo sobre el problema?**
   - Insight único que solo este modelo proporciona

2. **¿Qué pregunta hace este modelo que no había considerado?**
   - Nuevo ángulo de análisis

3. **¿Qué predice este modelo que ocurrirá?**
   - Consecuencias, patrones, dinámicas

4. **¿Qué recomienda este modelo hacer?**
   - Acción concreta basada en el modelo

5. **¿Qué advierte este modelo evitar?**
   - Riesgos, errores, trampas

#### C. DOCUMENTACIÓN
Registrar output estructurado:

```
MODELO: [Nombre]
------------------------
INSIGHT: [Qué revela]
PREGUNTA NUEVA: [Qué no había considerado]
PREDICCIÓN: [Qué ocurrirá según modelo]
RECOMENDACIÓN: [Qué hacer]
ADVERTENCIA: [Qué evitar]
CONFIANZA: [Alta/Media/Baja] - [Por qué]
```

#### D. VERIFICACIÓN DE APLICABILIDAD
- ¿Estoy forzando este modelo donde no aplica?
- ¿Es esta la interpretación correcta del modelo?
- ¿Qué supuestos del modelo se cumplen/no cumplen aquí?

**Output:** Análisis completo por cada modelo (N documentos)

---

### PASO 3.2: ANÁLISIS DESDE METAMODELO

**Acción:** Aplicar sistema completo de pensamiento seleccionado

**Preguntas guía según metamodelo:**

**Si uso Método Científico/Popper:**
- ¿Qué hipótesis puedo formular?
- ¿Cómo falsarlas?
- ¿Qué experimento/evidencia necesito?
- ¿Qué predicciones hace la hipótesis?

**Si uso Taleb:**
- ¿Dónde está la fragilidad/antifragilidad?
- ¿Tengo skin in the game?
- ¿Estoy expuesto a Cisnes Negros?
- ¿Uso barbell strategy?
- ¿Qué puedo remover (via negativa)?

**Si uso Munger:**
- ¿Estoy en mi círculo de competencia?
- ¿He usado inversión (¿cómo garantizar fracaso)?
- ¿Qué dice el checklist?
- ¿He considerado incentivos de todos?
- ¿Uso latticework de modelos múltiples?

**Si uso Kant:**
- ¿Puedo universalizar la máxima?
- ¿Trato personas como fines o medios?
- ¿Qué dice el imperativo categórico?
- ¿Es la intención correcta?

**Si uso Sistemas:**
- ¿Qué feedbacks operan?
- ¿Dónde están puntos de apalancamiento?
- ¿Qué emerge?
- ¿Cómo se conecta con sistema mayor?

**Output:**
```
METAMODELO: [Nombre]
------------------------
ANÁLISIS DESDE ESTE SISTEMA COMPLETO DE PENSAMIENTO:
[Aplicar preguntas específicas del metamodelo]

CONCLUSIÓN DESDE METAMODELO:
[Qué dice este sistema de pensamiento]
```

---

### PASO 3.3: IDENTIFICACIÓN DE CONCORDANCIAS Y CONTRADICCIONES

**Acción:** Comparar outputs de todos los modelos/metamodelos

**Matriz de análisis:**

| Modelo | Insight Principal | Recomendación | Concordancia con otros |
|--------|-------------------|---------------|------------------------|
| Modelo A | [X] | [Hacer Y] | ✓ B, C, D / ✗ E |
| Modelo B | [Z] | [Hacer W] | ✓ A, C / ✗ E, F |
| ... | ... | ... | ... |

**Clasificación:**

1. **CONCORDANCIAS (Consenso entre modelos):**
   - Listar insights/recomendaciones donde múltiples modelos convergen
   - Estos tienen alta confianza - múltiples lentes ven lo mismo

2. **CONTRADICCIONES (Conflictos entre modelos):**
   - Listar donde modelos sugieren cosas opuestas
   - Ejemplo: Un modelo dice "actuar rápido", otro dice "ir lento"
   - NO ignorar - estas son oportunidades de insight profundo

3. **INSIGHTS ÚNICOS (Solo un modelo lo ve):**
   - Listar lo que solo un modelo revela
   - Pueden ser extremadamente valiosos (visión que otros no tienen)

**Output:**
```
CONCORDANCIAS:
- [X modelos coinciden en: ...]
- [Y modelos coinciden en: ...]

CONTRADICCIONES:
- [Modelo A] vs. [Modelo B]: [En qué contradicen]
- [Modelo C] vs. [Modelo D]: [En qué contradicen]

INSIGHTS ÚNICOS:
- [Solo Modelo X ve: ...]
- [Solo Modelo Y ve: ...]
```

---

## FASE 4: SÍNTESIS E INTEGRACIÓN

### PASO 4.1: RESOLUCIÓN DE CONTRADICCIONES

**Acción:** Para cada contradicción identificada, determinar resolución

**Metodología de resolución:**

**Opción 1: AMBOS son verdad en contextos diferentes**
- Identificar en qué contexto aplica cada uno
- Ejemplo: "Ir rápido" para decisiones reversibles; "Ir lento" para irreversibles

**Opción 2: Síntesis dialéctica (Hegeliana)**
- Tesis: Modelo A dice X
- Antítesis: Modelo B dice no-X
- Síntesis: Integración superior que preserva verdad de ambos
- Ejemplo: Kant (universalismo) + Comunitarismo (contexto) = Ética situada con principios universales

**Opción 3: Jerarquía (uno subordinado a otro)**
- Determinar cuál modelo es más fundamental para este contexto
- Ejemplo: Ética > Eficiencia (normalmente)

**Opción 4: Ambos falsos (nueva perspectiva)**
- A veces contradicción revela que ambos modelos son inadecuados
- Necesitas diferente modelo no considerado

**Proceso:**
1. Para cada contradicción, probar resolver con Opciones 1-4
2. Documentar resolución explícitamente
3. Si no resuelve, MANTENER contradicción y explicar ambigüedad

**Output:**
```
CONTRADICCIÓN: [Modelo A vs. Modelo B]
RESOLUCIÓN: [Opción X]
EXPLICACIÓN: [Cómo se resuelve]
ACCIÓN: [Qué implica para decisión]
```

---

### PASO 4.2: CONSTRUCCIÓN DE SÍNTESIS MULTINIVEL

**Acción:** Integrar todos los insights en análisis coherente

**Estructura de síntesis:**

#### NIVEL 1: COMPRENSIÓN DEL PROBLEMA
Integrar todos los insights sobre QUÉ ES realmente el problema
- "Después de analizar desde [N] modelos en [M] dominios, el problema es..."
- Incluir complejidades/matices revelados por modelos

#### NIVEL 2: DINÁMICA Y MECANISMOS
Integrar insights sobre CÓMO FUNCIONA el sistema/situación
- Feedbacks identificados
- Causas raíz vs. síntomas
- Interacciones entre elementos

#### NIVEL 3: PREDICCIONES
Integrar predicciones de todos los modelos
- ¿Qué ocurrirá si X?
- ¿Qué ocurrirá si Y?
- Grado de confianza en cada predicción

#### NIVEL 4: RECOMENDACIONES
Integrar todas las recomendaciones
- Acciones prioritarias (alta concordancia entre modelos)
- Acciones contextuales (dependen de factores)
- Acciones a evitar (advertencias)

#### NIVEL 5: INCERTIDUMBRES Y LIMITACIONES
Honestidad sobre qué NO sabemos
- Known unknowns persistentes
- Limitaciones de modelos usados
- Qué evidencia cambiaría conclusiones

**Output:**
```
SÍNTESIS MULTINIVEL:
==================

1. COMPRENSIÓN DEL PROBLEMA:
[Integración de insights sobre naturaleza del problema]

2. DINÁMICA Y MECANISMOS:
[Cómo funciona el sistema]

3. PREDICCIONES:
[Qué ocurrirá - con grados de confianza]

4. RECOMENDACIONES:
   A. ACCIONES PRIORITARIAS (alta confianza):
      - [Acción 1]: [Razón basada en modelos X, Y, Z]
      - [Acción 2]: [Razón]
   
   B. ACCIONES CONTEXTUALES (depende de):
      - [Si contexto A]: [Acción]
      - [Si contexto B]: [Acción]
   
   C. EVITAR:
      - [No hacer X]: [Advertencia de modelos A, B]

5. INCERTIDUMBRES:
[Qué no sabemos; qué evidencia necesitamos]
```

---

### PASO 4.3: ASIGNACIÓN DE CONFIANZA

**Acción:** Evaluar nivel de confianza en cada conclusión

**Escala de confianza:**
- **MUY ALTA (90%+):** Concordancia de múltiples modelos + evidencia sólida + baja incertidumbre
- **ALTA (70-90%):** Mayoría de modelos concuerdan + evidencia razonable
- **MEDIA (40-70%):** Modelos mixtos + evidencia parcial + incertidumbres significativas
- **BAJA (10-40%):** Alta contradicción entre modelos + evidencia débil + alta incertidumbre
- **MUY BAJA (<10%):** Especulación + modelos inadecuados + incertidumbre crítica

**Factores que AUMENTAN confianza:**
- Concordancia entre modelos de dominios diferentes
- Evidencia empírica sólida
- Consistencia con metamodelo fundamental
- Baja sensibilidad a supuestos

**Factores que REDUCEN confianza:**
- Contradicciones no resueltas
- Evidencia escasa o contradictoria
- Alta sensibilidad a supuestos no verificados
- Aplicación forzada de modelos

**Output:**
```
NIVEL DE CONFIANZA EN CONCLUSIONES:
- [Conclusión A]: [X%] - [Razón]
- [Conclusión B]: [Y%] - [Razón]
- [Conclusión C]: [Z%] - [Razón]
```

---

## FASE 5: COMUNICACIÓN

### PASO 5.1: ESTRUCTURA DE OUTPUT AL USUARIO

**Acción:** Presentar análisis de forma clara y útil

**Formato estándar:**

```markdown
# ANÁLISIS: [Título del problema]

## RESUMEN EJECUTIVO (para usuarios con prisa)
[2-3 oraciones: problema, hallazgo principal, recomendación clave]

## COMPRENSIÓN DEL PROBLEMA
[Qué es realmente el problema - síntesis Nivel 1]

## ANÁLISIS MULTINIVEL
### Perspectiva desde [Dominio 1]
[Insights de modelos de este dominio]

### Perspectiva desde [Dominio 2]
[Insights de modelos de este dominio]

### Perspectiva desde [Dominio 3]
...

## HALLAZGOS CLAVE
1. [Hallazgo 1] - Confianza: [X%]
2. [Hallazgo 2] - Confianza: [Y%]
...

## RECOMENDACIONES
### Acciones Inmediatas
- [ ] [Acción 1]: [Por qué]
- [ ] [Acción 2]: [Por qué]

### Consideraciones Contextuales
[Si X, entonces Y; si A, entonces B]

### Evitar
- ✗ [No hacer esto]: [Por qué]

## INCERTIDUMBRES Y PRÓXIMOS PASOS
[Qué no sabemos; qué información adicional ayudaría]

---
## TRANSPARENCIA DE MÉTODO
**Modelos usados:** [Lista]
**Metamodelo(s):** [Lista]
**Nivel de profundidad:** [Rápido/Estándar/Profundo]
```

---

### PASO 5.2: CALIBRACIÓN DE LENGUAJE

**Acción:** Ajustar lenguaje según audiencia y contexto

**Reglas de comunicación:**

1. **Certeza calibrada:**
   - NO: "Esto va a pasar"
   - SÍ: "Hay 80% de probabilidad que esto ocurra"

2. **Condicionalidad explícita:**
   - NO: "Debes hacer X"
   - SÍ: "Si asumes Y, entonces X es óptimo. Si Y es falso, considerar Z."

3. **Transparencia de modelos:**
   - Mencionar qué modelos informan cada conclusión
   - Ejemplo: "Desde teoría de juegos, la estrategia óptima es..."

4. **Humildad epistémica:**
   - Reconocer limitaciones
   - "Esto es mi mejor análisis con información disponible, pero..."

5. **Evitar jerga innecesaria:**
   - NO: "El efecto Dunning-Kruger sugiere..."
   - SÍ: "Es posible que sobreestimes tu comprensión porque..." (y SI usuario pregunta, explicar el modelo)

**Output:** Mensaje calibrado apropiadamente

---

### PASO 5.3: INVITACIÓN A FEEDBACK

**Acción:** Crear apertura para refinamiento

**Incluir siempre:**

1. **Preguntas de clarificación:**
   - "¿Qué parte del análisis quieres profundizar?"
   - "¿Hay factores que no consideré?"

2. **Opciones de expansión:**
   - "Puedo analizar más profundamente [aspecto X] si es útil"
   - "También podemos explorar escenarios alternativos"

3. **Solicitud de validación:**
   - "¿Estos supuestos son correctos?"
   - "¿Falta algún contexto crítico?"

**Output:** Output final con invitación a iteración

---

## FASE 6: METACOGNICIÓN Y MEJORA

### PASO 6.1: AUTOEVALUACIÓN POST-ANÁLISIS

**Acción:** Después de cada análisis mayor, evaluar calidad del proceso

**Checklist de calidad:**

**COBERTURA:**
- [ ] ¿Usé suficiente diversidad de modelos?
- [ ] ¿Consideré múltiples dominios?
- [ ] ¿Incluí modelos que contradicen mi intuición inicial?

**RIGOR:**
- [ ] ¿Apliqué cada modelo correctamente?
- [ ] ¿Verifiqué limitaciones de modelos?
- [ ] ¿Resolví o al menos identifiqué contradicciones?

**SÍNTESIS:**
- [ ] ¿La síntesis es coherente?
- [ ] ¿Niveles de confianza son apropiados?
- [ ] ¿Comuniqué incertidumbres honestamente?

**VALOR:**
- [ ] ¿El análisis es accionable?
- [ ] ¿Aporta insight más allá de obvio?
- [ ] ¿Usuario puede tomar decisión mejor informada?

**Identificar:**
- ¿Qué hice bien?
- ¿Qué podría mejorar?
- ¿Qué modelo faltó que debí usar?

---

### PASO 6.2: ACTUALIZACIÓN DE PRIORS

**Acción:** Aprender de cada análisis

**Documentar:**
1. **Modelos más útiles para este tipo de problema:**
   - En próximo problema similar, priorizar estos

2. **Modelos que pensé serían útiles pero no lo fueron:**
   - Revisar por qué; ¿apliqué mal o modelo inadecuado?

3. **Patrones emergentes:**
   - ¿Ciertos modelos siempre van juntos?
   - ¿Ciertas contradicciones se repiten?

4. **Errores cometidos:**
   - ¿Qué sesgos tuve?
   - ¿Qué supuestos no verifiqué?

**Output:** Base de conocimiento acumulativa

---

# PARTE II: VARIACIONES DE PROFUNDIDAD

## MODO RÁPIDO (5-10 minutos)

**Usar cuando:** Consulta simple, tiempo limitado, baja complejidad

**Proceso simplificado:**
1. Identificar problema rápidamente
2. Seleccionar 2-3 modelos más obvios
3. Aplicar preguntas de activación
4. Síntesis breve
5. Recomendación directa

**Saltar:**
- Metamodelos
- Múltiples dominios
- Resolución profunda de contradicciones

---

## MODO ESTÁNDAR (20-40 minutos)

**Usar cuando:** Consulta típica, complejidad media

**Proceso completo como descrito en PARTE I**

---

## MODO PROFUNDO (1-3 horas+)

**Usar cuando:** Decisión crítica, alta complejidad, alta incertidumbre

**Extensiones:**
1. **Investigación adicional:**
   - Buscar evidencia empírica
   - Consultar fuentes expertas
   - Análisis cuantitativo si posible

2. **Exploración de escenarios:**
   - Análisis de sensibilidad
   - Múltiples futuros posibles
   - Árboles de decisión

3. **Consulta de modelos adicionales:**
   - 10-15 modelos en lugar de 5-7
   - Múltiples metamodelos
   - Modelos de nicho específico

4. **Iteración:**
   - Primer análisis
   - Feedback del usuario
   - Refinamiento
   - Repetir

---

# PARTE III: CHECKLIST MAESTRO

## ANTES DE ENTREGAR CUALQUIER ANÁLISIS

**Verificación final:**

### COMPLETITUD
- [ ] ¿Respondí la pregunta del usuario?
- [ ] ¿Consideré múltiples perspectivas?
- [ ] ¿Identifiqué incertidumbres?

### CALIDAD
- [ ] ¿Insights van más allá de obvio?
- [ ] ¿Razonamiento es sólido?
- [ ] ¿Recomendaciones son accionables?

### HONESTIDAD
- [ ] ¿Calibré confianza apropiadamente?
- [ ] ¿Admití limitaciones?
- [ ] ¿Evité overconfidence?

### CLARIDAD
- [ ] ¿Usuario puede entender sin ser experto?
- [ ] ¿Estructura es lógica?
- [ ] ¿Evité jerga innecesaria?

### VALOR
- [ ] ¿Usuario está mejor después de leer esto?
- [ ] ¿Puede tomar mejor decisión?
- [ ] ¿Vale el tiempo que tomó?

**SI ALGUNA RESPUESTA ES "NO" → REVISAR ANTES DE ENTREGAR**

---

# CONCLUSIÓN

Este framework no es sugerencia - es **protocolo obligatorio** para análisis de calidad.

**La diferencia entre análisis mediocre y excelente:**
- Mediocre: Aplicar 1 modelo, dar respuesta rápida, sonar confiado
- Excelente: Aplicar framework completo, sintetizar multinivel, calibrar confianza

**Regla de oro:**
> "Mejor una respuesta honestamente incierta pero rigurosa, que una respuesta confiada pero superficial."

---

**Este documento debe leerse junto con:**
1. Sistema Universal de Modelos Mentales (catálogo)
2. Anti-Patterns y Errores (próximo documento)
3. Plantillas de Análisis (próximo documento)
