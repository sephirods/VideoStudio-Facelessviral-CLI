#!/usr/bin/env python3
"""
Interactive Onboarding & Grill-Me CLI
Permite configurar canales de forma interactiva desde la terminal o ser invocado por cualquier agente de IA.
Incorpora selección de Idioma (Español vs Inglés Tier 1) e Identidad Sonora (Voz Oficial unificada).
"""

import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHANNELS_PATH = os.path.join(ROOT_DIR, "config", "channels.json")

VOICE_CATALOG = {
    "es": {
        "masculina_recomendada": ("es-MX-JorgeNeural", "Profunda, misterio, autoridad y negocios"),
        "masculina_alternativa": ("es-ES-AlvaroNeural", "Directa, sobria, documental periodístico"),
        "femenina_recomendada": ("es-MX-DaliaNeural", "Envolvente, cálida, psicología y curiosidades"),
        "femenina_alternativa": ("es-ES-ElviraNeural", "Dinámica, profesional, tendencias y vida práctica")
    },
    "en": {
        "masculina_recomendada": ("en-US-ChristopherNeural", "Autoritaria, cine, storytelling de alto impacto"),
        "masculina_alternativa": ("en-GB-RyanNeural", "Acento británico prestigioso, documental BBC"),
        "femenina_recomendada": ("en-US-JennyNeural", "Clara, enérgica, profesional, alta retención"),
        "femenina_alternativa": ("en-US-AriaNeural", "Cálida, narrativa profunda, emotiva")
    }
}


def print_banner():
    print("\n" + "=" * 65)
    print("  FACTORIA DE VIDEO - ONBOARDING Y GRILL-ME DE CANALES")
    print("=" * 65)


def load_channels():
    if os.path.exists(CHANNELS_PATH):
        try:
            with open(CHANNELS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"active_default_channel": None, "channels": {}}


