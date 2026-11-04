# Paso 0: Diagnóstico de Entorno, Onboarding y Configuración Flexible

Este documento define el protocolo del **Paso 0** que el CLI y el Orquestador ejecutan antes o durante la producción de videos. Diseñado para ser un motor maestro portátil, listo para clonarse desde GitHub y operar en cualquier equipo y en cualquier sistema operativo.

---

## 🗺️ Mapa de Control Rápido del Repositorio (Acceso Inmediato)

Cualquier agente u orquestador que clone este repositorio encuentra todo en estas rutas exactas:

| Elemento / Tarea | Archivo / Carpeta Exacta | Qué se hace aquí |
|---|---|---|
| **Registro de Canales** | [`config/channels.json`](config/channels.json) | Añadir, editar o cambiar el canal activo, idioma, voz y nichos. |
| **Plantilla de Canales** | [`config/channels.example.json`](config/channels.example.json) | Estructura de referencia sin datos personales. |
| **Configuración de Hardware** | [`config/hardware.json`](config/hardware.json) | GPU detectada (NVENC, AMF, VideoToolbox) o CPU multihilo. |
| **Protocolo de Onboarding** | [`SETUP_ONBOARDING.md`](SETUP_ONBOARDING.md) | Flujo paso a paso de la entrevista "Grill-Me", idioma y voces. |
| **Contrato del Orquestador** | [`AGENTS.md`](AGENTS.md) | Reglas de despacho, gatekeeping estricto y paralelismo. |
| **Reglas de Subagentes** | `.agents/agents/<nombre>/agent.md` | Prompts y herramientas de cada especialista. |
| **Entregables Finales** | `videos/publicaciones/[CANAL]/[FECHA]_[slug]/` | Paquetes listos para subir a redes o consumo. |

---

## 1. Fase de Diagnóstico Automático (CLI Doctor)

Antes de operar, el sistema audita el entorno para optimizar el rendimiento sin configuraciones manuales:

1. **Detección de Hardware de Video (`detect_hardware.py`):**
   - **NVIDIA GPU:** Detecta CUDA/NVENC (`h264_nvenc`). Configura concurrencia x4 por hardware.
   - **AMD GPU:** Detecta AMF (`h264_amf`).
   - **Apple Silicon:** Detecta VideoToolbox (`h264_videotoolbox`).
   - **CPU Fallback:** Selecciona codificación multihilo CPU (`libx264`, preset `fast`).
   - *Persistencia:* Guarda el resultado en [`config/hardware.json`](config/hardware.json).

2. **Verificación de Dependencias Esenciales:**
   - Python 3.10+ (entorno virtual activo).
   - FFmpeg con soporte de códecs de audio/video.
   - Motor de video MoneyPrinterTurbo (local o externo).
   - Edge-TTS y Whisper.

3. **Credenciales de Stock (Pixabay y Pexels - Arquitectura Multi-Proveedor):**
   - El sistema audita [`config/stock_credentials.json`](config/stock_credentials.json) y el motor.
   - **Pixabay (100% Activa e Instantánea):** Ve a [pixabay.com/api/docs](https://pixabay.com/api/docs/), inicia sesión y copia tu clave en la sección *Parameters* (`key (str): Your API key`).
   - **Pexels (4K Vertical Cinematográfico):** Si ya tienes clave previa o cuando Pexels reabra nuevas solicitudes, regístrala para aprovechar su calidad 4K.
   - **Modo Híbrido:** Permite configurar ambas; el sistema intenta Pexels primero y si se satura o falta material, respalda con Pixabay automáticamente.
   - *Gestor dedicado:* `python scripts/configure_stock_api.py`.
   - *Seguridad:* Las claves se almacenan localmente y **nunca se suben a Git** (protegidas en `.gitignore`). Plantilla en [`config/stock_credentials.example.json`](config/stock_credentials.example.json).

---

## 2. Entrevista de Configuración Inicial ("Grill-Me" de Canales)

Cuando el Orquestador detecta que [`config/channels.json`](config/channels.json) está vacío, o cuando el usuario escribe `configurar canal`, se ejecuta el siguiente flujo interactivo:

### Paso 1: Selección de Modo Inicial
- **A) Configurar mi primer Grupo de Canales ahora.**
- **B) Sugerir temáticas primero:** El Analizador de Tendencias explora el mercado y presenta sugerencias sin guardar nada aún.
- **C) Modo Prueba / Demo:** Generar un video piloto de prueba local sin registrar canales ni publicar.
- **D) Saltar por ahora:** Continuar en modo libre y configurar los canales más tarde a pedido.

