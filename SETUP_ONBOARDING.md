# Paso 0: Diagnóstico de Entorno, Onboarding y Configuración Flexible

Este documento define el protocolo del **Paso 0** que el CLI y el Orquestador ejecutan antes o durante la producción de videos. Diseñado para ser un motor maestro portátil, listo para clonarse desde GitHub y operar en cualquier equipo.

---

## 🗺️ Mapa de Control Rápido del Repositorio (Acceso Inmediato)

Cualquier agente u orquestador que clone este repositorio encuentra todo en estas rutas exactas:

| Elemento / Tarea | Archivo / Carpeta Exacta | Qué se hace aquí |
|---|---|---|
| **Registro de Canales** | [`config/channels.json`](config/channels.json) | Añadir, editar o cambiar el canal activo y sus nichos. |
| **Configuración de Hardware** | [`config/hardware.json`](config/hardware.json) | GPU detectada (NVENC, AMF, VideoToolbox) o CPU. |
| **Protocolo de Onboarding** | [`SETUP_ONBOARDING.md`](SETUP_ONBOARDING.md) | Flujo paso a paso de la entrevista "Grill-Me" y doctor. |
| **Contrato del Orquestador** | [`AGENTS.md`](AGENTS.md) | Reglas de despacho, gatekeeping y paralelismo. |
| **Reglas de Subagentes** | `.agents/agents/<nombre>/agent.md` | Prompts y herramientas de cada especialista. |
| **Entregables Finales** | `videos/publicaciones/[CANAL]/[FECHA]_[slug]/` | Paquetes listos para subir a redes o consumo. |

---

## 1. Fase de Diagnóstico Automático (CLI Doctor)

Antes de operar, el sistema audita el entorno para optimizar el rendimiento sin configuraciones manuales:

1. **Detección de Hardware de Video:**
   - **NVIDIA GPU:** Detecta CUDA/NVENC (`h264_nvenc`). Configura concurrencia x4 por hardware.
   - **AMD GPU:** Detecta AMF (`h264_amf`).
   - **Apple Silicon:** Detecta VideoToolbox (`h264_videotoolbox`).
   - **CPU Fallback:** Selecciona codificación multihilo CPU (`libx264`, preset `fast`).
   - *Persistencia:* Guarda el resultado en [`config/hardware.json`](config/hardware.json).

2. **Verificación de Dependencias Esenciales:**
   - Python 3.10+ (entorno virtual activo).
   - FFmpeg con soporte de códecs de audio/video.
   - Node.js (para utilidades y MCPs).
   - Edge-TTS y Whisper (o alternativas locales).

---

## 2. Entrevista de Configuración Inicial ("Grill-Me" de Canales)

Cuando el Orquestador detecta que [`config/channels.json`](config/channels.json) está vacío, o cuando el usuario escribe `configurar canal`, se ejecuta el siguiente flujo interactivo:

### Paso 1: Selección de Modo Inicial
- **A) Configurar mi primer Grupo de Canales ahora.**
- **B) Sugerir temáticas primero:** El Analizador de Tendencias explora el mercado y presenta sugerencias sin guardar nada aún.
- **C) Modo Prueba / Demo:** Generar un video piloto de prueba local sin registrar canales ni publicar.
- **D) Saltar por ahora:** Continuar en modo libre y configurar los canales más tarde a pedido.

---

### Paso 2 (Si elige Configurar Canal): Propósito del Canal
- **Monetización / Ganancias (Alto RPM):**
  - Filtros de alta retención, curiosidad y nichos de alto valor comercial (finanzas, tecnología, negocios, psicología persuasiva, misterio intrigante).
  - Guión de 140-165 palabras (62-72s) para calificar en fondos de creadores (>60s).
- **Entretenimiento / Viralidad Pura / Marca Personal:**
  - Enfoque relajado: humor, anécdotas, datos asombrosos, gaming, cultura pop.
  - Prioriza consumo masivo y viralidad general.

---

### Paso 3: Identidad y Temática
- **Nombre del Grupo de Canales:** (Ej: *Mente Oculta*, *CuriosaMente*, *Finanzas Pro*).
- **Temática / Nicho Principal:**
  - Si el usuario la define: se toma directamente.
  - Si no sabe qué nicho elegir: se despacha a `trend-researcher` con el propósito elegido para generar 2-3 propuestas respaldadas por tendencias.

---

### Paso 4: Plataformas de Publicación (Multi-Red)
- ¿En qué plataformas se distribuirá este canal automáticamente?
  - `youtube_shorts`: YouTube Shorts (Monetización oficial y tráfico de búsqueda).
  - `tiktok`: TikTok (Creator Rewards Program >60s).
  - `instagram_reels`: Instagram Reels (Engagement y marca personal).
  - `facebook_reels`: Facebook Reels (Audiencia adulta de alto RPM comercial).
  - `linkedin`: LinkedIn Video (Tráfico profesional de alta conversión B2B).
  - `x_twitter`: X / Twitter (Video nativo en timeline).

