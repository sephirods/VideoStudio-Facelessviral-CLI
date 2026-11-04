# 🚀 VideoStudio-Facelessviral-CLI
### Motor Maestro de Producción Desatendida con 9 Subagentes Especializados y 3 Pilares

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Multi-Agent](https://img.shields.io/badge/architecture-9%20Subagents-brightgreen.svg)]()

Este repositorio contiene la arquitectura completa, portátil y lista para producción de una **Factoría de Video Automatizada para YouTube Shorts, TikTok e Instagram Reels**. Diseñada para operar en cualquier CLI moderna (Antigravity, Freebuff, Claude Code, Cursor, Windsurf, Aider) y en cualquier sistema operativo (Windows, macOS, Linux).

---

## ⚡ Arranque Rápido en 3 Pasos (Quickstart)

```bash
# 1. Clonar el repositorio
git clone https://github.com/sephirods/VideoStudio-Facelessviral-CLI.git
cd VideoStudio-Facelessviral-CLI

# 2. Diagnóstico e instalación automática en 1 clic
python scripts/setup_environment.py

# 3. Producir video (o Modo Demo si aún no registras canales)
python scripts/produce_channel_video.py
```

---

## 🤖 Protocolo Universal para Agentes de IA (Freebuff, Claude Code, Cursor, Antigravity)

> **Instrucción de Sistema para el Asistente:**
> Si un usuario te proporciona el enlace a este repositorio (`https://github.com/sephirods/VideoStudio-Facelessviral-CLI`) o te pide operar en este espacio de trabajo:
> 
> 1. **Clonado Automático:** Si tu carpeta de trabajo actual está vacía o no contiene los scripts, clona el repositorio directamente:
>    ```bash
>    git clone https://github.com/sephirods/VideoStudio-Facelessviral-CLI.git .
>    ```
> 2. **Instalador de Entorno:** Ejecuta inmediatamente:
>    ```bash
>    python scripts/setup_environment.py
>    ```
> 3. **Rol del Orquestador:** Asume de inmediato el rol de **Director de Producción** regido por [`AGENTS.md`](AGENTS.md). 
>    - Comunícate siempre en **español claro, breve, empático y 100% humano**.
>    - **Cero tecnicismos, cero explicaciones robóticas de código** y cero justificaciones.
>    - Nunca modifiques el flujo del usuario ni pidas Google Cloud Console o API keys manuales.
> 4. **Paso 0 (Onboarding):** Revisa [`config/channels.json`](config/channels.json).
>    - Si está vacío (`"channels": {}`), da la bienvenida al usuario y preséntale de forma conversacional las 4 opciones de inicio:
>      - *A) Configurar mi primer Grupo de Canales ahora.*
>      - *B) Sugerir temáticas y nichos de alto RPM (usando el subagente `trend-researcher`).*
>      - *C) Generar un video piloto de prueba local (Modo Demo sin publicar).*
>      - *D) Saltar por ahora.*
>    - Si ya hay un canal configurado, repórtalo y pregunta qué tema producir hoy o si desea investigar tendencias.

---

## 🗺️ Mapa Rápido del Repositorio

| Archivo / Carpeta | Función Principal |
|---|---|
| [`scripts/setup_environment.py`](scripts/setup_environment.py) | **Instalador 1 Clic:** Audita Python >= 3.10, FFmpeg, instala librerías, detecta hardware y valida 9/9 agentes. |
| [`SETUP_ONBOARDING.md`](SETUP_ONBOARDING.md) | **Protocolo Onboarding (Paso 0):** Entrevista guiada "Grill-Me", vinculación interactiva de cuentas y cadencia. |
| [`AGENTS.md`](AGENTS.md) / [`AGENT.md`](AGENT.md) | **Contrato del Orquestador:** Reglas de despacho, gatekeeping estricto, macro-paralelismo y tiempos. |
| `.agents/agents/<nombre>/agent.md` | **Directorio de los 9 Subagentes:** Misión, herramientas y especificación de entregables. |
| [`config/channels.json`](config/channels.json) | **Fichas de Canales:** Configuración de canales activos, nichos, plataformas y estilo. |
| `config/sessions/[canal]/` | **Almacén de Sesiones:** Credenciales y cookies aisladas por canal (protegidas por `.gitignore`). |
| [`config/hardware.json`](config/hardware.json) | **Hardware Doctor:** Encoder detectado (`h264_nvenc`, `h264_amf`, `h264_videotoolbox` o CPU) y concurrencia. |
| `videos/publicaciones/[CANAL]/` | **Entrega Final:** Paquetes fechados con video aprobado, miniatura viral y `copy_publicacion.txt`. |