---

### Paso 2 (Si elige Configurar Canal): Idioma y Mercado Objetivo
El idioma condiciona el mercado, el volumen y el RPM de monetización publicitaria:
- **🇪🇸 Español (Latinoamérica y España):**
  - Tráfico masivo, alta velocidad de interacción y comentarios.
  - Guión de 140 a 165 palabras (~2.4 palabras/segundo).
- **🇺🇸 Inglés (Tier 1: Estados Unidos, Reino Unido, Canadá, Australia):**
  - RPM publicitario **3x a 5x superior** en YouTube Shorts y TikTok Creator Rewards.
  - Guión de 155 a 180 palabras (~2.6 palabras/segundo).

---

### Paso 3: Propósito del Canal y Regla Universal de Duración
- **Monetización / Ganancias (Alto RPM):**
  - Filtros de alta retención, curiosidad y nichos comerciales (finanzas, tecnología, negocios, psicología persuasiva, misterio).
- **Entretenimiento / Viralidad Pura:**
  - Consumo masivo: curiosidades asombrosas, mitos desmentidos, dilemas morales, cultura pop, gaming.
- **⚠️ REGLA UNIVERSAL DE DURACIÓN (Innegociable):**
  Sin importar si el canal es de Monetización o de Entretenimiento, la duración del video final **SIEMPRE debe estar en el rango de monetización: 62 a 72 segundos totales** (>60.0s netos para calificar en los fondos de pago de creadores de TikTok y YouTube Shorts).

---

### Paso 4: Identidad y Temática del Canal
- **Nombre de Marca / Grupo de Canales:** (Ej: *Mente Oculta*, *CuriosaMente*, *Hidden Empire*, *Finanzas Pro*).
- **Nicho Principal:**
  - Si el usuario lo define: se toma directamente.
  - Si no sabe qué nicho elegir: se despacha a `trend-researcher` para sugerir 2-3 opciones ganadoras basadas en datos de búsqueda reales.

---

### Paso 5: Identidad Sonora Unificada (Voz Oficial del Canal)
Para construir reconocimiento y autoridad de marca, cada grupo de canales debe mantener una voz neural humana y consistente en todos sus videos:

| Idioma | Género | Código Oficial | Perfil Sonoro | Nichos Recomendados |
|---|---|---|---|---|
| 🇪🇸 **Español** | **Masculina** | `es-MX-JorgeNeural` | Profunda, intrigante, autoritaria. | Finanzas, Leyes del Dinero, Crímenes, Misterios. |
| 🇪🇸 **Español** | **Masculina** | `es-ES-AlvaroNeural` | Sobria, directa, documental periodístico. | Geopolítica, Noticias, Estrategia, Filosofía. |
| 🇪🇸 **Español** | **Femenina** | `es-MX-DaliaNeural` | Envolvente, cálida, alta retención. | Psicología, Curiosidades, Salud y Hábitos. |
| 🇪🇸 **Español** | **Femenina** | `es-ES-ElviraNeural` | Dinámica, segura, profesional. | Emprendimiento, Tendencias, Productividad. |
| 🇺🇸 **Inglés** | **Masculina** | `en-US-ChristopherNeural` | Cine, storytelling, voz grave de autoridad. | Money, Dark Psychology, Wealth, True Crime. |
| 🇬🇧 **Inglés** | **Masculina** | `en-GB-RyanNeural` | Acento británico prestigioso, documental BBC. | Luxury, History, Geopolitics, Elite Secrets. |
| 🇺🇸 **Inglés** | **Femenina** | `en-US-JennyNeural` | Clara, enérgica, profesional, altísimo CTR. | Tech, AI Trends, Life Hacks, Psychology. |
| 🇺🇸 **Inglés** | **Femenina** | `en-US-AriaNeural` | Cálida, narrativa profunda, emotiva. | Human Stories, Mindset, Health, Mystery. |

*El Orquestador recomienda la voz ideal según el Idioma + Nicho. La voz elegida se almacena en `channels.json` como `voice_preference` y `viral-scriptwriter` la fija obligatoriamente en cada producción.*

---

