#!/usr/bin/env python3
"""
Fast Parallel Contact Sheet / Mosaic Generator for Visual Asset Review
Extrae fotogramas clave en paralelo (8 hilos) y los une en una sola
cuadrícula visual numerada (Contact Sheet) en alta resolución (<1s).
Permite a la IA inspeccionar 16-20 clips en UNA SOLA llamada visual.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import glob
import json
import math
import os
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def extract_frame_from_clip(video_path: str, output_jpg: str, timestamp_sec: float = 1.2) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp_sec),
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "3",
        output_jpg
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0 and os.path.exists(output_jpg)


def build_contact_sheet(clips: list, output_image: str, temp_dir: str = None) -> dict:
    if not clips:
        return {"total_clips": 0, "mosaic_path": None, "clip_map": {}}

    if not temp_dir:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(output_image)), "_thumbs_tmp")
    os.makedirs(temp_dir, exist_ok=True)

    thumb_w, thumb_h = 240, 426  # Relación vertical 9:16
    n = len(clips)
    cols = 4 if n <= 16 else 5
    rows = math.ceil(n / cols)

    cell_padding = 8
    badge_h = 36
    cell_w = thumb_w + cell_padding * 2
    cell_h = thumb_h + cell_padding * 2 + badge_h

    grid_w = cols * cell_w
    grid_h = rows * cell_h

    canvas = Image.new("RGB", (grid_w, grid_h), color=(18, 18, 22))
    draw = ImageDraw.Draw(canvas)

    try:
        font_large = ImageFont.truetype("arialbd.ttf", 22)
        font_small = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = font_large

    # Extract all thumbnails in parallel (8 threads)
    def _extract_worker(idx_clip):
        i, clip_path = idx_clip
        clip_num = i + 1
        thumb_file = os.path.join(temp_dir, f"thumb_{clip_num:02d}.jpg")
        ok = extract_frame_from_clip(clip_path, thumb_file, timestamp_sec=1.2)
        return i, clip_path, thumb_file, ok

    with ThreadPoolExecutor(max_workers=8) as pool:
        extracted_results = list(pool.map(_extract_worker, enumerate(clips)))

    clip_map = {}
    for i, clip_path, thumb_file, ok in extracted_results:
        clip_num = i + 1
        clip_map[str(clip_num)] = clip_path
        row = i // cols
        col = i % cols

        x_base = col * cell_w + cell_padding
        y_base = row * cell_h + cell_padding

        if ok:
            try:
                with Image.open(thumb_file) as im:
                    im_resized = im.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    canvas.paste(im_resized, (x_base, y_base + badge_h))
            except Exception:
                draw.rectangle([x_base, y_base + badge_h, x_base + thumb_w, y_base + badge_h + thumb_h], fill=(40, 40, 45))
        else:
            draw.rectangle([x_base, y_base + badge_h, x_base + thumb_w, y_base + badge_h + thumb_h], fill=(30, 30, 35))

        badge_bg = (245, 180, 0) if clip_num % 2 == 1 else (255, 205, 40)
        draw.rectangle([x_base, y_base, x_base + thumb_w, y_base + badge_h], fill=(26, 26, 32))
        draw.rectangle([x_base + 4, y_base + 4, x_base + 55, y_base + badge_h - 4], fill=badge_bg)
        draw.text((x_base + 10, y_base + 6), f"#{clip_num:02d}", fill=(0, 0, 0), font=font_large)

        base_name = os.path.basename(clip_path)
        if len(base_name) > 22:
            base_name = base_name[:19] + "..."
        draw.text((x_base + 64, y_base + 10), base_name, fill=(220, 220, 230), font=font_small)
        draw.rectangle([x_base - 2, y_base - 2, x_base + thumb_w + 2, y_base + badge_h + thumb_h + 2], outline=(60, 60, 70), width=1)

    os.makedirs(os.path.dirname(os.path.abspath(output_image)), exist_ok=True)
    canvas.save(output_image, "JPEG", quality=90)

    try:
        for f in glob.glob(os.path.join(temp_dir, "thumb_*.jpg")):
            os.remove(f)
        os.rmdir(temp_dir)
    except Exception:
        pass

    manifest = {
        "total_clips": n,
        "grid_dimensions": f"{cols}x{rows}",
        "mosaic_path": output_image,
        "clip_map": clip_map
    }

    manifest_path = os.path.splitext(output_image)[0] + "_map.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate visual contact sheet from clips")
    parser.add_argument("--clips-dir", default=None, help="Directory containing .mp4 clips")
    parser.add_argument("--clips-list", default=None, help="JSON file or comma-separated list of clip paths")
    parser.add_argument("--output", required=True, help="Path for output mosaic image (.jpg)")
    args = parser.parse_args()

    clips = []
    if args.clips_dir and os.path.exists(args.clips_dir):
        clips = sorted(glob.glob(os.path.join(args.clips_dir, "*.mp4")))
    elif args.clips_list:
        if os.path.exists(args.clips_list):
            with open(args.clips_list, "r", encoding="utf-8") as f:
                data = json.load(f)
                clips = data if isinstance(data, list) else data.get("clips", data.get("approved_clips", []))
        else:
            clips = [p.strip() for p in args.clips_list.split(",") if p.strip()]

    if not clips:
        print("ERROR: No se encontraron clips de video para generar el mosaico.", file=sys.stderr)
        return 1

    manifest = build_contact_sheet(clips, args.output)
    print(f"[OK] Mosaico de contacto generado exitosamente: {manifest['mosaic_path']}")
    print(f"Total clips analizados en el mosaico: {manifest['total_clips']} ({manifest['grid_dimensions']})")
    print(f"Mapa de clips guardado en: {os.path.splitext(args.output)[0] + '_map.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
