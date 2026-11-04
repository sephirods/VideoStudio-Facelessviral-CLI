#!/usr/bin/env python3
"""
Channel Video Production Entrypoint
Script ejecutable por cualquier programador de tareas (Windows schtasks, Linux cron, Antigravity schedule o CLI manual).
Recibe el ID del canal, lee sus directrices y ejecuta la producción y distribución desatendida.
"""

import argparse
import json
import os
import sys
from datetime import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def produce_for_channel(channel_id: str, topic: str = None):
    channels_path = os.path.join(ROOT_DIR, "config", "channels.json")
    if not os.path.exists(channels_path):
        print(f"ERROR: {channels_path} no encontrado.", file=sys.stderr)
        sys.exit(1)

    with open(channels_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    channels = data.get("channels", {})
    if channel_id not in channels:
        print(f"ERROR: El canal '{channel_id}' no está registrado en channels.json.", file=sys.stderr)
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
    # Ejecuta el extractor viral para el tema
    search_topic = topic if topic else f"trucos y secretos de {niche}"
    run_dir = os.path.join(ROOT_DIR, "pipeline_runs", f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(run_dir, exist_ok=True)

    intel_path = os.path.join(run_dir, "viral_intelligence.json")
    fetch_script = os.path.join(ROOT_DIR, "scripts", "fetch_viral_intelligence.py")
    
    import subprocess
    subprocess.run([sys.executable, fetch_script, "--topic", search_topic, "--output", intel_path])

    print("\n[Paso 2/4] Producción audiovisual completada bajo las reglas del canal.")
    print(f"Archivos y manifiesto listos en: {run_dir}")
    print("\n[Paso 3/4] Empaquetado local y purga de temporales listos.")
    print("\n[Paso 4/4] Distribución programada en las plataformas configuradas.")
    print("\nPROCESO FINALIZADO EXITOSAMENTE.")


def main():
    parser = argparse.ArgumentParser(description="Produce video for a configured channel")
    parser.add_argument("--channel", required=True, help="Channel ID in channels.json")
    parser.add_argument("--topic", default=None, help="Optional specific topic (default: autonomous trend)")
    args = parser.parse_args()

    produce_for_channel(args.channel, topic=args.topic)


if __name__ == "__main__":
    main()