### Paso 6: Plataformas de Publicación (Multi-Red)
¿En qué plataformas se distribuirá este canal automáticamente?
- `youtube_shorts`: YouTube Shorts (Monetización oficial y búsqueda).
- `tiktok`: TikTok (Creator Rewards Program >60s).
- `instagram_reels`: Instagram Reels (Engagement y marca personal).
- `facebook_reels`: Facebook Reels (Audiencia adulta de alto RPM comercial).
- `linkedin`: LinkedIn Video (Tráfico profesional B2B).
- `x_twitter`: X / Twitter (Video nativo en timeline).

---

### Paso 7: Vinculación Interactiva de Cuentas (Zero-Tech y Aislamiento por Canal)

Para conectar plataformas (YouTube Shorts, TikTok, Instagram) sin exigir al usuario claves de Google Cloud ni pasos complejos:

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
  ```powershell
  schtasks /create /tn "AntigravityConnectChannel" /tr "'%CD%\scripts\run_connect.bat' [canal] [plataforma]" /sc once /st 23:59 /it /f; schtasks /run /tn "AntigravityConnectChannel"
  ```
- **En Linux / macOS:**
  ```bash
  python3 scripts/connect_account.py --channel [canal] --platform [plataforma]
  ```

#### 3. Monitor Inteligente y Cierre Automático (`scripts/connect_account.py`):
- Abre Google Chrome con banderas anti-bloqueo (`--disable-blink-features=AutomationControlled`).
- Detecta cookies de acceso (`LOGIN_INFO`, `SSID`, `SID` o `sessionid`).
- Guarda la sesión aislada en:
  ```
  config/sessions/[channel_id]/[plataforma]_session.json
  ```
- Cierra la ventana automáticamente y limpia la tarea temporal.

#### 4. Aislamiento Estricto para Múltiples Canales:
- Cada canal tiene su propia carpeta aislada:
  - Canal 1: `config/sessions/canal_finanzas/youtube_session.json`
  - Canal 2: `config/sessions/canal_misterios/youtube_session.json`
- El publicador lee **únicamente** la carpeta del canal activo. Imposible mezclar publicaciones entre marcas.

---

### Paso 8: Servicios Visuales y Outro
- **¿Dispones de cuenta en Canva conectada?**
  - **Sí:** Utiliza el MCP de Canva para intros/outros dinámicas y plantillas.
  - **No:** Activa la **Plantilla Local** (FFmpeg/Pillow genera el outro automáticamente en disco sin servicios externos).

---

### Paso 9: Gestión de Almacenamiento y Material Visual de Stock
- **A) Crear Biblioteca Local de Calidad (Recomendado):** Guardamos los mejores clips en `assets/b-roll/<categoria>/` para reutilizarlos en futuros videos.
- **B) Modo Ahorro de Espacio en Disco:** Borramos los clips temporales de stock inmediatamente después de aprobar el video final.

---

### Paso 10: Cadencia de Operación y Disparador Universal
- **A Pedido (Bajo Demanda):** El sistema solo produce cuando tú lo ordenes en chat o terminal.
- **Piloto Automático (Programado):** 
  - Define hora y frecuencia (ej. 13:00 y 19:00).
  - En Antigravity: cron nativo con `/schedule`.
  - En Windows: Tarea Programada con `schtasks.exe`.
  - En Linux/macOS: `crontab`.
  - O daemon continuo: `python scripts/universal_scheduler.py --channel <id> --daemon`.

---

## 3. Protocolo de Verificación en Turno 1 (Antes de Producir)

Antes de iniciar la producción para un canal con cuentas vinculadas, el Orquestador ejecuta una comprobación preventiva de 1 segundo:
1. Comprueba si existen los archivos en `config/sessions/[canal]/`.
2. Si una sesión venció o no existe, avisa al usuario de inmediato en el Turno 1 para renovarla o cambiar a modo local.

---

## 4. Estructura de Ficha de Canal en `config/channels.json`

```json
{
  "active_default_channel": "canal_1",
  "channels": {
    "canal_1": {
      "name": "Mente Oculta",
      "language": "es",
      "niche": "Psicología y Curiosidades",
      "purpose": "monetization",
      "target_duration_seconds": [62, 72],
      "voice_preference": "es-MX-JorgeNeural",
      "platforms": ["youtube_shorts", "tiktok"],
      "visual_assets": {
        "outro_mode": "local",
        "canva_user": null
      }
    }
  }
}
```