*(La IA inyecta de forma 100% desatendida en cada red el título <70 chars, la descripción formateada, los tags de doble capa, la miniatura móvil y el comentario fijado de debate sin que el usuario tenga que escribir nada).*

---

### Paso 5: Vinculación Interactiva de Cuentas (1 Clic, Zero-Tech y Aislamiento por Canal)

Cuando el usuario selecciona las plataformas donde desea publicar automáticamente (ej: YouTube Shorts, TikTok, Instagram Reels), el Orquestador realiza la vinculación de forma **100% humana, sin tecnicismos y sin pedir cuentas de Google Cloud**:

#### 1. Comunicación con el Usuario:
> **🎬 Director de Producción:**
> Para que los videos se publiquen solos en tu canal **[Nombre del Canal]** sin que tengas que subirlos a mano, solo conectamos tu cuenta **una sola vez**:
> 1. Te abro una ventana normal en tu pantalla.
> 2. Inicias sesión con tu cuenta como siempre.
> 3. En cuanto entras, la ventana detecta tu acceso, guarda la sesión y **se cierra sola**.
>
> ¿Te abro la ventana ahora para conectar **YouTube**?

#### 2. Mecanismo Técnico Universal de Lanzamiento Visual (Multi-OS):
- **En Windows (Aislamiento de Fondo Solucionado con `/it`):**
  Para que la ventana salte al monitor físico interactivo del usuario y no quede atrapada en subprocesos invisibles, el sistema utiliza el Programador de Tareas con la bandera interactiva `/it`:
  ```powershell
  schtasks /create /tn "AntigravityConnectChannel" /tr "'%CD%\scripts\run_connect.bat' [canal] [plataforma]" /sc once /st 23:59 /it /f; schtasks /run /tn "AntigravityConnectChannel"
  ```
- **En Linux / macOS:**
  Ejecuta directamente:
  ```bash
  python3 scripts/connect_account.py --channel [canal] --platform [plataforma]
  ```

#### 3. Monitor Inteligente y Cierre Automático (`scripts/connect_account.py`):
- Abre **Google Chrome real** con banderas anti-automatización (`--disable-blink-features=AutomationControlled`) para que Google o TikTok jamás bloqueen el acceso.
- El usuario ingresa sus credenciales normales.
- El script vigila las cookies y URLs en tiempo real:
  - **YouTube:** Detecta cookies `LOGIN_INFO`, `SSID`, `SID` o navegación a `studio.youtube.com/channel/...`.
  - **TikTok:** Detecta cookie `sessionid` y salida de `/login`.
  - **Instagram:** Detecta cookie `sessionid` y salida de `accounts/login`.
- Al confirmar el acceso:
  1. Asienta tokens durante 2.5 segundos.
  2. Guarda la sesión aislada en:
     ```
     config/sessions/[channel_id]/[plataforma]_session.json
     ```
  3. Cierra la ventana automáticamente.
  4. Elimina la tarea temporal de `schtasks`.

#### 4. Aislamiento Estricto para Múltiples Canales:
- Cada canal tiene su propia carpeta:
  - Canal 1 (Finanzas): `config/sessions/canal_finanzas/youtube_session.json`
  - Canal 2 (Misterio): `config/sessions/misterios_mundo/youtube_session.json`
  - Canal 3 (Humor): `config/sessions/risas_top/tiktok_session.json`
- El publicador lee **únicamente** la carpeta del canal activo. Imposible mezclar publicaciones o credenciales entre marcas.

---

### Paso 6: Servicios Visuales y Outro
- **¿Dispones de cuenta en Canva conectada?**
  - **Sí:** Utiliza el MCP de Canva para intros/outros dinámicas y plantillas.
  - **No:** Ofrece el enlace de registro (`https://www.canva.com/`) o activa la **Plantilla Local** (FFmpeg/Pillow genera el outro automáticamente en disco sin servicios externos).

---

### Paso 7: Gestión de Almacenamiento y Material Visual de Stock
El Orquestador consulta al creador cómo prefiere administrar los clips de video descargados:
> **🎬 Pregunta Grill-Me:**
> ¿Cómo prefieres que gestionemos el material visual que descargamos para tus videos?
> - **A) Crear Biblioteca Local de Calidad (Recomendado):** Guardamos los mejores clips en `videos/biblioteca_stock/` para reutilizarlos en futuros videos. Ahorra tiempo de descarga, consume menos internet y agiliza el renderizado.
> - **B) Modo Ahorro de Espacio en Disco:** Borramos los clips temporales de stock inmediatamente después de aprobar el video final. Mantiene tu disco limpio y descarga material 100% nuevo en cada producción.

