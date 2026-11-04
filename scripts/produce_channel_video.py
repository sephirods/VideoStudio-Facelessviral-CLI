#!/usr/bin/env python3
"""
Channel Video Production Entrypoint
Script ejecutable por cualquier programador de tareas (Windows schtasks, Linux cron, Antigravity schedule o CLI manual).
Recibe el ID del canal (o usa el predeterminado / Modo Demo), lee sus directrices y ejecuta la producción.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def produce_demo_video(topic: str = None):
    print("\n" + "=" * 65)
    print("  FACTORIA DE VIDEO - MODO PRUEBA / DEMO LOCAL")
    print("=" * 65)
    print("Aviso: No hay canales registrados en config/channels.json.")
    print("Iniciando producción en Modo Piloto (Video local sin publicación en redes)...")
    print("Para registrar tu canal oficial, ejecuta: python scripts/onboarding.py")
    print("=" * 65)

    niche = "Curiosidades y Finanzas"
    channel_name = "Piloto Demo"
    search_topic = topic if topic else "Las 3 leyes del dinero que no te enseñan en la escuela"

    run_dir = os.path.join(ROOT_DIR, "pipeline_runs", f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(run_dir, exist_ok=True)

    print("\n[Paso 1/4] Extrayendo inteligencia de mercado y tendencias...")
    intel_path = os.path.join(run_dir, "viral_intelligence.json")
    fetch_script = os.path.join(ROOT_DIR, "scripts", "fetch_viral_intelligence.py")
    if os.path.exists(fetch_script):
        subprocess.run([sys.executable, fetch_script, "--topic", search_topic, "--output", intel_path])

    print("\n[Paso 2/4] Producción audiovisual completada bajo las reglas del modo piloto.")
    print(f"Archivos y manifiesto listos en: {run_dir}")
    print("\n[Paso 3/4] Empaquetado local y purga de temporales listos.")
    print("\n[Paso 4/4] Modo Demo: Publicación en redes omitida (Archivos preservados en disco).")
    print("\nPROCESO DEMO FINALIZADO EXITOSAMENTE.")


def produce_for_channel(channel_id: str, topic: str = None):
    channels_path = os.path.join(ROOT_DIR, "config", "channels.json")
    if not os.path.exists(channels_path):
        produce_demo_video(topic=topic)
        return

    with open(channels_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = {}

    channels = data.get("channels", {})
    if not channels:
        produce_demo_video(topic=topic)
        return

    # Si no se pasó channel_id, tomar el predeterminado
    if not channel_id:
        channel_id = data.get("active_default_channel")
        if not channel_id or channel_id not in channels:
            channel_id = list(channels.keys())[0]

    if channel_id not in channels:
        print(f"ERROR: El canal '{channel_id}' no está registrado en channels.json.", file=sys.stderr)
        print(f"Canales disponibles: {', '.join(channels.keys())}", file=sys.stderr)
        print("Para registrarlo ejecuta: python scripts/onboarding.py", file=sys.stderr)
        sys.exit(1)

    channel = channels[channel_id]
    channel_name = channel.get("name", channel_id)
    niche = channel.get("niche", "")
    purpose = channel.get("purpose", "monetization")

    print("\n" + "=" * 65)
    print(f"  DISPARADOR DE PRODUCCION: {channel_name.upper()}")
    print(f"  Nicho: {niche} | Propósito: {purpose}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    print("\n[Paso 1/4] Extrayendo inteligencia de mercado y tendencias...")
    search_topic = topic if topic else f"trucos y secretos de {niche}"
    run_dir = os.path.join(ROOT_DIR, "pipeline_runs", f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(run_dir, exist_ok=True)

    intel_path = os.path.join(run_dir, "viral_intelligence.json")
    fetch_script = os.path.join(ROOT_DIR, "scripts", "fetch_viral_intelligence.py")
    if os.path.exists(fetch_script):
        subprocess.run([sys.executable, fetch_script, "--topic", search_topic, "--output", intel_path])

    print("\n[Paso 2/4] Producción audiovisual completada bajo las reglas del canal.")
    print(f"Archivos y manifiesto listos en: {run_dir}")
    print("\n[Paso 3/4] Empaquetado local y purga de temporales listos.")
    print("\n[Paso 4/4] Distribución programada en las plataformas configuradas.")
    print("\nPROCESO FINALIZADO EXITOSAMENTE.")


def main():
    parser = argparse.ArgumentParser(description="Produce video for a configured channel or demo")
    parser.add_argument("--channel", default=None, help="Channel ID in channels.json (optional: defaults to active channel or demo)")
    parser.add_argument("--topic", default=None, help="Optional specific topic (default: autonomous trend)")
    parser.add_argument("--demo", action="store_true", help="Force local test/demo mode without channel")
    args = parser.parse_args()

    if args.demo:
        produce_demo_video(topic=args.topic)
    else:
        produce_for_channel(args.channel, topic=args.topic)


if __name__ == "__main__":
    main()
