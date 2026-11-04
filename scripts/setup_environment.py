#!/usr/bin/env python3
"""
Master Environment Setup & Dependency Installer (Paso 0 CLI)
Installs dependencies, audits FFmpeg, auto-detects hardware encoding,
creates required directory structure and verifies subagent definitions.
Ready for one-click setup after cloning from GitHub.
"""

import json
import os
import shutil
import subprocess
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def print_header(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def step_check_python():
    print_header("1. Verificando Entorno de Python")
    v = sys.version_info
    print(f"Python detectado: {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print("ERROR: Se requiere Python 3.10 o superior.", file=sys.stderr)
        sys.exit(1)
    print("Python OK.")


def step_install_dependencies():
    print_header("2. Instalando Dependencias de Python (requirements.txt)")
    req_file = os.path.join(ROOT_DIR, "requirements.txt")
    if not os.path.exists(req_file):
        print("Aviso: No se encontro requirements.txt, omitiendo pip install.")
        return
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"])
        print("Dependencias de Python instaladas correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"Aviso al instalar dependencias: {e}", file=sys.stderr)


def step_check_ffmpeg():
    print_header("3. Verificando FFmpeg")
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        print(f"FFmpeg encontrado en: {ffmpeg_bin}")
    else:
        print("ADVERTENCIA: FFmpeg no se encontro en el PATH del sistema.", file=sys.stderr)
        print("Instalalo antes de renderizar videos (https://ffmpeg.org/download.html)", file=sys.stderr)


def step_check_engine():
    print_header("4. Verificando Motor de Video (MoneyPrinterTurbo)")
    engine_paths = [
        os.path.join(ROOT_DIR, "engine", "MoneyPrinterTurbo"),
        r"C:\MoneyPrinterTurbo" if sys.platform.startswith("win") else "/opt/MoneyPrinterTurbo"
    ]
    found_path = next((p for p in engine_paths if os.path.exists(p)), None)
    if found_path:
        print(f"Motor de video detectado en: {found_path}")
        return found_path

    target_dir = os.path.join(ROOT_DIR, "engine", "MoneyPrinterTurbo")
    print(f"Motor no detectado. Clonando repositorio oficial en {target_dir}...")
    try:
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        subprocess.check_call(["git", "clone", "https://github.com/harry0703/MoneyPrinterTurbo.git", target_dir])
        req_file = os.path.join(target_dir, "requirements.txt")
        if os.path.exists(req_file):
            print("Instalando requerimientos del motor...")
            subprocess.call([sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"])
        print("Motor de video instalado y configurado.")
        return target_dir
    except Exception as e:
        print(f"Aviso al descargar motor: {e}. Puedes clonarlo en engine/MoneyPrinterTurbo manualmente.")
        return None


def step_detect_hardware():
    print_header("5. Auditando Aceleracion de Hardware de Video")
    detect_script = os.path.join(ROOT_DIR, "scripts", "detect_hardware.py")
    if os.path.exists(detect_script):
        subprocess.call([sys.executable, detect_script])
    else:
        print("Aviso: detect_hardware.py no encontrado.")


def step_ensure_directories():
    print_header("6. Inicializando Estructura de Carpetas")
    dirs = [
        "config",
        "assets/b-roll",
        "videos/publicaciones",
        "videos/biblioteca_stock",
        "pipeline_runs",
        "storage/local_videos"
    ]
    for d in dirs:
        full_p = os.path.join(ROOT_DIR, d)
        os.makedirs(full_p, exist_ok=True)
    print("Estructura de carpetas lista.")

    channels_path = os.path.join(ROOT_DIR, "config", "channels.json")
    if not os.path.exists(channels_path):
        with open(channels_path, "w", encoding="utf-8") as f:
            f.write('{\n  "active_default_channel": null,\n  "channels": {}\n}\n')
        print("config/channels.json inicializado.")


def step_verify_subagents():
    print_header("7. Verificando Definicion de Subagentes")
    agents_dir = os.path.join(ROOT_DIR, ".agents", "agents")
    expected = [
        "trend-researcher",
        "viral-scriptwriter",
        "viral-copywriter",
        "visual-asset-reviewer",
        "video-renderer",
        "video-qa-validator",
        "thumbnail-designer",
        "packaging-archiver",
        "social-media-publisher"
    ]
    found = 0
    for ag in expected:
        agent_file = os.path.join(agents_dir, ag, "agent.md")
        if os.path.exists(agent_file):
            found += 1
            print(f"  [OK] {ag}")
        else:
            print(f"  [FALTA] {ag} -> {agent_file}")
    print(f"\nSubagentes operativos: {found}/{len(expected)}")


def main():
    print_header("FACTORIA DE VIDEO - INSTALADOR Y SETUP MAESTRO")
    step_check_python()
    step_install_dependencies()
    step_check_ffmpeg()
    step_check_engine()
    step_detect_hardware()
    step_ensure_directories()
    step_verify_subagents()
    print_header("INSTALACION COMPLETADA EXITOSAMENTE")
    print("Todo listo. El Orquestador puede operar la factoria de video.")

    channels_path = os.path.join(ROOT_DIR, "config", "channels.json")
    has_channels = False
    if os.path.exists(channels_path):
        try:
            with open(channels_path, "r", encoding="utf-8") as f:
                cdata = json.load(f)
                has_channels = bool(cdata.get("channels"))
        except Exception:
            pass

    if not has_channels:
        print("\n[AVISO] No hay canales configurados todavía en config/channels.json.")
        print("  1) Pídele a tu IA en el chat: 'Quiero configurar mi canal' para iniciar la entrevista.")
        print("  2) O corre el asistente interactivo en terminal: python scripts/onboarding.py")
        print("  3) O genera un video de prueba local: python scripts/produce_channel_video.py --demo")


if __name__ == "__main__":
    main()
