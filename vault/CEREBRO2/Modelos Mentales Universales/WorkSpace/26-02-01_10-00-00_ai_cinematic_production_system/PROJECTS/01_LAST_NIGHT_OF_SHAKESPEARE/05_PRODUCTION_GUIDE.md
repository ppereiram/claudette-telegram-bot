# GUÍA DE PRODUCCIÓN EJECUTIVA: PASO A PASO
**Proyecto:** The Last Night of Shakespeare

## ⏱️ DURACIÓN ESTIMADA
**Tiempo Total:** 1:30 a 2:00 minutos.
*   **Por qué:** El terror atmosférico necesita "respirar". No cortes rápido. Deja que la incomodidad de la mirada de Otelo o el silencio de la casa duren unos segundos más de lo cómodo.

---

## FASE 1: GENERACIÓN DE IMÁGENES (EL RODAJE ESTÁTICO)
**Herramienta Sugerida:** Midjourney v6 (Mejor calidad artística).

1.  [ ] Abre el archivo `03_SHOT_LIST_AND_PROMPTS.md`.
2.  [ ] Copia el prompt del **SHOT 1**.
3.  [ ] Genera 4 variaciones.
4.  [ ] **Elige la mejor:** Busca la que tenga la iluminación más dramática (Chiaroscuro). No te preocupes si hay pequeños errores, se ocultarán en la oscuridad.
5.  [ ] **Upscale:** Escala la imagen elegida.
6.  [ ] **Repetir:** Haz esto para los 10 shots de la lista.
    *   *Tip:* Guarda las imágenes en una carpeta llamada `ASSETS/IMG` numeradas (01_Camino.png, 02_Cara.png...).

## FASE 2: ANIMACIÓN (DARLE VIDA)
**Herramienta Sugerida:** Runway Gen-2, Kling o Luma Dream Machine.

1.  [ ] Ve a tu herramienta de Video IA.
2.  [ ] Selecciona **"Image to Video"** (No Text to Video).
3.  [ ] Sube la imagen del **SHOT 1**.
4.  [ ] **El Prompt de Movimiento:** Escribe una instrucción simple.
    *   *Ejemplo:* "Subtle smoke movement, moon glow, slow camera push in".
5.  [ ] **Motion Brush (Truco Pro):** Si usas Runway, usa el pincel para pintar *solo* las nubes o la capa de Shakespeare. Deja el suelo quieto para evitar que se deforme.
6.  [ ] Genera 2 o 3 versiones de cada shot. Quédate con la que tenga menos "morphing" (deformaciones raras).
7.  [ ] Descarga los clips a `ASSETS/VIDEO`.

## FASE 3: LAS VOCES (EL ALMA)
**Herramienta Sugerida:** ElevenLabs.

1.  [ ] Abre `02_SCREENPLAY.md`.
2.  [ ] **Casting de Voz:**
    *   **Shakespeare:** Busca una voz "Old British male", baja la "Stability" al 30% para que suene temblorosa/ebria.
    *   **Otelo:** Voz "Deep narration", tono solemne.
3.  [ ] Genera los diálogos frase por frase.
4.  [ ] Descarga los audios a `ASSETS/AUDIO`.

## FASE 4: EL MONTAJE (LA MAGIA)
**Herramienta:** CapCut (PC), Premiere Pro o DaVinci Resolve.

**Paso 4.1: El Esqueleto de Audio (Haz esto PRIMERO)**
1.  Arrastra las voces a la línea de tiempo.
2.  Arrastra los efectos de sonido (Viento, Crujidos) de `04_SOUND_DESIGN.md`.
3.  Ajusta los silencios. Deja 3 segundos de silencio total antes de que hable la cabeza de Macbeth. **El ritmo lo marca el audio, no el video.**

**Paso 4.2: Vestir con Video**
1.  Pon los videos generados encima del audio correspondiente.
2.  Si un video es muy corto, usa la opción de "Velocidad" para ralentizarlo (0.8x) y que dure lo que dura la frase.

**Paso 4.3: Etalonaje y Efectos (El Look Final)**
1.  **Filtro:** Aplica un filtro de "Blanco y Negro" o desatura los colores al 50% para unificar el look de Eggers.
2.  **Grano:** Añade una capa de "Film Grain" o ruido visual encima de todo. Esto hace que el video digital parezca cine de 1616 y oculta imperfecciones de la IA.

## CHECKLIST DE CALIDAD FINAL
*   [ ] ¿Se entiende lo que dicen los personajes?
*   [ ] ¿El negro es negro puro o gris lavado? (Debe ser oscuro).
*   [ ] ¿Hay coherencia visual entre Otelo y Macbeth? (Mismo estilo de luz).
