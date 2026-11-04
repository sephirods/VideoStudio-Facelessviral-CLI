#!/usr/bin/env python3
"""
Generic Short-Video Outro Generator
Creates an animated 1080x1920 (9:16) outro video with a pulsing CTA button,
Edge-TTS Spanish voiceover, and universal follow prompt for TikTok, Shorts, and Reels.
"""
from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def get_font(size: int, bold: bool = True):
    font_paths = [
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\MoneyPrinterTurbo\resource\fonts\MicrosoftYaHeiBold.ttc"
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_tts_audio(text: str, voice: str, out_path: str):
    cmd = [
        "edge-tts",
        "--voice", voice,
        "--text", text,
        "--write-media", out_path
    ]
    subprocess.run(cmd, check=True)


def create_outro_video(
    output_path: str,
    voice: str = "es-MX-JorgeNeural",
    spoken_text: str = "¿Quieres saber más? ¡Síguenos y no te pierdas el próximo dato!",
    cta_badge: str = "CURIOSIDAD DIARIA",
    cta_title: str = "¿QUIERES SABER MÁS?",
    button_text: str = "+ SÍGUENOS",
    cta_subtitle: str = "Descubre los secretos que nadie te cuenta"
):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_dir = output_path + ".temp_frames"
    os.makedirs(temp_dir, exist_ok=True)

    audio_path = output_path + ".temp_audio.mp3"
    print("Generating outro voiceover with Edge-TTS...")
    generate_tts_audio(spoken_text, voice, audio_path)

    # Get exact audio duration via ffprobe
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    audio_dur = float(res.stdout.strip())
    # Add 0.5s pause after audio for clean finish
    total_dur = max(3.5, audio_dur + 0.5)

    fps = 30
    total_frames = int(total_dur * fps)
    w, h = 1080, 1920

    print(f"Rendering {total_frames} frames ({total_dur:.2f}s at {fps} fps)...")

    # Pre-load fonts
    badge_font = get_font(size=36, bold=True)
    title_font = get_font(size=72, bold=True)
    btn_font = get_font(size=56, bold=True)
    sub_font = get_font(size=36, bold=False)

    # Pre-render static background gradient
    base_bg = Image.new("RGBA", (w, h))
    draw_bg = ImageDraw.Draw(base_bg)
    for y in range(h):
        ratio = y / h
        # Deep cinematic dark navy to charcoal
        r = int(12 * (1 - ratio) + 4 * ratio)
        g = int(20 * (1 - ratio) + 6 * ratio)
        b = int(38 * (1 - ratio) + 12 * ratio)
        draw_bg.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # Pre-calculate particle positions
    num_particles = 35
    particles = []
    for i in range(num_particles):
        px = (i * 97) % w
        speed = 1.5 + ((i * 13) % 25) / 10.0
        rad = 3 + (i % 5)
        alpha = 80 + (i * 23) % 120
        particles.append({"x": px, "speed": speed, "radius": rad, "alpha": alpha, "seed": i * 110})

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        frame = base_bg.copy()
        draw = ImageDraw.Draw(frame)

        # 1. Floating ambient particles
        for p in particles:
            py = int((h - (t * p["speed"] * 100 + p["seed"])) % h)
            px = int(p["x"] + 15 * math.sin((t * 2 + p["seed"]) * 0.5))
            r = p["radius"]
            draw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 235, 59, p["alpha"]))

        # 2. Glowing central ambient light behind button
        glow_pulse = 0.85 + 0.15 * math.sin(t * math.pi * 2 * 1.5)
        glow_radius = int(350 * glow_pulse)
        center_x = w // 2
        center_y = int(h * 0.52)

        # 3. Top Curiosity Badge
        bbox_badge = badge_font.getbbox(cta_badge)
        bw = bbox_badge[2] - bbox_badge[0]
        bh = bbox_badge[3] - bbox_badge[1]
        badge_y = int(h * 0.28)
        bx0 = (w - bw) // 2 - 25
        by0 = badge_y - 12
        bx1 = bx0 + bw + 50
        by1 = by0 + bh + 24
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=16, fill=(255, 235, 59, 220))
        draw.text(((w - bw) // 2, badge_y - bbox_badge[1]), cta_badge, font=badge_font, fill="#000000")

        # 4. Bold Centered Question / Hook
        bbox_title = title_font.getbbox(cta_title)
        tw = bbox_title[2] - bbox_title[0]
        title_y = int(h * 0.36)
        draw.text(((w - tw) // 2 + 3, title_y + 3), cta_title, font=title_font, fill="#000000", stroke_width=4, stroke_fill="#000000")
        draw.text(((w - tw) // 2, title_y), cta_title, font=title_font, fill="#FFFFFF", stroke_width=2, stroke_fill="#000000")

        # 5. Pulsing CTA Button
        btn_scale = 1.0 + 0.05 * math.sin(t * math.pi * 2 * 1.5)
        btn_w = int(480 * btn_scale)
        btn_h = int(110 * btn_scale)
        btn_x0 = center_x - btn_w // 2
        btn_y0 = center_y - btn_h // 2
        btn_x1 = btn_x0 + btn_w
        btn_y1 = btn_y0 + btn_h

        # Button Outer Glow / Halo
        draw.rounded_rectangle(
            [btn_x0 - 8, btn_y0 - 8, btn_x1 + 8, btn_y1 + 8],
            radius=int(32 * btn_scale),
            fill=(255, 23, 68, 90)
        )
        # Button Shadow
        draw.rounded_rectangle(
            [btn_x0 + 6, btn_y0 + 6, btn_x1 + 6, btn_y1 + 6],
            radius=int(28 * btn_scale),
            fill=(0, 0, 0, 160)
        )
        # Button Body (Electric Crimson)
        draw.rounded_rectangle(
            [btn_x0, btn_y0, btn_x1, btn_y1],
            radius=int(26 * btn_scale),
            fill=(255, 23, 68, 255)
        )

        # Button Text
        current_btn_font = get_font(size=int(52 * btn_scale), bold=True)
        bbox_btn = current_btn_font.getbbox(button_text)
        btn_txt_w = bbox_btn[2] - bbox_btn[0]
        btn_txt_h = bbox_btn[3] - bbox_btn[1]
        btn_txt_x = center_x - btn_txt_w // 2
        btn_txt_y = center_y - btn_txt_h // 2 - bbox_btn[1]
        draw.text((btn_txt_x, btn_txt_y), button_text, font=current_btn_font, fill="#FFFFFF", stroke_width=2, stroke_fill="#000000")

        # 6. Subtitle / Value Promise
        bbox_sub = sub_font.getbbox(cta_subtitle)
        sw = bbox_sub[2] - bbox_sub[0]
        sub_y = int(h * 0.65)
        draw.text(((w - sw) // 2, sub_y), cta_subtitle, font=sub_font, fill=(200, 210, 230, 240))

        # 7. Subtle platform icons hint (Checkmark / Bell)
        icon_text = "✦  NUEVO VIDEO CADA DÍA  ✦"
        bbox_ico = badge_font.getbbox(icon_text)
        iw = bbox_ico[2] - bbox_ico[0]
        draw.text(((w - iw) // 2, int(h * 0.72)), icon_text, font=badge_font, fill=(255, 235, 59, 210))

        frame_file = os.path.join(temp_dir, f"frame_{frame_idx:05d}.jpg")
        frame.convert("RGB").save(frame_file, "JPEG", quality=90)

    # Encode video + audio with FFmpeg
    print("Encoding final outro video with FFmpeg...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(temp_dir, "frame_%05d.jpg"),
        "-i", audio_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"Generic outro successfully created: {output_path}")

    # Clean up temp frames and audio
    shutil.rmtree(temp_dir, ignore_errors=True)
    if os.path.exists(audio_path):
        os.remove(audio_path)


def main():
    parser = argparse.ArgumentParser(description="Create generic short video outro.")
    parser.add_argument("--output", default=r"c:\ganar dinero\assets\outro_generico.mp4", help="Output MP4 path")
    parser.add_argument("--voice", default="es-MX-JorgeNeural", help="Edge-TTS voice name")
    parser.add_argument("--text", default="¿Quieres saber más? ¡Síguenos y no te pierdas el próximo dato!", help="Spoken CTA")
    args = parser.parse_args()

    create_outro_video(args.output, voice=args.voice, spoken_text=args.text)


if __name__ == "__main__":
    main()
