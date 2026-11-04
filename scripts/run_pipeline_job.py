#!/usr/bin/env python3
"""
Pipeline Job Runner for MoneyPrinterTurbo
Executes pipeline stages ensuring:
1. 100% native UTF-8 encoding for scripts, subtitles, and voices.
2. Centered subtitle positioning (custom_position = 58.0) above mobile UI.
3. High-contrast rounded dark background capsule.
4. Seamless automated appending of the generic outro card (assets/outro_generico.mp4).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid

# Ensure MoneyPrinterTurbo is on the import path dynamically
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE_CANDIDATES = [
    os.path.join(ROOT_DIR, "engine", "MoneyPrinterTurbo"),
    r"C:\MoneyPrinterTurbo" if sys.platform.startswith("win") else "/opt/MoneyPrinterTurbo"
]
ENGINE_DIR = next((p for p in ENGINE_CANDIDATES if os.path.exists(p)), ENGINE_CANDIDATES[0])
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

if os.path.exists(ENGINE_DIR):
    os.chdir(ENGINE_DIR)
    import cli
else:
    cli = None


def get_hardware_encoder():
    hw_file = os.path.join(ROOT_DIR, "config", "hardware.json")
    if os.path.exists(hw_file):
        try:
            with open(hw_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("video_encoder", "libx264"), data.get("ffmpeg_preset", "fast")
        except Exception:
            pass
    return "libx264", "fast"


def append_outro(main_video: str, outro_video: str, output_path: str):
    encoder, preset = get_hardware_encoder()
    print(f"Appending outro ({outro_video}) to {main_video} using encoder '{encoder}'...")
    cmd = [
        "ffmpeg", "-y",
        "-i", main_video,
        "-i", outro_video,
        "-filter_complex",
        "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]",
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", encoder,
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Final video with outro created: {output_path}")


def main():
    if cli is None:
        print(f"ERROR: Motor de video no encontrado en {ENGINE_DIR}.", file=sys.stderr)
        print("Ejecuta 'python scripts/setup_environment.py' para instalarlo automáticamente.", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Run MoneyPrinterTurbo pipeline with native UTF-8.")
    parser.add_argument("--mode", choices=["materials", "render"], required=True)
    parser.add_argument("--script-json", required=True, help="Path to video_script.json")
    parser.add_argument("--materials-json", default=None, help="Path to approved_materials.json (for render mode)")
    parser.add_argument("--task-id", default=None, help="Task UUID")
    parser.add_argument("--output-video", default=None, help="Destination MP4 path (e.g. videos/slug.mp4)")
    parser.add_argument("--no-outro", action="store_true", help="Disable automatic outro appending")
    args = parser.parse_args()

    with open(args.script_json, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    full_script = script_data["full_script"]
    voice_name = script_data.get("voice_name", "es-MX-JorgeNeural")

    task_id = args.task_id or str(uuid.uuid4())

    argv = [
        "--task-id", task_id,
        "--video-script", full_script,
        "--video-aspect", "9:16",
        "--video-clip-duration", "4",
        "--bgm-type", "random",
        "--bgm-volume", "0.2",
        "--subtitle-enabled",
        "--subtitle-background-enabled",
        "--subtitle-background-color", "#000000",
        "--rounded-subtitle-background",
        "--subtitle-position", "custom",
        "--custom-position", "58.0",
    ]

    if args.mode == "materials":
        terms_csv = script_data.get("video_terms_csv", "")
        argv.extend([
            "--video-source", "pixabay",
            "--video-terms", terms_csv,
            "--stop-at", "materials"
        ])
        return cli.run_cli(argv)

    elif args.mode == "render":
        if not args.materials_json:
            raise ValueError("--materials-json is required in render mode")
        with open(args.materials_json, "r", encoding="utf-8") as f:
            materials_data = json.load(f)
        approved_clips = materials_data["approved_clips"]
        clips_csv = ",".join(approved_clips)
        argv.extend([
            "--video-source", "local",
            "--video-materials", clips_csv,
            "--voice-name", voice_name,
            "--stop-at", "video"
        ])

        ret = cli.run_cli(argv)
        if ret != 0:
            return ret

        # Find rendered final video
        raw_final = os.path.join(ENGINE_DIR, "storage", "tasks", task_id, "final-1.mp4")
        if not os.path.exists(raw_final):
            print(f"Warning: Expected final video not found at {raw_final}")
            return ret

        outro_path = os.path.join(ROOT_DIR, "assets", "outro_generico.mp4")
        dest_path = args.output_video or raw_final

        if not args.no_outro and os.path.exists(outro_path):
            temp_out = raw_final + ".with_outro.mp4"
            append_outro(raw_final, outro_path, temp_out)
            shutil.move(temp_out, dest_path)
            print(f"Render and outro append complete: {dest_path}")
        elif args.output_video:
            shutil.copy2(raw_final, args.output_video)
            print(f"Copied final video to: {args.output_video}")

        return 0


if __name__ == "__main__":
    sys.exit(main())
