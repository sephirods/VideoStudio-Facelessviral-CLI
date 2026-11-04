#!/usr/bin/env python3
"""
Interactive Onboarding & Grill-Me CLI
Permite configurar canales de forma interactiva desde la terminal o ser invocado por cualquier agente de IA.
"""

import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHANNELS_PATH = os.path.join(ROOT_DIR, "config", "channels.json")


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
    return {"active_default_channel": null, "channels": {}}


def save_channels(data):
    os.makedirs(os.path.dirname(CHANNELS_PATH), exist_ok=True)
    with open(CHANNELS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def interactive_onboarding():
    print_banner()
    data = load_channels()
    channels = data.get("channels", {})

    print("\n¿Qué deseas hacer hoy?")
    print("1) Configurar un nuevo Canal")
    print("2) Modo Prueba / Demo (Video piloto local sin redes)")
    print("3) Listar canales registrados")
    print("4) Salir")

    try:
        choice = input("\nElige una opción (1-4) [1]: ").strip() or "1"
    except (KeyboardInterrupt, EOFError):
        print("\nOperación cancelada.")
        return

    if choice == "2":
        print("\nEjecutando Modo Demo...")
        import subprocess
        subprocess.run([sys.executable, os.path.join(ROOT_DIR, "scripts", "produce_channel_video.py"), "--demo"])
        return

    elif choice == "3":
        if not channels:
            print("\nNo hay canales registrados todavía.")
        else:
            print(f"\nCanales registrados ({len(channels)}):")
            for cid, c in channels.items():
                print(f" - [{cid}] {c.get('name')} | Nicho: {c.get('niche')} | Propósito: {c.get('purpose')}")
            print(f"\nCanal activo predeterminado: {data.get('active_default_channel')}")
        return

    elif choice == "4":
        print("\nHasta luego.")
        return

    # Opción 1: Configurar canal
    print("\n--- PASO 1: Identidad del Canal ---")
    try:
        name = input("Nombre del Canal (ej: Finanzas Ocultas): ").strip()
        if not name:
            name = "Mi Canal Viral"

        cid = name.lower().replace(" ", "_")
        for char in "áéíóúñ/\\:*?\"<>|":
            cid = cid.replace(char, "")

        niche = input("Nicho / Temática (ej: Secretos de Dinero y Hábitos): ").strip()
        if not niche:
            niche = "Curiosidades y Dinero"

        print("\n--- PASO 2: Propósito del Canal ---")
        print("1) Monetización (RPM alto, retención, guiones >60s)")
        print("2) Entretenimiento / Viralidad masiva")
        p_choice = input("Propósito (1 o 2) [1]: ").strip() or "1"
        purpose = "monetization" if p_choice == "1" else "entertainment"

        print("\n--- PASO 3: Redes Sociales ---")
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

        # Registrar canal
        new_channel = {
            "name": name,
            "niche": niche,
            "purpose": purpose,
            "target_duration_seconds": [62, 72] if purpose == "monetization" else [30, 60],
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
        print(f"Canal activo fijado: {cid}")
        print("\nPara conectar sus redes sociales ejecuta:")
        print(f"  python scripts/connect_account.py --channel {cid} --platform youtube")
        print("\nPara producir tu primer video ejecuta:")
        print(f"  python scripts/produce_channel_video.py --channel {cid}")

    except (KeyboardInterrupt, EOFError):
        print("\nCancelado.")


if __name__ == "__main__":
    interactive_onboarding()
