---
name: video-studio
description: >-
  Motor maestro de producción desatendida y factoría de video viral para YouTube Shorts, TikTok e Instagram Reels.
  Utiliza 9 subagentes especializados, aceleración por hardware (NVENC / RTX 3070), MoneyPrinterTurbo, Edge-TTS,
  b-roll inteligente y empaquetado automático. Úsalo para crear videos virales automatizados, investigar nichos y tendencias,
  redactar guiones de 5 compases (>60s para monetización), renderizar con subtítulos contrastados y empaquetar publicaciones.
---

# 🚀 Factoría de Video Viral (VideoStudio-Facelessviral-CLI)

Sistema de producción audiovisual desatendido con 9 subagentes especializados y aceleración por GPU.

## 🗺️ Mapa de Control Rápido

| Componente | Ruta | Acción |
|---|---|---|
| **Instalador y Dependencias** | `scripts/setup_environment.py` | Audita Python, FFmpeg, dependencias y 9/9 subagentes. |
| **Canales y Perfiles** | `config/channels.json` | Configuración del canal activo, nicho, plataformas y estilo. |
| **Aceleración Hardware** | `config/hardware.json` | Configuración de GPU detectada (`h264_nvenc` en RTX 3070). |
| **Onboarding y Grill-Me** | `SETUP_ONBOARDING.md` | Protocolo guiado de bienvenida, canales y diagnóstico. |
| **Contrato Maestro** | `AGENTS.md` / `AGENT.md` | Reglas de despacho, gatekeeping estricto y paralelismo. |
| **Subagentes Especialistas** | `.agents/agents/<nombre>/agent.md` | Definición de los 9 especialistas de producción. |
| **Entregables Finales** | `videos/publicaciones/[CANAL]/` | Paquetes aprobados con video, miniatura y copy. |

---

## 🤖 Los 9 Subagentes Especializados

1. **`trend-researcher`**: Analiza tendencias con Google Trends y feeds virales. Emite `trend_brief.json`.
2. **`viral-scriptwriter`**: Redacta guiones hipnóticos de 5 compases (140-165 palabras, 62-72s para Creator Rewards). Emite `video_script.json`.
3. **`viral-copywriter`**: Inteligencia de competencia con YouTube Autocomplete. Título <70 caracteres, tags doble capa y comentario de debate. Emite `viral_metadata.json`.
4. **`visual-asset-reviewer`**: Descarga y audita stock en 4 hilos paralelos. Emite `approved_materials.json`.
5. **`video-renderer`**: Ensambla con aceleración de hardware (NVENC), subtítulos al 58% con cápsula negra y outro. Emite `video_final.mp4`.
6. **`video-qa-validator`**: Gatekeeper multi-segundo (5s, 25s, 45s, 62s). Emite `qa_certificate.json` (PASS/FAIL).
7. **`thumbnail-designer`**: Se despacha **solo tras QA PASS**. Extrae frame heroico real y genera badge 74px amarillo eléctrico. Emite `miniatura_viral.jpg`.
8. **`packaging-archiver`**: Crea la carpeta fechada `videos/publicaciones/[CANAL]/[FECHA]_[slug]/`, redacta `copy_publicacion.txt` y purga la caché pesada.
9. **`social-media-publisher`**: Publicación desatendida en plataformas configuradas.

---

## ⚡ Comandos Rápidos de Producción

```bash
# Diagnosticar entorno y verificar 9/9 subagentes
python scripts/setup_environment.py

# Iniciar producción autónoma para el canal activo (ej: canal_ejemplo)
python scripts/produce_channel_video.py --channel canal_ejemplo

# Extracción de inteligencia de tendencias en tiempo real
python scripts/fetch_trends_data.py
```
