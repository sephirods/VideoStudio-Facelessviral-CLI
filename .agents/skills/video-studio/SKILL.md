---
name: video-studio
description: >-
  Motor maestro de producción desatendida y factoría de video viral para YouTube Shorts, TikTok e Instagram Reels.
  Utiliza 9 subagentes especializados, Motor Directo FFmpeg + GPU (NVENC / RTX 3070 en ~20s), fotos reales verificadas
  con Ken Burns sin deformación, Edge-TTS, subtítulos Hormozi sin parpadeo, cooldown de 30 días por grupo de canales
  y empaquetado automático con límite LRU de 1.5 GB.
---

# 🚀 Factoría de Video Viral (VideoStudio-Facelessviral-CLI)

Sistema de producción audiovisual desatendido con 9 subagentes especializados, deduplicación por grupo de canales y renderizado directo por GPU.

## 🗺️ Mapa de Control Rápido

| Componente | Ruta | Acción |
|---|---|---|
| **Instalador y Dependencias** | `scripts/setup_environment.py` | Audita Python, FFmpeg (`libass`/`nvenc`), dependencias y 9/9 subagentes. |
| **Contrato Maestro** | `AGENTS.md` | Reglas de despacho, gatekeeping estricto y paralelismo. |
| **Canales y Grupos** | `config/channels.json` | Configuración del canal activo, grupo anti-repetición, idioma y voz. |
| **Deduplicación (30 días)** | `scripts/content_deduplication.py` | Control bilingüe (ES/EN) de temas y dHash perceptual de miniaturas. |
| **Fotos Reales + Ken Burns** | `scripts/fetch_real_images.py` / `scripts/convert_image_to_clip.py` | Cuadrícula 2x2 HD (`candidates_grid.jpg`), `hero_image.jpg` y `hero_clip.mp4`. |
| **Motor de Render GPU** | `scripts/run_pipeline_job.py` | Ensamblado secuencial directo FFmpeg + NVENC (~20s) + outro paralelo. |
| **Auditoría QA en 1 Mirada** | `scripts/run_qa_audit.py` | Valida 62-72s con `ffprobe` y genera `qa_strip.jpg` con 5 marcas dinámicas. |
| **Empaquetado y Purga LRU** | `scripts/manage_storage_and_archive.py` | Empaqueta en `videos/publicaciones/[CANAL]/` y limita `cache_videos` a 1.5 GB. |
| **Sincronizador Triple** | `scripts/sync_workspaces.py` | Mantiene idénticos los 3 repositorios locales. |

---

## 🤖 Los 9 Subagentes Especializados

1. **`trend-researcher`**: Extrae tendencias en paralelo (ES/EN), verifica cooldown de 30 días (`content_deduplication.py`) y emite `trend_brief.json`.
2. **`viral-scriptwriter`**: Redacta guiones de 5 compases (duración obligatoria 62-72s, cero doble despedida) con la voz oficial del canal. Emite `video_script.json`.
3. **`viral-copywriter`**: Inteligencia paralela con `yt-dlp` y YouTube Autocomplete (`fetch_viral_intelligence.py`). Emite `viral_metadata.json`.
4. **`visual-asset-reviewer`**: Adquiere foto real del sujeto (`candidates_grid.jpg` -> `hero_image.jpg` -> `hero_clip.mp4` en posición `0`) y audita stock en mosaico único (`mosaico_clips.jpg`). Emite `approved_materials.json`.
5. **`video-renderer`**: Motor directo FFmpeg + GPU con orden secuencial estricto, subtítulos Hormozi al 58% con trazo negro nítido, BGM a 0.2 y outro personalizado en memoria. Emite `video_final.mp4` + `render_manifest.json`.
6. **`video-qa-validator`**: Ejecuta `run_qa_audit.py`, inspecciona `qa_strip.jpg` en 1 lectura y verifica rango universal 62-72s. Emite `qa_certificate.json` (`PASS`/`FAIL`).
7. **`thumbnail-designer`**: Se despacha **solo tras QA PASS**. Usa prioritariamente `hero_image.jpg` aprobada (o frame real del video) + badge 74px + Impact amarillo. Emite `miniatura_viral.jpg`.
8. **`packaging-archiver`**: Ejecuta `manage_storage_and_archive.py` creando `videos/publicaciones/[CANAL]/[FECHA]_[slug]/`, registra historial 30d y recorta caché a 1.5 GB LRU. Emite `package_manifest.json`.
9. **`social-media-publisher`**: Publicación desatendida en plataformas configuradas con sesiones aisladas.

---

## ⚡ Comandos Rápidos de Producción

```bash
# Diagnosticar entorno y verificar 9/9 subagentes
python scripts/setup_environment.py

# Pre-vuelo paralelo (cooldown 30d + sesiones + tendencias + inteligencia)
python scripts/produce_channel_video.py --channel canal_ejemplo

# Limpieza directa de almacenamiento con tope LRU de 1.5 GB
python scripts/manage_storage_and_archive.py --purge-only --max-cache-mb 1500
```