def save_channels(data):
    os.makedirs(os.path.dirname(CHANNELS_PATH), exist_ok=True)
    with open(CHANNELS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def interactive_onboarding():
    print_banner()
    data = load_channels()
    channels = data.get("channels", {})

    print("\n¿Qué deseas hacer hoy?")
    print("1) Configurar un nuevo Grupo de Canales")
    print("2) Modo Prueba / Demo (Video piloto local sin redes)")
    print("3) Listar canales registrados")
    print("4) Configurar APIs de Stock (Pixabay y Pexels)")
    print("5) Salir")

    try:
        choice = input("\nElige una opción (1-5) [1]: ").strip() or "1"
    except (KeyboardInterrupt, EOFError):
        print("\nOperación cancelada.")
        return

    if choice == "2":
        print("\nEjecutando Modo Demo...")
        import subprocess
        subprocess.run([sys.executable, os.path.join(ROOT_DIR, "scripts", "produce_channel_video.py")])
        return

    elif choice == "3":
        if not channels:
            print("\nNo hay canales registrados todavía en config/channels.json.")
        else:
            print(f"\nCanales registrados ({len(channels)}):")
            for cid, c in channels.items():
                print(f" - [{cid}] {c.get('name')} | Idioma: {c.get('language', 'es').upper()} | Voz: {c.get('voice_preference')} | Nicho: {c.get('niche')}")
            print(f"\nCanal activo predeterminado: {data.get('active_default_channel')}")
        return

    elif choice == "4":
        sys.path.insert(0, os.path.join(ROOT_DIR, "scripts"))
        import configure_stock_api
        configure_stock_api.configure_interactive()
        return

    elif choice == "5":
        print("\nHasta luego.")
        return

    # Opción 1: Configurar canal
    print("\n--- PASO 1: Idioma y Mercado Objetivo ---")
    print("1) Español (Latinoamérica y España - Tráfico masivo y alta interacción)")
    print("2) Inglés (Tier 1: US, UK, CA, AU - RPM publicitario x3 a x5 superior)")
    lang_choice = input("Selecciona idioma (1 o 2) [1]: ").strip() or "1"
    language = "en" if lang_choice == "2" else "es"

    print("\n--- PASO 2: Identidad y Nicho del Canal ---")
    try:
        name = input("Nombre de la Marca / Canal (ej: Mente Oculta / Hidden Empire): ").strip()
        if not name:
            name = "Mi Canal Viral"

        cid = name.lower().replace(" ", "_")
        for char in "áéíóúñ/\\:*?\"<>|":
            cid = cid.replace(char, "")

        niche = input("Nicho / Temática (ej: Psicología Oscura, Secretos de Dinero, Curiosidades): ").strip()
        if not niche:
            niche = "Curiosidades y Finanzas"

        print("\n--- PASO 3: Propósito del Canal ---")
        print("1) Monetización / Ganancias (Alto RPM, curiosidad y negocios)")
        print("2) Entretenimiento / Viralidad Pura (Humor, cultura pop, datos asombrosos)")
        p_choice = input("Propósito (1 o 2) [1]: ").strip() or "1"
        purpose = "monetization" if p_choice == "1" else "entertainment"

        print("\n--- PASO 4: Identidad Sonora Unificada (Voz Oficial del Canal) ---")
        cat = VOICE_CATALOG[language]
        print("¿Qué perfil de voz prefieres para mantener consistente en este canal?")
        print(f"1) Masculina Recomendada: {cat['masculina_recomendada'][0]} ({cat['masculina_recomendada'][1]})")
        print(f"2) Femenina Recomendada: {cat['femenina_recomendada'][0]} ({cat['femenina_recomendada'][1]})")
        print(f"3) Masculina Alternativa: {cat['masculina_alternativa'][0]} ({cat['masculina_alternativa'][1]})")
        print(f"4) Femenina Alternativa: {cat['femenina_alternativa'][0]} ({cat['femenina_alternativa'][1]})")
        v_choice = input("Elige la voz (1-4) [1]: ").strip() or "1"

        if v_choice == "2":
            voice = cat["femenina_recomendada"][0]
        elif v_choice == "3":
            voice = cat["masculina_alternativa"][0]
        elif v_choice == "4":
            voice = cat["femenina_alternativa"][0]
        else:
            voice = cat["masculina_recomendada"][0]

        print(f"Voz seleccionada: {voice}")

        print("\n--- PASO 5: Plataformas de Publicación ---")
        print("Selecciona las plataformas donde publicarás (separadas por coma):")
        print("1) YouTube Shorts  2) TikTok  3) Instagram Reels")
        plats_in = input("Plataformas [1,2,3]: ").strip() or "1,2,3"
        platforms = []
        if "1" in plats_in:
            platforms.append("youtube_shorts")
        if "2" in plats_in:
            platforms.append("tiktok")
        if "3" in plats_in:
            platforms.append("instagram_reels")
        if not platforms:
            platforms = ["youtube_shorts", "tiktok"]

        # Registrar canal (REGLA UNIVERSAL: duración siempre en rango de monetización [62, 72])
        new_channel = {
            "name": name,
            "language": language,
            "niche": niche,
            "purpose": purpose,
            "target_duration_seconds": [62, 72],
            "voice_preference": voice,
            "platforms": platforms,
            "visual_assets": {
                "outro_mode": "local",
                "canva_user": None
            },
            "style_notes": "Cortes dinámicos cada 2.5s, subtítulos contrastados al 58% con cápsula negra.",
            "schedule": {
                "mode": "on_demand",
                "time": "19:00",
                "cadence": "DAILY",
                "engine": "windows_task_scheduler"
            }
        }

        channels[cid] = new_channel
        data["channels"] = channels
        if not data.get("active_default_channel"):
            data["active_default_channel"] = cid

        save_channels(data)

        print("\n" + "=" * 65)
        print(f"  ¡CANAL REGISTRADO CON EXITO: {name} ({cid})!")
        print("=" * 65)
        print(f"Ficha guardada en: {CHANNELS_PATH}")
        print(f"Idioma: {language.upper()} | Voz Oficial: {voice}")
        print(f"Duración: 62-72 segundos (Rango Universal de Monetización)")
        print(f"Canal activo fijado: {cid}")
        print("\nPara conectar sus redes sociales ejecuta:")
        print(f"  python scripts/connect_account.py --channel {cid} --platform youtube")
        print("\nPara producir tu primer video ejecuta:")
        print(f"  python scripts/produce_channel_video.py --channel {cid}")

    except (KeyboardInterrupt, EOFError):
        print("\nCancelado.")


if __name__ == "__main__":
    interactive_onboarding()
