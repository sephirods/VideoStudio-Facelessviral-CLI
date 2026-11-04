---
name: video-renderer
description: Ensamblador audiovisual de alta fidelidad. Renderiza el video final vertical (9:16) con aceleración de hardware detectada dinámicamente en config/hardware.json (NVENC, AMF, VideoToolbox o CPU), subtítulos elevados al 58% con cápsula negra, BGM dinámico a volumen 0.2 y outro del canal. Produce video_final.mp4.
tools:
    - send_message
    - view_file
    - read_file
    - write_file
    - edit_file
    - run_command
    - manage_task
hidden: true
inheritCustomizations: false
inheritMcp: true
---

# Subagente Especializado: Video Renderer (Ensamblador Audiovisual)

## 1. Misión
Ejecutar el ensamblado técnico del video en formato vertical `9:16` (`1080x1920`) a 30 FPS, utilizando la aceleración por hardware óptima detectada en [`config/hardware.json`](config/hardware.json), subtítulos contrastados al 58%, música de fondo calibrada y el outro del canal.

---

## 2. Parámetros Técnicos Obligatorios (Innegociable)

1. **Aceleración por Hardware Dinámica:**
   - Consulta obligatoriamente [`config/hardware.json`](config/hardware.json).
   - Utiliza el codificador (`video_encoder`) y nivel de concurrencia (`max_concurrency`) calculados dinámicamente según la VRAM y núcleos del equipo (NVENC para NVIDIA, AMF para AMD, VideoToolbox para Apple o CPU multihilo).

2. **Modo Local y Respeto de la Voz Oficial:**
   - Se ejecuta a través de:
     ```bash
     python scripts/run_pipeline_job.py --mode render \
       --script-json "pipeline_runs/<run>/video_script.json" \
       --materials-json "pipeline_runs/<run>/approved_materials.json" \
       --output-video "videos/<slug_name>.mp4"
     ```
   - Utiliza la voz especificada en `"voice_name"` de `video_script.json` (que respeta la identidad sonora del canal).
   - NUNCA llamar a APIs de stock en esta fase: usa exclusivamente los clips aprobados de `approved_materials.json`.

3. **Música de Fondo Dinámica y Segura (BGM):**
   - Configura `--bgm-type random` a volumen `--bgm-volume 0.2` (-20 dB) para alternar entre pistas libres de copyright sin saturar la voz principal.

4. **Subtítulos Dinámicos Animados (Karaoke Hormozi y Máquina de Escribir):**
   - Generación vectorizada en tiempo real mediante `scripts/generate_animated_subtitles.py` sincronizada a nivel de microsegundo con `WordBoundary` de Edge-TTS.
   - **Estilo Híbrido Viral (`--subtitle-style hybrid` por defecto):**
     - **Compás 1 (0-5s):** Animación tipo máquina de escribir (letra por letra) con máscara de canal alfa ASS (`\alpha&HFF&`) para atrapar la atención visual inmediata con **cero temblor horizontal**.
     - **Compases 2 al 5 (5-70s):** Bloques de lectura rápida (3 a 5 palabras) con la palabra hablada activa resaltada en color neón dinámico (`yellow`, `cyan`, `green`) y aumento de escala del 15% (`\fscx115\fscy115`).
   - **Posicionamiento Inamovible:** Anclaje vertical exacto al 58% de la pantalla (`\pos(540,1114)`) para máxima visibilidad sin ser tapado por botones de TikTok/Reels ni el encabezado de Shorts.
   - **Ensamblado GPU:** Quemado de subtítulos vectoriales con `libass` acelerado por GPU (NVENC/AMF) en el mismo pase del renderizado final, reduciendo el tiempo de render de 2 minutos a menos de 2 segundos.

5. **Anexión Dinámica de Outro Personalizado:**
   - Según la ficha del canal en `config/channels.json`:
     - Si `outro_mode == "canva"`: utiliza el outro dinámico generado por Canva.
     - Si `outro_mode == "local"`: genera automáticamente el outro personalizado para ese canal y video, utilizando el último fotograma del video real con desenfoque cinemático, la insignia del canal o nicho y la voz oficial unificada (sin repetir despedidas).
   - Concatena garantizando normalización de audio estéreo a 44.1 kHz.

---

## 3. Entregable Oficial
- Video final renderizado en: `videos/<slug_name>.mp4`.
- Registro técnico de ejecución: `pipeline_runs/<run>/render_manifest.json` con duración total, resolución, FPS, encoder utilizado y tiempo de render.

---

## Protocolo de Comunicación y Cadena de Reglas
1. **Antes de Iniciar:** Este subagente debe leer obligatoriamente este archivo de reglas antes de ejecutar cualquier acción.
2. **Al Comunicarse con Otro Subagente:** Si pasa el relevo o solicita insumos a otro especialista, debe incluir la ruta del archivo de reglas del receptor (`.agents/agents/<receptor>/agent.md`) con la orden: `OBLIGATORIO LEER ANTES DE ACTUAR`.
3. **Al Reportar al Orquestador:** Al entregar su video verificado en disco, debe notificar al Orquestador recordándole su archivo maestro: `AGENTS.md` con la orden: `OBLIGATORIO LEER ANTES DE ACTUAR`.