---

### Paso 8: Cadencia de Operación y Disparador Universal (Multi-CLI)
- **El usuario decide el ritmo**, pero el Orquestador le presenta la **recomendación algorítmica**:
  > *💡 Recomendación de crecimiento:* Para ganar tracción en YouTube Shorts y TikTok sin saturar al algoritmo ni arriesgar shadowban, lo óptimo es **1 a 2 videos diarios**, preferentemente en horas pico (13:00 y 19:00 hora local).
- **Modalidades a elegir:**
  - **A Pedido (Bajo Demanda):** El sistema solo genera videos cuando tú des la orden explícita en tu terminal (`crear video para canal X`).
  - **Piloto Automático (Programado):** 
    - Define la hora y frecuencia (ej. *"Todos los días a las 19:00"* o *"Lunes, Miércoles y Viernes"*).
    - **Detección Automática de Motor:**
      - Si estás en **Antigravity**: Registra un cron nativo con `/schedule`.
      - Si estás en **Windows (CLI/Terminal estándar)**: Registra una Tarea Programada de Windows con `schtasks.exe`.
      - Si estás en **Linux/macOS**: Registra una entrada en el `crontab` del sistema.
      - O inicia el servicio en segundo plano: `python scripts/universal_scheduler.py --channel <id> --daemon`.

---

## 3. Protocolo de Verificación en Turno 1 (Antes de Producir)

Antes de iniciar la redacción o renderizado de cualquier video para un canal con cuentas vinculadas, el Orquestador ejecuta una **comprobación preventiva de 1 segundo**:
1. Comprueba si existen los archivos en `config/sessions/[canal]/`.
2. Si una sesión venció o no existe, **avisa al usuario de inmediato en el Turno 1**:
   > *"Aviso rápido: la sesión de YouTube para este canal necesita renovarse. ¿Te abro la ventana 1 minuto para refrescarla o prefieres generar el video en modo local?"*
3. Esto evita gastar minutos de CPU/GPU generando un video para luego descubrir al final que la subida fue rechazada por sesión caducada.

---

## 4. Flujo para Crear Nuevos Canales (Reutilización del Grill-Me)

El Grill-Me no es un evento de una sola vez. Cada vez que el usuario decida expandir su red y diga:
- *"Quiero abrir otro canal"*
- *"Añadir nuevo canal"*
- O use una orden similar

El Orquestador vuelve a ejecutar la entrevista (Pasos 2 al 5) para el nuevo canal y lo añade en [`config/channels.json`](config/channels.json) bajo una nueva clave:

```json
{
  "active_default_channel": "canal_1",
  "channels": {
    "canal_1": {
      "name": "Mente Oculta",
      "niche": "Psicología y Lenguaje Corporal",
      "purpose": "monetization",
      "platforms": ["youtube_shorts", "tiktok"]
    },
    "canal_2": {
      "name": "Risas Diarias",
      "niche": "Humor y Anécdotas",
      "purpose": "entertainment",
      "platforms": ["tiktok", "instagram_reels"]
    }
  }
}
```
*Al terminar, pregunta al usuario si desea fijar el nuevo canal como canal activo predeterminado o conservar el anterior.*

---

### 3. Aislamiento Estricto de Cuentas y Cookies por Canal
Para que un creador pueda operar **múltiples canales de YouTube, TikTok o Instagram** (ej: 4 canales de temáticas distintas) desde la misma computadora sin cruce de credenciales:
- Cada canal tiene su propio almacén de sesiones aislado en:
  ```
  config/sessions/[channel_id]/
  ```
- Al publicar, el sistema invoca la sesión específica de ese canal (`--account [channel_id]`).
- Es imposible que un video de un canal se suba a la cuenta de otro, garantizando independencia total de marcas.

---

## 4. Modos Flexibles de Operación

1. **Modo Producción Vinculada a Canal:**
   - La orden indica el canal (ej: *"video para 'Risas Diarias'"*) o usa el fijado en `active_default_channel`.
   - Aplica el propósito (`monetization` o `entertainment`) y las reglas fijadas en su ficha.

2. **Modo Libre / Video de Prueba:**
   - El usuario pide: *"Haz un video de prueba sobre volcanes sin publicar"*.
   - El sistema ejecuta todo el pipeline técnico en carpeta local sin exigir registro de canal ni publicar en redes.

3. **Modo Sugerencia a Pedido:**
   - El usuario pide: *"Sugiéreme nichos para monetizar"* o *"Sugiéreme nichos de entretenimiento"*.
   - Se despacha a `trend-researcher` para analizar el mercado y devolver las 3 mejores propuestas sin tocar `channels.json` hasta que el usuario elija una.
