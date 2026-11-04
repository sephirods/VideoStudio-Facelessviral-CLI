# Hoja de Ruta del Sistema y Arquitectura de Grupos de Canales

Este documento registra de forma permanente los 3 desarrollos pendientes y el sistema de gestión multicanal (**Grupos de Canales**) para que cualquier sesión de Antigravity reconozca y opere la factoría automáticamente.

---

## PARTE 1: Los 3 Desarrollos Técnicos Pendientes (1 a 1)

### 📌 Pilar 1: Extractor de Tendencias con Datos Duros (`trend-researcher`)
- **Objetivo:** Conectar fuentes de datos objetivos para que la selección de temas se base en volumen de búsqueda y aceleración algorítmica real, no en intuición.
- **Herramienta a implementar:** `scripts/fetch_trends_data.py`.
- **Fuentes integradas:**
  1. **Google Trends RSS Feed:** Extracción en tiempo real de términos *Breakout* (>500% de crecimiento en las últimas 24h) por región (US, ES, MX, Global).
  2. **Reddit Hot API (JSON público):** Monitoreo de comunidades virales (`r/business`, `r/todayilearned`, `r/technology`) filtrando por posts de alta interacción.
- **Entregable del subagente:** `trend_brief.json` respaldado con métricas de búsqueda reales.

---

### 📌 Pilar 2: Inteligencia Viral de Mercado para Títulos, Tags y Engagement (`viral-packager`) ✅ [IMPLEMENTADO]
- **Objetivo:** Empaquetar el video basándose en datos reales de la competencia y búsquedas en vivo (cero plantillas rígidas).
- **Herramienta implementada:** `scripts/fetch_viral_intelligence.py`.
- **Componentes:**
  1. **Espionaje de Shorts Virales:** Consulta en vivo con `yt-dlp` los videos más vistos sobre el tema y extrae sus títulos y conteos de vistas reales.
  2. **Búsquedas Predictivas en Vivo (YouTube Autocomplete):** Extrae directamente del buscador de YouTube lo que la gente está tipeando en tiempo real.
  3. **Síntesis Creativa de la IA:** El subagente `viral-packager` analiza los gatillos ganadores y compone de forma autónoma:
     - Título único (<70 caracteres con `#Shorts`).
     - Tags de Doble Capa (Capa de Nicho derivada de búsquedas en vivo + Capa Universal de tracción).
     - Comentario fijado para provocar debate en los primeros 30 minutos.
     - Miniatura móvil con badge de 74px y gancho amarillo eléctrico.

---

### 📌 Pilar 3: Motor de Subida Automática Multi-Plataforma (`social-media-publisher`) ✅ [IMPLEMENTADO]
- **Objetivo:** Distribuir o programar los videos empaquetados directamente en las plataformas sin intervención humana.
- **Herramienta implementada:** `scripts/publish_video.py` con soporte para `social-auto-upload` (`sau`), YouTube Data API y sesiones locales.
- **Funcionalidad:**
  - Carga desatendida en **YouTube Shorts, TikTok, Instagram Reels, Facebook Reels, LinkedIn y X**.
  - Inyección 100% automática de todos los activos creados por la IA: título (<70 chars), descripción formateada, tags de doble capa, miniatura móvil y comentario fijado de debate.
  - Generación de `publication_receipt.json` con registro y enlaces de cada plataforma.

---

## PARTE 2: Arquitectura de "Grupos de Canales" (Multi-Canal)

### 1. ¿Qué es un Grupo de Canales?
Un **Grupo de Canales** es una marca / perfil único con una **temática específica**, que tiene presencia en una o varias redes sociales:
- *Ejemplo Grupo A:* Nombre: **"Imperio de Dinero"** | Temática: **Economía y Negocios** | Plataformas: TikTok, YouTube Shorts, Instagram Reels.
- *Ejemplo Grupo B:* Nombre: **"Enigmas del Cosmos"** | Temática: **Espacio y Misterios** | Plataformas: YouTube Shorts, TikTok.
- *Ejemplo Grupo C:* Nombre: **"Mente Maestra"** | Temática: **Psicología y Lenguaje Corporal** | Plataformas: TikTok, Instagram.

---

### 2. Flujo de Configuración y Detección Automática (Onboarding)
Cuando el Orquestador inicia una sesión (o se despierta por `/schedule`):
1. **Verificación de Configuración:** Lee el archivo maestro [`config\channels.json`](config/channels.json).
2. **Si NO hay canales configurados:**
   - El Orquestador detecta que es una configuración nueva y avisa al usuario.
   - Si el usuario **no sabe qué canal abrir**, el subagente `trend-researcher` analiza las tendencias de mayor RPM y menor competencia y le sugiere 2-3 opciones ganadoras de grupos de canales.
   - El usuario elige y el Orquestador guarda la configuración en `config/channels.json`.
3. **Si YA hay canales configurados:**
   - Cuando el disparador `/schedule` o el usuario dice:  
     *"produce video para el canal 'Imperio de Dinero'"* (o si solo hay un canal por defecto):
     - El Orquestador carga automáticamente su temática, su estilo de guion, sus parámetros visuales y las credenciales de las plataformas a las que debe subir el video.
     - El empaquetado final se guarda en `videos/publicaciones/[CANAL]/[FECHA]_[slug]/`.

---

### 3. Esquema Maestro: `config/channels.json`
```json
{
  "active_default_channel": "imperio_dinero",
  "channels": {
    "imperio_dinero": {
      "channel_id": "imperio_dinero",
      "display_name": "Imperio de Dinero",
      "niche": "negocios_y_finanzas",
      "description": "Historias de negocios, dinero, poder y secretos corporativos.",
      "content_pillars": [
        "Business Storytelling",
        "Secretos de Grandes Marcas",
        "Psicología Financiera y Retos de Ahorro"
      ],
      "voice_preference": "es-MX-JorgeNeural",
      "connected_platforms": {
        "youtube": {
          "enabled": true,
          "channel_name": "@ImperioDeDineroShorts",
          "auth_type": "oauth2_or_cookies"
        },
        "tiktok": {
          "enabled": true,
          "username": "@imperiodedinero",
          "auth_type": "sau_cookies"
        },
        "instagram": {
          "enabled": true,
          "username": "@imperiodedinero.reels",
          "auth_type": "sau_cookies"
        }
      }
    }
  }
}
```
