#!/usr/bin/env python3
"""
Vertical 9:16 Ken Burns Clip Converter for Real Subject Photographs
Converts any static photograph (horizontal 16:9, square 1:1, or vertical 9:16) into a
distortion-free 1080x1920 MP4 clip using cover-crop + smooth Ken Burns zoompan and
hardware acceleration configured in config/hardware.json.
"""
import argparse
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


def get_encoder_candidates():
    hw_file = os.path.join(ROOT_DIR, "config", "hardware.json")
    candidates = []
    if os.path.exists(hw_file):
        try:
            with open(hw_file, "r", encoding="utf-8") as f:
                hw = json.load(f)
            enc = hw.get("video_encoder", "h264_nvenc")
            preset = hw.get("ffmpeg_preset", "p4" if "nvenc" in enc else "veryfast")
            if enc != "libx264":
                candidates.append(["-c:v", enc, "-preset", preset])
        except Exception:
            pass
    if not candidates:
        candidates.append(["-c:v", "h264_nvenc", "-preset", "p4"])
    candidates.append(["-c:v", "libx264", "-preset", "veryfast"])
    return candidates


def convert_image_to_vertical_clip(image_path, output_clip_path, duration=4.0, fps=30, zoom_speed=0.00125):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"No existe la imagen: {image_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_clip_path)), exist_ok=True)
    total_frames = max(1, int(round(duration * fps)))

    # 1. Cover-scale & center-crop to exact 9:16 (2160x3840) BEFORE zoompan so aspect ratio
    #    is 100% preserved (never squashes 16:9 or 4:3 images horizontally).
    # 2. Smooth Ken Burns zoom from 1.0x to 1.15x outputting 1080x1920 at 30 fps.
    # 3. No '-loop 1' needed: zoompan generates exact d=total_frames from a single decode.
    vf_filter = (
        f"scale=2160:3840:force_original_aspect_ratio=increase,"
        f"crop=2160:3840,setsar=1,"
        f"zoompan=z='min(zoom+{zoom_speed},1.15)':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps},"
        f"setsar=1"
    )

    encoders = get_encoder_candidates()

    t0 = time.time()
    success = False
    used_encoder = "libx264"
    last_err = ""

    for enc_args in encoders:
        cmd = [
            "ffmpeg", "-y",
            "-i", os.path.abspath(image_path),
            "-vf", vf_filter,
            *enc_args,
            "-t", f"{duration:.3f}",
            "-r", str(fps),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            os.path.abspath(output_clip_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_clip_path):
            success = True
            used_encoder = enc_args[1]
            break
        else:
            last_err = res.stderr[-400:]

    elapsed = time.time() - t0
    if not success:
        raise RuntimeError(f"FFmpeg fallo al convertir imagen a video: {last_err}")

    return {
        "success": True,
        "clip_path": os.path.abspath(output_clip_path),
        "duration": duration,
        "encoder": used_encoder,
        "elapsed_seconds": round(elapsed, 2)
    }


def main():
    parser = argparse.ArgumentParser(description="Convierte imagen real a clip 9:16 con efecto Ken Burns sin deformacion")
    parser.add_argument("--image-path", required=True, help="Ruta de la imagen heroica")
    parser.add_argument("--output-clip", required=True, help="Ruta del video .mp4 resultante")
    parser.add_argument("--duration", type=float, default=4.0, help="Duracion en segundos (default 4.0)")
    args = parser.parse_args()

    try:
        res = convert_image_to_vertical_clip(args.image_path, args.output_clip, duration=args.duration)
        print(f"[OK] Clip 9:16 generado en {res['elapsed_seconds']}s ({res['encoder']}) -> {res['clip_path']}")
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
