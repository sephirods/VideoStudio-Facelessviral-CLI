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
INITIAL_CWD = os.getcwd()
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE_CANDIDATES = [
    os.path.join(ROOT_DIR, "engine", "MoneyPrinterTurbo"),
    r"C:\MoneyPrinterTurbo" if sys.platform.startswith("win") else "/opt/MoneyPrinterTurbo"
]
ENGINE_DIR = next((p for p in ENGINE_CANDIDATES if os.path.exists(p)), ENGINE_CANDIDATES[0])
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

if os.path.exists(ENGINE_DIR):
    # Auto-switch to engine's virtual environment if current python lacks dependencies
    venv_py = os.path.join(ENGINE_DIR, ".venv", "Scripts", "python.exe") if sys.platform.startswith("win") else os.path.join(ENGINE_DIR, ".venv", "bin", "python")
    if os.path.exists(venv_py) and sys.executable.lower() != os.path.abspath(venv_py).lower():
        try:
            import loguru
        except ImportError:
            res = subprocess.run([venv_py] + sys.argv)
            sys.exit(res.returncode)

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


def escape_ffmpeg_filter_path(file_path: str) -> str:
    abs_p = os.path.abspath(file_path).replace("\\", "/")
    return abs_p.replace(":", r"\:").replace("'", r"\'")