---

## 🤖 Directorio Oficial de los 9 Subagentes

```mermaid
flowchart TD
    A["1. trend-researcher<br/>(Demanda real y nichos)"] -->|trend_brief.json| B["2. viral-scriptwriter<br/>(Guión 5 compases: 140-165 pal, 62-72s)"]
    B -->|video_script.json| C{"Bifurcación en Paralelo"}
    C -->|Rama SEO| D["3. viral-copywriter<br/>(Investigación real: Título <70 chars, tags y debate)"]
    C -->|Rama Stock| E["4. visual-asset-reviewer<br/>(Descarga paralela 4 hilos + B-Roll)"]
    D -->|viral_metadata.json| F["5. video-renderer<br/>(Hardware detectado en config/hardware.json)"]
    E -->|approved_materials.json| F
    F -->|video_final.mp4| G["6. video-qa-validator<br/>(Auditoría multi-segundo 5s, 25s, 45s, 62s)"]
    G -->|qa_certificate.json = PASS| H["7. thumbnail-designer<br/>(Extracción de fotograma real + Badge 74px)"]
    H -->|miniatura_viral.jpg| I["8. packaging-archiver<br/>(Carpeta fechada + purga caché)"]
    I -->|package_manifest.json| J["9. social-media-publisher<br/>(Distribución con sesiones aisladas)"]
```

1. **`trend-researcher`**: Análisis empírico de mercado y volumen según el propósito (`monetization` vs `entertainment`).
2. **`viral-scriptwriter`**: Redacción de guiones de 5 compases con gancho y sujeto ancla (62-72s, >60s para fondos de monetización).
3. **`viral-copywriter`**: Inteligencia de competencia con YouTube Autocomplete y `yt-dlp`. Títulos obligatorios $< 70$ caracteres, tags de doble capa y comentario fijado de debate.
4. **`visual-asset-reviewer`**: Descarga paralela en 4 hilos de clips de stock, auditoría visual de frames y archivado en B-Roll.
5. **`video-renderer`**: Ensamblado acelerado por GPU (NVENC/AMF/CPU), subtítulos al 58% con cápsula negra y outro dinámico.
6. **`video-qa-validator`**: Gatekeeper multi-segundo (5s, 25s, 45s, 62s). Emite `qa_certificate.json` (`PASS` / `FAIL`).
7. **`thumbnail-designer`**: Se despacha **únicamente tras QA PASS**. Extrae el fotograma heroico del video real y monta el badge móvil de 74px con tipografía Impact amarillo eléctrico.
8. **`packaging-archiver`**: Crea la carpeta fechada `videos/publicaciones/[CANAL]/[FECHA]_[slug]/`, redacta `copy_publicacion.txt` y purga la caché pesada.
9. **`social-media-publisher`**: Publicación desatendida leyendo las sesiones aisladas en `config/sessions/[canal]/`.

---

## 🔑 Protocolo de Vinculación Interactiva de Cuentas (Zero-Tech)

Para conectar plataformas (YouTube Shorts, TikTok, Instagram) sin exigir al usuario claves de Google Cloud ni pasos complejos:

1. **El Orquestador habla de forma humana y directa:**
   > *"Te abro una ventana en tu pantalla. Inicias sesión en tu cuenta como siempre, el sistema detecta que entraste, guarda la sesión y cierra la ventana sola."*
2. **Lanzador Interactivo Universal:**
   - **En Windows:** Utiliza `schtasks /create ... /it /f` seguido de `schtasks /run` a través de [`scripts/run_connect.bat`](scripts/run_connect.bat). La bandera `/it` permite a Windows romper el aislamiento de fondo y mostrar la ventana en el monitor físico del usuario.
   - **En Linux / macOS:** Ejecuta directamente `python3 scripts/connect_account.py --channel [canal] --platform [plataforma]`.
3. **Cierre y Aislamiento Automático:**
   - [`scripts/connect_account.py`](scripts/connect_account.py) abre Google Chrome con protecciones anti-bloqueo.
   - Al detectar las cookies de sesión activa (`LOGIN_INFO`, `SSID`, `SID` o `sessionid`), guarda el estado en `config/sessions/[canal]/[plataforma]_session.json` y **cierra la ventana automáticamente**.
   - Cada canal opera en su propia carpeta aislada, evitando cruces entre marcas.
