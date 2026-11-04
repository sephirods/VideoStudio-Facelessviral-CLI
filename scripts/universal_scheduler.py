#!/usr/bin/env python3
"""
Universal Cross-CLI Scheduler (Disparador Universal)
Soporta piloto automático desatendido en cualquier entorno:
1. Antigravity (/schedule nativo).
2. Windows (Programador de Tareas vía schtasks.exe).
3. Linux / macOS (crontab nativo).
4. Daemon Standalone en Python para cualquier sistema operativo.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_platform_engine() -> str:
    """Detecta el motor nativo de programación según el sistema operativo."""
    current_os = platform.system().lower()
    if "windows" in current_os:
        return "windows_task_scheduler"
    elif "linux" in current_os or "darwin" in current_os:
        return "cron"
    return "daemon"


def register_windows_task(channel_id: str, time_str: str, days: str = "DAILY") -> dict:
    """Registra una tarea programada en Windows con schtasks.exe."""
    task_name = f"FactoriaVideo_{channel_id}"
    python_exe = sys.executable
    script_path = os.path.join(ROOT_DIR, "scripts", "produce_channel_video.py")
    cmd_to_run = f'"{python_exe}" "{script_path}" --channel "{channel_id}"'

    # Formato de schtasks: HH:MM
    sch_cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", cmd_to_run,
        "/sc", days,
        "/st", time_str,
        "/f"  # Sobrescribir si ya existe
    ]

    try:
        res = subprocess.run(sch_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[OK] Tarea programada en Windows creada con exito: {task_name} a las {time_str}")
            return {"status": "success", "engine": "windows_task_scheduler", "task_name": task_name, "time": time_str}
        else:
            print(f"Aviso schtasks: {res.stderr.strip()}", file=sys.stderr)
            return {"status": "error", "engine": "windows_task_scheduler", "details": res.stderr.strip()}
    except Exception as e:
        return {"status": "error", "engine": "windows_task_scheduler", "details": str(e)}


def register_linux_cron(channel_id: str, cron_expr: str) -> dict:
    """Añade una entrada al crontab de Linux/macOS."""
    python_exe = sys.executable
    script_path = os.path.join(ROOT_DIR, "scripts", "produce_channel_video.py")
    cron_line = f"{cron_expr} {python_exe} {script_path} --channel {channel_id} # FactoriaVideo_{channel_id}\n"

    try:
        # Obtener crontab actual
        current_cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        if f"FactoriaVideo_{channel_id}" not in current_cron:
            new_cron = current_cron + cron_line
            proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
            proc.communicate(new_cron)
            print(f"[OK] Tarea registrada en crontab para el canal {channel_id}: {cron_expr}")
            return {"status": "success", "engine": "cron", "cron_expr": cron_expr}
        return {"status": "already_exists", "engine": "cron"}
    except Exception as e:
        return {"status": "error", "engine": "cron", "details": str(e)}


def run_standalone_daemon(channel_id: str, interval_hours: int = 24):
    """Bucle ligero en segundo plano que produce un video a intervalos regulares."""
    print(f"[DAEMON] Iniciando servicio en segundo plano para el canal '{channel_id}' cada {interval_hours} horas...")
    python_exe = sys.executable
    script_path = os.path.join(ROOT_DIR, "scripts", "produce_channel_video.py")

    while True:
        print(f"\n[DAEMON] Disparando producción de video automática: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        subprocess.run([python_exe, script_path, "--channel", channel_id])
        print(f"[DAEMON] Producción finalizada. Esperando {interval_hours} horas...")
        time.sleep(interval_hours * 3600)


def configure_channel_schedule(channel_id: str, mode: str, time_str: str = "19:00", days: str = "DAILY") -> dict:
    """Actualiza la configuración en config/channels.json y registra el disparador."""
    channels_path = os.path.join(ROOT_DIR, "config", "channels.json")
    if not os.path.exists(channels_path):
        return {"status": "error", "details": "channels.json no encontrado"}

    with open(channels_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if channel_id not in data.get("channels", {}):
        return {"status": "error", "details": f"Canal '{channel_id}' no existe en channels.json"}

    detected_engine = get_platform_engine()
    schedule_data = {
        "mode": mode,  # "on_demand" o "automated"
        "time": time_str,
        "cadence": days,
        "engine": detected_engine
    }

    data["channels"][channel_id]["schedule"] = schedule_data

    with open(channels_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Configuracion de horario guardada para '{channel_id}' en config/channels.json")

    # Si es automático y no es Antigravity nativo, intentar registrar en SO
    if mode == "automated":
        if detected_engine == "windows_task_scheduler":
            return register_windows_task(channel_id, time_str, days=days)
        elif detected_engine == "cron":
            # Convertir HH:MM a cron diario: MM HH * * *
            parts = time_str.split(":")
            minute = parts[1] if len(parts) > 1 else "0"
            hour = parts[0]
            cron_expr = f"{minute} {hour} * * *"
            return register_linux_cron(channel_id, cron_expr)

    return {"status": "success", "mode": mode, "engine": detected_engine}


def main():
    parser = argparse.ArgumentParser(description="Universal Cross-CLI Scheduler")
    parser.add_argument("--channel", required=True, help="ID del canal")
    parser.add_argument("--mode", choices=["on_demand", "automated"], default="on_demand", help="Modo: a pedido o automatico")
    parser.add_argument("--time", default="19:00", help="Hora de disparo (formato HH:MM)")
    parser.add_argument("--cadence", default="DAILY", choices=["DAILY", "WEEKLY"], help="Cadencia de disparo")
    parser.add_argument("--daemon", action="store_true", help="Ejecutar como daemon en segundo plano")
    parser.add_argument("--interval-hours", type=int, default=24, help="Intervalo en horas para modo daemon")

    args = parser.parse_args()

    if args.daemon:
        run_standalone_daemon(args.channel, interval_hours=args.interval_hours)
    else:
        res = configure_channel_schedule(
            channel_id=args.channel,
            mode=args.mode,
            time_str=args.time,
            days=args.cadence
        )
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
