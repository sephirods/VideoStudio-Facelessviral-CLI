import os
import sys
import subprocess
import argparse
import time

def convert_image_to_vertical_clip(image_path, output_clip_path, duration=4.0, fps=30, zoom_speed=0.00125):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"No existe la imagen: {image_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_clip_path)), exist_ok=True)
    total_frames = int(duration * fps)

    # Detect hardware encoder (try h264_nvenc, fallback to libx264)
    # zoompan filter: scale to high height, then zoom and crop to 1080x1920
    # z zooms from 1.0 to ~1.15 smoothly
    vf_filter = (
        f"scale=-2:2160,"
        f"zoompan=z='min(zoom+{zoom_speed},1.15)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
    )

    encoders = [
        ["-c:v", "h264_nvenc", "-preset", "p4"],
        ["-c:v", "libx264", "-preset", "veryfast"]
    ]

    t0 = time.time()
    success = False
    last_err = ""

    for enc_args in encoders:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", os.path.abspath(image_path),
            "-vf", vf_filter,
            *enc_args,
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            os.path.abspath(output_clip_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            success = True
            break
        else:
            last_err = res.stderr[-300:]

    elapsed = time.time() - t0
    if not success:
        raise RuntimeError(f"FFmpeg fallo al convertir imagen a video: {last_err}")

    return {
        "success": True,
        "clip_path": os.path.abspath(output_clip_path),
        "duration": duration,
        "elapsed_seconds": round(elapsed, 2)
    }

def main():
    parser = argparse.ArgumentParser(description="Convierte imagen real a clip 9:16 con efecto Ken Burns")
    parser.add_argument("--image-path", required=True, help="Ruta de la imagen heroica")
    parser.add_argument("--output-clip", required=True, help="Ruta del video .mp4 resultante")
    parser.add_argument("--duration", type=float, default=4.0, help="Duracion en segundos (default 4.0)")
    args = parser.parse_args()

    try:
        res = convert_image_to_vertical_clip(args.image_path, args.output_clip, duration=args.duration)
        print(f"[OK] Clip 9:16 generado en {res['elapsed_seconds']}s -> {res['clip_path']}")
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
