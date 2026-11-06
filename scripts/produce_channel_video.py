#!/usr/bin/env python3
"""
Channel Video Production Preflight & Bootstrapper
Prepara y valida de forma honesta y paralela los insumos de una corrida antes del despacho de los 9 subagentes:
1. Verifica el cooldown de 30 días de temas y miniaturas por grupo de canales (content_deduplication.py).
2. Audita preventivamente las sesiones de redes configuradas en config/sessions/[canal]/.
3. Ejecuta en paralelo la extracción de tendencias en vivo (fetch_trends_data.py) y la inteligencia
   de competencia de YouTube (fetch_viral_intelligence.py).
4. Emite preflight_manifest.json listo para el Orquestador (sin mensajes falsos de video renderizado).
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
import subprocess
import sys
import time

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from content_deduplication import check_topic_cooldown
except Exception:
    check_topic_cooldown = None


PLATFORM_SESSION_MAP = {
    "youtube_shorts": "youtube_session.json",
    "youtube": "youtube_session.json",
    "tiktok": "tiktok_session.json",
    "instagram_reels": "instagram_session.json",
    "instagram": "instagram_session.json",
}


def audit_channel_sessions(channel_id: str, platforms: list[str]) -> dict:
    sess_dir = os.path.join(ROOT_DIR, "config", "sessions", channel_id)
    missing = []
    present = []
    for p in platforms:
        fname = PLATFORM_SESSION_MAP.get(p, f"{p}_session.json")
        fpath = os.path.join(sess_dir, fname)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 20:
            present.append(p)
        else:
            missing.append(p)
    return {
        "session_dir": sess_dir,
        "ready_platforms": present,
        "missing_platforms": missing,
        "all_sessions_ready": len(missing) == 0
    }


def _run_preflight_jobs(run_dir: str, search_topic: str, language: str) -> dict:
    intel_path = os.path.join(run_dir, "viral_intelligence.json")
    trends_path = os.path.join(run_dir, "market_trends.json")

    fetch_intel = os.path.join(SCRIPTS_DIR, "fetch_viral_intelligence.py")
    fetch_trends = os.path.join(SCRIPTS_DIR, "fetch_trends_data.py")

    def _job_intel():
        if os.path.exists(fetch_intel):
            subprocess.run(
                [sys.executable, fetch_intel, "--topic", search_topic, "--lang", language, "--output", intel_path],
                check=False
            )
        return intel_path if os.path.exists(intel_path) else None

    def _job_trends():
        if os.path.exists(fetch_trends):
            subprocess.run(
                [sys.executable, fetch_trends, "--output", trends_path],
                check=False
            )
        return trends_path if os.path.exists(trends_path) else None

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_job_intel)
        f2 = pool.submit(_job_trends)
        return {
            "viral_intelligence_path": f1.result(),
            "market_trends_path": f2.result()
        }


def run_preflight(channel_id: str | None = None, topic: str | None = None, force_demo: bool = False) -> int:
    t0 = time.time()
    channels_path = os.path.join(ROOT_DIR, "config", "channels.json")
    channels = {}
    default_id = None

    if not force_demo and os.path.exists(channels_path):
        try:
            with open(channels_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            channels = data.get("channels", {})
            default_id = data.get("active_default_channel")
        except Exception:
            channels = {}

    is_demo = force_demo or not channels
    if is_demo:
        active_id = "modo_prueba"
        ch_info = {
            "name": "Piloto Demo Local",
            "group": "demo_group",
            "language": "es",
            "niche": "Curiosidades y Ciencia",
            "purpose": "demo",
            "voice_preference": "es-MX-JorgeNeural",
            "platforms": []
        }
        prefix = "demo"
    else:
        active_id = channel_id or default_id or next(iter(channels.keys()))
        if active_id not in channels:
            print(f"ERROR: El canal '{active_id}' no está registrado en config/channels.json.", file=sys.stderr)
            print(f"Canales disponibles: {', '.join(channels.keys())}", file=sys.stderr)
            return 1
        ch_info = channels[active_id]
        prefix = "auto"

    channel_name = ch_info.get("name", active_id)
    language = ch_info.get("language", "es")
    niche = ch_info.get("niche", "Curiosidades")
    voice_pref = ch_info.get("voice_preference", "es-MX-JorgeNeural" if language == "es" else "en-US-ChristopherNeural")
    platforms = ch_info.get("platforms", [])
    search_topic = topic or (f"curious secrets about {niche}" if language == "en" else f"secretos y datos de {niche}")

    print("\n" + "=" * 65)
    print(f"  PRE-VUELO DE PRODUCCION: {channel_name.upper()} ({active_id})")
    print(f"  Nicho: {niche} | Idioma: {language.upper()} | Voz Oficial: {voice_pref}")
    print(f"  Modo: {'PRUEBA LOCAL (sin redes)' if is_demo else ch_info.get('purpose', 'monetization').upper()} | Rango: 62-72s")
    print("=" * 65)

    # 1. Topic Cooldown Verification (30 days per group)
    cooldown_res = {"allowed": True, "status": "SKIPPED"}
    if topic and check_topic_cooldown:
        cooldown_res = check_topic_cooldown(topic, active_id, cooldown_days=30)
        if not cooldown_res.get("allowed", True):
            print(f"\n[BLOQUEO COOLDOWN 30D] {cooldown_res['reason']}", file=sys.stderr)
            print(f"Días restantes para repetir este tema en el grupo '{cooldown_res['group']}': {cooldown_res['days_remaining']}", file=sys.stderr)
            return 2

    # 2. Session Audit (Preventive Turn-1 Gatekeeping)
    session_audit = audit_channel_sessions(active_id, platforms) if platforms else {
        "ready_platforms": [], "missing_platforms": [], "all_sessions_ready": True
    }
    if session_audit["missing_platforms"]:
        print(f"\n[AVISO SESIONES] Faltan sesiones activas para: {', '.join(session_audit['missing_platforms'])}")
        print(f"Puedes vincularlas con: python scripts/connect_account.py --channel {active_id} --platform <red>")

    # 3. Parallel Intelligence & Trends Extraction
    run_dir = os.path.join(ROOT_DIR, "pipeline_runs", f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(run_dir, exist_ok=True)
    print("\nExtrayendo tendencias e inteligencia viral en paralelo...")
    artifacts = _run_preflight_jobs(run_dir, search_topic=search_topic, language=language)

    elapsed = round(time.time() - t0, 2)
    manifest = {
        "status": "PREFLIGHT_READY",
        "note": "Insumos de pre-vuelo listos. El pipeline completo de 9 subagentes debe continuar con guion, stock/fotos reales, render GPU, QA y empaquetado.",
        "channel_id": active_id,
        "channel_name": channel_name,
        "group": ch_info.get("group") or niche,
        "language": language,
        "voice_preference": voice_pref,
        "target_duration_seconds": [62, 72],
        "seed_topic": search_topic,
        "cooldown_check": cooldown_res,
        "session_audit": session_audit,
        "run_dir": run_dir,
        "artifacts": artifacts,
        "elapsed_seconds": elapsed,
        "created_at": datetime.now().isoformat()
    }
    manifest_path = os.path.join(run_dir, "preflight_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(f"\n[OK] Pre-vuelo completado en {elapsed}s -> {manifest_path}")
    print("Siguiente paso en el Orquestador: despachar subagentes (viral-scriptwriter -> copywriter + visual-asset-reviewer -> video-renderer -> QA -> thumbnail -> archiver).")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Prepare & validate channel production preflight.")
    parser.add_argument("--channel", default=None, help="Channel ID in channels.json")
    parser.add_argument("--topic", default=None, help="Optional specific topic (checked against 30-day group cooldown)")
    parser.add_argument("--demo", action="store_true", help="Force local demo preflight without channel")
    args = parser.parse_args()
    sys.exit(run_preflight(channel_id=args.channel, topic=args.topic, force_demo=args.demo))


if __name__ == "__main__":
    main()
