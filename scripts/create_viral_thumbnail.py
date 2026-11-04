#!/usr/bin/env python3
"""
High-CTR Viral Thumbnail Generator
Creates eye-catching clickbait thumbnails for YouTube Shorts, TikTok, and Instagram Reels.
Features: Impact typography, contrast outline, drop shadow, dark vignette, and highlight badge.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


def extract_frame(video_path: str, timestamp: str, out_path: str):
    cmd = [
        "ffmpeg", "-ss", timestamp, "-i", video_path,
        "-vframes", "1", "-q:v", "2", out_path, "-y"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


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


def sanitize_text(text: str) -> str:
    # Filter out emoji characters that font engines like Impact cannot render properly
    return "".join(c for c in text if ord(c) < 0xFFFF)


def create_thumbnail(
    image_path: str,
    output_path: str,
    main_text: str,
    badge_text: str | None = None,
    text_color: str = "#FFEB3B",  # Electric yellow
    stroke_color: str = "#000000",
    stroke_width: int = 10,
    accent_color: str = "#FF1744"  # Red for badge
):
    main_text = sanitize_text(main_text)
    if badge_text:
        badge_text = sanitize_text(badge_text).strip()
    img = Image.open(image_path).convert("RGBA")

    # Ensure 9:16 vertical target resolution (1080x1920) with cover fit
    target_w, target_h = 1080, 1920
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        # Source is wider, scale by height and crop center horizontally
        scale = target_h / src_h
        new_w = int(src_w * scale)
        img_resized = img.resize((new_w, target_h), Image.Resampling.LANCZOS)
        crop_x = int((new_w - target_w) / 2)
        img = img_resized.crop((crop_x, 0, crop_x + target_w, target_h))
    else:
        # Source is taller, scale by width and crop center vertically
        scale = target_w / src_w
        new_h = int(src_h * scale)
        img_resized = img.resize((target_w, new_h), Image.Resampling.LANCZOS)
        crop_y = int((new_h - target_h) / 2)
        img = img_resized.crop((0, crop_y, target_w, crop_y + target_h))

    w, h = target_w, target_h

    # Enhance contrast and saturation slightly for punchy visuals
    enhancer_con = ImageEnhance.Contrast(img)
    img = enhancer_con.enhance(1.15)
    enhancer_sat = ImageEnhance.Color(img)
    img = enhancer_sat.enhance(1.2)

    # Create dark vignette / gradient overlay at top and bottom
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # Top subtle dark gradient (for badge or title)
    for y in range(int(h * 0.25)):
        alpha = int(140 * (1.0 - (y / (h * 0.25))))
        draw_overlay.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        
    # Center-bottom dark vignette for text legibility
    for y in range(int(h * 0.45), h):
        progress = (y - (h * 0.45)) / (h * 0.55)
        alpha = int(180 * progress)
        draw_overlay.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Calculate Fonts
    main_font_size = int(w * 0.095)  # ~102px
    main_font = get_font(size=main_font_size, bold=True)

    # Word wrap main text
    words = main_text.split()
    lines = []
    curr_line = []
    for word in words:
        curr_line.append(word)
        test_str = " ".join(curr_line)
        tb = main_font.getbbox(test_str)
        if (tb[2] - tb[0]) > (w * 0.88):
            if len(curr_line) > 1:
                curr_line.pop()
                lines.append(" ".join(curr_line))
                curr_line = [word]
            else:
                lines.append(test_str)
                curr_line = []
    if curr_line:
        lines.append(" ".join(curr_line))

    line_height = int(main_font_size * 1.15)
    total_main_text_h = len(lines) * line_height

    # Badge measurements (Large & prominent clickbait badge)
    has_badge = bool(badge_text)
    badge_total_h = 0
    badge_gap = 35
    if has_badge:
        # Giant badge font size (~72px on 1080w)
        badge_font_size = int(w * 0.068)
        badge_font = get_font(size=badge_font_size, bold=True)
        bbox = badge_font.getbbox(badge_text)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        pad_x = 45
        pad_y = 22
        badge_box_w = bw + 2 * pad_x
        badge_box_h = bh + 2 * pad_y
        badge_total_h = badge_box_h + badge_gap

    # Calculate unified vertical center block (around 52% of canvas height)
    total_block_h = badge_total_h + total_main_text_h
    center_focal_y = int(h * 0.54)
    block_start_y = max(int(h * 0.20), center_focal_y - int(total_block_h / 2))

    # 1. Draw Centered Giant Badge
    if has_badge:
        bx0 = int((w - badge_box_w) / 2)
        by0 = block_start_y
        bx1 = bx0 + badge_box_w
        by1 = by0 + badge_box_h

        # Badge drop shadow
        draw.rounded_rectangle(
            [bx0 + 6, by0 + 6, bx1 + 6, by1 + 6],
            radius=24,
            fill=(0, 0, 0, 180)
        )
        # Badge outer outline for contrast
        draw.rounded_rectangle(
            [bx0 - 3, by0 - 3, bx1 + 3, by1 + 3],
            radius=26,
            fill="#000000"
        )
        # Badge fill (Vibrant Red)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=24, fill=accent_color)

        # Draw badge text (Bold White with crisp dark shadow)
        draw.text(
            (bx0 + pad_x, by0 + pad_y - bbox[1]),
            badge_text,
            font=badge_font,
            fill="#FFFFFF",
            stroke_width=3,
            stroke_fill="#000000"
        )

    # 2. Draw Main Hook Text (Directly below badge, centered)
    main_text_start_y = block_start_y + badge_total_h

    for i, line in enumerate(lines):
        bbox = main_font.getbbox(line)
        lw = bbox[2] - bbox[0]
        lx = int((w - lw) / 2)
        ly = main_text_start_y + (i * line_height)

        # Deep drop shadow
        draw.text(
            (lx + 7, ly + 7),
            line,
            font=main_font,
            fill="#000000",
            stroke_width=stroke_width + 5,
            stroke_fill="#000000"
        )
        # Main text with thick outline
        draw.text(
            (lx, ly),
            line,
            font=main_font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_color
        )

    # Convert back to RGB and save
    final_img = img.convert("RGB")
    final_img.save(output_path, "JPEG", quality=95)
    print(f"Thumbnail created successfully: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Create viral high-CTR thumbnail.")
    parser.add_argument("--video-path", default=None, help="Input video MP4 path")
    parser.add_argument("--frame-path", default=None, help="Input image/frame path")
    parser.add_argument("--timestamp", default="00:00:04", help="Frame timestamp if extracting from video")
    parser.add_argument("--hook-text", required=True, help="Main clickbait hook text (ALL CAPS)")
    parser.add_argument("--badge-text", default=None, help="Top badge/pill text (optional)")
    parser.add_argument("--output", required=True, help="Output JPG path")
    parser.add_argument("--color", default="#FFEB3B", help="Text color hex (default yellow)")
    args = parser.parse_args()

    temp_frame = None
    if args.video_path:
        temp_frame = args.output + ".temp_frame.jpg"
        extract_frame(args.video_path, args.timestamp, temp_frame)
        input_image = temp_frame
    elif args.frame_path:
        input_image = args.frame_path
    else:
        raise ValueError("Must provide either --video-path or --frame-path")

    try:
        create_thumbnail(
            image_path=input_image,
            output_path=args.output,
            main_text=args.hook_text,
            badge_text=args.badge_text,
            text_color=args.color
        )
    finally:
        if temp_frame and os.path.exists(temp_frame):
            try:
                os.remove(temp_frame)
            except OSError:
                pass


if __name__ == "__main__":
    main()
