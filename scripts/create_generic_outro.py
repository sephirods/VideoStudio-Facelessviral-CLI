#!/usr/bin/env python3
"""
Dynamic Per-Channel and Per-Video Short Outro Generator
Creates an animated 1080x1920 (9:16) outro video tailored to the active channel and video footage.
Features:
- Contextual background extracted from the video's last frame with cinematic blur.
- Channel name / niche branding on the top curiosity badge.
- Edge-TTS voiceover using the channel's official voice without duplicate goodbyes.
- Language adaptation (Spanish and English).
- Pulsing high-contrast CTA button and ambient floating particles.
"""
from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


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


def extract_video_last_frame(video_path: str, out_img: str) -> bool:
    try:
        cmd = [
            "ffmpeg", "-y", "-sseof", "-1", "-i", video_path,
            "-update", "1", "-q:v", "2", out_img
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0 and os.path.exists(out_img)
    except Exception as e:
        print(f"Warning: Failed to extract frame from {video_path}: {e}")
        return False


def create_outro_video(
    output_path: str,
    voice: str | None = None,
    spoken_text: str | None = None,
    cta_badge: str | None = None,
    cta_title: str | None = None,
    button_text: str | None = None,
    cta_subtitle: str | None = None,
    video_path: str | None = None,
    source_frame: str | None = None,
    channel_name: str | None = None,
    niche: str | None = None,
    language: str = "es"
):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_dir = output_path + ".temp_frames"
    os.makedirs(temp_dir, exist_ok=True)

    is_english = (language or "es").lower().startswith("en")

    # Smart badge: channel name or niche
    if not cta_badge:
        if channel_name:
            cta_badge = channel_name.strip().upper()
        elif niche:
            cta_badge = niche.strip().upper()[:26]
        else:
            cta_badge = "EXPLORE MORE" if is_english else "DESCUBRE MÁS"

    # Smart title
    if not cta_title:
        cta_title = "WANT TO SEE MORE?" if is_english else "¿QUIERES SABER MÁS?"

    # Smart button
    if not button_text:
        button_text = "+ SUBSCRIBE" if is_english else "+ SUSCRÍBETE"

    # Smart subtitle
    if not cta_subtitle:
        cta_subtitle = "Never miss our next discovery" if is_english else "No te pierdas el próximo descubrimiento"

    # Smart spoken audio text (concise, single CTA, never duplicate goodbyes)
    if not spoken_text:
        spoken_text = "Subscribe now and never miss our next discovery!" if is_english else "¡Suscríbete ahora y no te pierdas el próximo descubrimiento!"

    # Smart voice
    if not voice:
        voice = "en-US-ChristopherNeural" if is_english else "es-MX-JorgeNeural"

    # Smart footer (bullet instead of special unicode to prevent missing glyphs)
    icon_text = "•  NEW VIDEO EVERY DAY  •" if is_english else "•  NUEVO VIDEO CADA DÍA  •"

    audio_path = output_path + ".temp_audio.mp3"
    print(f"Generating outro voiceover with Edge-TTS (voice: {voice})...")
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
    title_font = get_font(size=70, bold=True)
    btn_font = get_font(size=54, bold=True)
    sub_font = get_font(size=36, bold=False)

    # 1. Background image: extract and blur video frame if available
    base_bg = None
    frame_to_use = source_frame

    if not frame_to_use and video_path and os.path.exists(video_path):
        extracted_frame = os.path.join(temp_dir, "extracted_last_frame.jpg")
        if extract_video_last_frame(video_path, extracted_frame):
            frame_to_use = extracted_frame

    if frame_to_use and os.path.exists(frame_to_use):
        try:
            img = Image.open(frame_to_use).convert("RGBA")
            target_ratio = w / h
            img_ratio = img.width / img.height
            if img_ratio > target_ratio:
                new_h = h
                new_w = int(h * img_ratio)
            else:
                new_w = w
                new_h = int(w / img_ratio)
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            base_bg = img_resized.crop((left, top, left + w, top + h))
            # Apply smooth cinematic blur
            base_bg = base_bg.filter(ImageFilter.GaussianBlur(radius=28))
            # Overlay a dark tint layer for maximum legibility and contrast
            overlay = Image.new("RGBA", (w, h), (8, 12, 22, 160))
            base_bg = Image.alpha_composite(base_bg, overlay)
            print(f"Personalized outro background built from footage: {frame_to_use}")
        except Exception as e:
            print(f"Warning: Could not process background frame: {e}")
            base_bg = None

    if base_bg is None:
        # Fallback to dark cinematic navy gradient
        base_bg = Image.new("RGBA", (w, h))
        draw_bg = ImageDraw.Draw(base_bg)
        for y in range(h):
            ratio = y / h
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

        # Floating ambient particles
        for p in particles:
            py = int((h - (t * p["speed"] * 100 + p["seed"])) % h)
            px = int(p["x"] + 15 * math.sin((t * 2 + p["seed"]) * 0.5))
            r = p["radius"]
            draw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 235, 59, p["alpha"]))

        # Glowing central ambient light behind button
        glow_pulse = 0.85 + 0.15 * math.sin(t * math.pi * 2 * 1.5)
        center_x = w // 2
        center_y = int(h * 0.52)

        # Top Badge: Channel Name / Niche
        bbox_badge = badge_font.getbbox(cta_badge)
        bw = bbox_badge[2] - bbox_badge[0]
        bh = bbox_badge[3] - bbox_badge[1]
        badge_y = int(h * 0.28)
        bx0 = (w - bw) // 2 - 25
        by0 = badge_y - 12
        bx1 = bx0 + bw + 50
        by1 = by0 + bh + 24
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=16, fill=(255, 235, 59, 230))
        draw.text(((w - bw) // 2, badge_y - bbox_badge[1]), cta_badge, font=badge_font, fill="#000000")

        # Bold Centered Question / Hook
        bbox_title = title_font.getbbox(cta_title)
        tw = bbox_title[2] - bbox_title[0]
        title_y = int(h * 0.36)
        draw.text(((w - tw) // 2 + 3, title_y + 3), cta_title, font=title_font, fill="#000000", stroke_width=4, stroke_fill="#000000")
        draw.text(((w - tw) // 2, title_y), cta_title, font=title_font, fill="#FFFFFF", stroke_width=2, stroke_fill="#000000")

        # Pulsing CTA Button
        btn_scale = 1.0 + 0.05 * math.sin(t * math.pi * 2 * 1.5)
        btn_w = int(500 * btn_scale)
        btn_h = int(114 * btn_scale)
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
        current_btn_font = get_font(size=int(50 * btn_scale), bold=True)
        bbox_btn = current_btn_font.getbbox(button_text)
        btn_txt_w = bbox_btn[2] - bbox_btn[0]
        btn_txt_h = bbox_btn[3] - bbox_btn[1]
        btn_txt_x = center_x - btn_txt_w // 2
        btn_txt_y = center_y - btn_txt_h // 2 - bbox_btn[1]
        draw.text((btn_txt_x, btn_txt_y), button_text, font=current_btn_font, fill="#FFFFFF", stroke_width=2, stroke_fill="#000000")

        # Subtitle / Value Promise
        bbox_sub = sub_font.getbbox(cta_subtitle)
        sw = bbox_sub[2] - bbox_sub[0]
        sub_y = int(h * 0.65)
        draw.text(((w - sw) // 2, sub_y), cta_subtitle, font=sub_font, fill=(210, 225, 245, 240))

        # Platform / Schedule Hint
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
        "-ar", "44100",
        "-ac", "2",
        "-shortest",
        output_path
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"Personalized outro successfully created: {output_path}")

    # Clean up temp frames and audio
    shutil.rmtree(temp_dir, ignore_errors=True)
    if os.path.exists(audio_path):
        os.remove(audio_path)


def main():
    parser = argparse.ArgumentParser(description="Create personalized short video outro.")
    parser.add_argument("--output", default=os.path.join(ROOT_DIR, "assets", "outro_generico.mp4"), help="Output MP4 path")
    parser.add_argument("--video-path", default=None, help="Video path to extract last frame from for blurred background")
    parser.add_argument("--source-frame", default=None, help="Direct frame path to use for background")
    parser.add_argument("--channel-name", default=None, help="Channel name for top badge")
    parser.add_argument("--niche", default=None, help="Channel niche or topic")
    parser.add_argument("--language", default="es", choices=["es", "en"], help="Language code")
    parser.add_argument("--voice", default=None, help="Edge-TTS voice name")
    parser.add_argument("--text", default=None, help="Spoken CTA text")
    parser.add_argument("--badge", default=None, help="Override badge text")
    parser.add_argument("--title", default=None, help="Override title text")
    parser.add_argument("--button", default=None, help="Override button text")
    parser.add_argument("--subtitle", default=None, help="Override subtitle text")
    args = parser.parse_args()

    create_outro_video(
        output_path=args.output,
        voice=args.voice,
        spoken_text=args.text,
        cta_badge=args.badge,
        cta_title=args.title,
        button_text=args.button,
        cta_subtitle=args.subtitle,
        video_path=args.video_path,
        source_frame=args.source_frame,
        channel_name=args.channel_name,
        niche=args.niche,
        language=args.language
    )


if __name__ == "__main__":
    main()