def assemble_final_video(
    main_video: str,
    output_path: str,
    ass_path: str | None = None,
    outro_video: str | None = None,
):
    encoder, preset = get_hardware_encoder()
    print(f"Assembling video (Encoder: '{encoder}', Subtitles: '{bool(ass_path)}', Outro: '{bool(outro_video)}')...")
    
    if ass_path and outro_video:
        escaped_ass = escape_ffmpeg_filter_path(ass_path)
        filter_complex = f"[0:v:0]ass='{escaped_ass}'[subv];[subv][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]"
        cmd = [
            "ffmpeg", "-y",
            "-i", main_video,
            "-i", outro_video,
            "-filter_complex", filter_complex,
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
    elif ass_path:
        escaped_ass = escape_ffmpeg_filter_path(ass_path)
        filter_complex = f"[0:v:0]ass='{escaped_ass}'[outv]"
        cmd = [
            "ffmpeg", "-y",
            "-i", main_video,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a:0",
            "-c:v", encoder,
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", "copy",
            output_path
        ]
    elif outro_video:
        filter_complex = "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]"
        cmd = [
            "ffmpeg", "-y",
            "-i", main_video,
            "-i", outro_video,
            "-filter_complex", filter_complex,
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
    else:
        shutil.copy2(main_video, output_path)
        return

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error during video assembly: {res.stderr[-500:]}", file=sys.stderr)
        raise RuntimeError(f"FFmpeg assembly failed: {res.stderr[-200:]}")
    print(f"Final video created: {output_path}")


def append_outro(main_video: str, outro_video: str, output_path: str):
    assemble_final_video(
        main_video=main_video,
        output_path=output_path,
        ass_path=None,
        outro_video=outro_video
    )


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
    parser.add_argument("--channel", default=None, help="Channel identifier or name for personalized outro")
    parser.add_argument("--no-outro", action="store_true", help="Disable automatic outro appending")
    parser.add_argument("--subtitle-style", choices=["hybrid", "hormozi", "typewriter", "mpt_legacy"], default=None, help="Dynamic subtitle style")
    parser.add_argument("--subtitle-color", default=None, help="Accent color (e.g. yellow, cyan, green)")
    args = parser.parse_args()

    if args.script_json and not os.path.isabs(args.script_json):
        args.script_json = os.path.abspath(os.path.join(INITIAL_CWD, args.script_json))
    if args.materials_json and not os.path.isabs(args.materials_json):
        args.materials_json = os.path.abspath(os.path.join(INITIAL_CWD, args.materials_json))
    if args.output_video and not os.path.isabs(args.output_video):
        args.output_video = os.path.abspath(os.path.join(INITIAL_CWD, args.output_video))

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
        # Determinar proveedor dinámico de stock (Pixabay, Pexels o Híbrido)
        try:
            import configure_stock_api
            stock_source = configure_stock_api.get_active_stock_source()
            creds = configure_stock_api.load_stock_credentials()
            is_both_mode = (creds.get("provider_mode") == "both" and
                            bool(creds.get("pexels_api_keys")) and
                            bool(creds.get("pixabay_api_keys")))
        except Exception:
            stock_source = "pixabay"
            is_both_mode = False

        argv_materials = list(argv)
        argv_materials.extend([
            "--video-source", stock_source,
            "--video-terms", terms_csv,
            "--stop-at", "materials"
        ])
        ret = cli.run_cli(argv_materials)

        # Si estamos en modo Híbrido y Pexels falla o está saturado, respaldar automáticamente con Pixabay
        if is_both_mode and ret != 0 and stock_source == "pexels":
            print("Aviso: Reintentando descarga con Pixabay como respaldo automático...")
            argv_fallback = list(argv)
            argv_fallback.extend([
                "--video-source", "pixabay",
                "--video-terms", terms_csv,
                "--stop-at", "materials"
            ])
            return cli.run_cli(argv_fallback)

        return ret

    elif args.mode == "render":
        if not args.materials_json:
            raise ValueError("--materials-json is required in render mode")
        with open(args.materials_json, "r", encoding="utf-8") as f:
            materials_data = json.load(f)
        approved_clips = materials_data["approved_clips"]
        clips_csv = ",".join(approved_clips)

        # 1. Resolve channel metadata and styling preferences
        channel_name = None
        niche = None
        channel_voice = None
        channel_lang = None
        channel_sub_style = None
        channel_sub_color = None
        channels_file = os.path.join(ROOT_DIR, "config", "channels.json")
        if os.path.exists(channels_file):
            try:
                with open(channels_file, "r", encoding="utf-8") as f:
                    ch_data = json.load(f)
                active_id = args.channel or ch_data.get("active_default_channel")
                channels = ch_data.get("channels", {})
                if active_id and active_id in channels:
                    ch_info = channels[active_id]
                elif len(channels) == 1:
                    ch_info = next(iter(channels.values()))
                else:
                    ch_info = {}
                channel_name = ch_info.get("name")
                niche = ch_info.get("niche")
                channel_voice = ch_info.get("voice_preference")
                channel_lang = ch_info.get("language")
                channel_sub_style = ch_info.get("subtitle_style")
                channel_sub_color = ch_info.get("subtitle_color")
            except Exception:
                pass

        # Fallback to script_data fields if present
        if not channel_name and script_data.get("channel_name"):
            channel_name = script_data.get("channel_name")
        if not channel_name and script_data.get("channel"):
            channel_name = str(script_data.get("channel")).replace("_", " ").title()
        if not niche and script_data.get("niche"):
            niche = script_data.get("niche")

        language = script_data.get("language", channel_lang or "es")
        final_voice = script_data.get("voice_name", channel_voice or voice_name)
        subtitle_style = args.subtitle_style or script_data.get("subtitle_style") or channel_sub_style or "hybrid"
        subtitle_color = args.subtitle_color or script_data.get("subtitle_color") or channel_sub_color or "yellow"

        dynamic_ass_path = None
        if subtitle_style != "mpt_legacy":
            scripts_dir = os.path.join(ROOT_DIR, "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from generate_animated_subtitles import generate_animated_subtitles

            task_dir = os.path.join(ENGINE_DIR, "storage", "tasks", task_id)
            os.makedirs(task_dir, exist_ok=True)
            custom_speech_audio = os.path.join(task_dir, "speech.mp3")
            dynamic_ass_path = os.path.join(task_dir, "dynamic_subtitles.ass")

            print(f"Generating dynamic animated subtitles (Style: '{subtitle_style}', Accent: '{subtitle_color}', Voice: '{final_voice}')...")
            generate_animated_subtitles(
                text=full_script,
                voice=final_voice,
                output_audio=custom_speech_audio,
                output_ass=dynamic_ass_path,
                style=subtitle_style,
                accent_color=subtitle_color,
            )

            argv.extend([
                "--video-source", "local",
                "--video-materials", clips_csv,
                "--custom-audio-file", custom_speech_audio,
                "--no-subtitle-enabled",
                "--stop-at", "video"
            ])
        else:
            argv.extend([
                "--subtitle-enabled",
                "--subtitle-background-enabled",
                "--subtitle-background-color", "#000000",
                "--rounded-subtitle-background",
                "--subtitle-position", "custom",
                "--custom-position", "58.0",
                "--video-source", "local",
                "--video-materials", clips_csv,
                "--voice-name", final_voice,
                "--stop-at", "video"
            ])

        ret = cli.run_cli(argv)
        if ret != 0:
            return ret

        # Find rendered final video from engine
        raw_final = os.path.join(ENGINE_DIR, "storage", "tasks", task_id, "final-1.mp4")
        if not os.path.exists(raw_final):
            print(f"Warning: Expected final video not found at {raw_final}")
            return ret

        dest_path = os.path.abspath(args.output_video) if args.output_video else raw_final
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        # 2. Check and generate personalized outro
        outro_to_use = None
        temp_dynamic_outro = None
        if not args.no_outro:
            temp_dynamic_outro = raw_final + ".dynamic_outro.mp4"
            try:
                scripts_dir = os.path.join(ROOT_DIR, "scripts")
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                from create_generic_outro import create_outro_video
                print(f"Generating personalized outro (Channel: '{channel_name}', Voice: '{final_voice}', Lang: '{language}')...")
                create_outro_video(
                    output_path=temp_dynamic_outro,
                    video_path=raw_final,
                    channel_name=channel_name,
                    niche=niche,
                    language=language,
                    voice=final_voice
                )
                if os.path.exists(temp_dynamic_outro):
                    outro_to_use = temp_dynamic_outro
            except Exception as e:
                print(f"Warning: Failed to generate personalized outro ({e}). Checking for generic outro fallback...")

            if not outro_to_use:
                generic_fallback = os.path.join(ROOT_DIR, "assets", "outro_generico.mp4")
                if os.path.exists(generic_fallback):
                    outro_to_use = generic_fallback

        # 3. Assemble: burn dynamic subtitles and/or append outro in a single fast pass
        temp_assembled = raw_final + ".assembled.mp4"
        assemble_final_video(
            main_video=raw_final,
            output_path=temp_assembled,
            ass_path=dynamic_ass_path,
            outro_video=outro_to_use
        )

        shutil.move(temp_assembled, dest_path)
        print(f"Render, dynamic subtitles and assembly complete: {dest_path}")

        # Clean up temporary dynamic outro
        if temp_dynamic_outro and os.path.exists(temp_dynamic_outro):
            try:
                os.remove(temp_dynamic_outro)
            except Exception:
                pass

        return 0


if __name__ == "__main__":
    sys.exit(main())
