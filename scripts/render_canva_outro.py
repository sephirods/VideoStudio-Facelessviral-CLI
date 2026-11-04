#!/usr/bin/env python3
"""
Animate Canva Outro Card with Edge-TTS voiceover.
Produces assets/outro_generico.mp4 (1080x1920, 30fps).
"""
import os
import subprocess
import shutil
import math
from PIL import Image, ImageEnhance

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CANVA_PNG = os.path.join(ROOT_DIR, "assets", "canva_outro_card.png")
OUTPUT_MP4 = os.path.join(ROOT_DIR, "assets", "outro_generico.mp4")
TEMP_DIR = os.path.join(ROOT_DIR, "assets", "temp_outro_frames")
AUDIO_PATH = os.path.join(ROOT_DIR, "assets", "temp_outro_audio.mp3")

def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # 1. Generate Voiceover with Edge-TTS
    spoken_text = "¿Quieres saber más? ¡Síguenos para más secretos!"
    print("Generating voiceover...")
    cmd_tts = [
        "edge-tts",
        "--voice", "es-MX-JorgeNeural",
        "--rate=+10%",
        "--text", spoken_text,
        "--write-media", AUDIO_PATH
    ]
    subprocess.run(cmd_tts, check=True)
    
    # 2. Probe audio duration
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", AUDIO_PATH
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    audio_dur = float(res.stdout.strip())
    total_dur = max(3.5, audio_dur + 0.4)
    
    fps = 30
    total_frames = int(total_dur * fps)
    print(f"Total duration: {total_dur:.2f}s ({total_frames} frames)")
    
    # Load base Canva image
    base_img = Image.open(CANVA_PNG).convert("RGBA")
    # Ensure exact 1080x1920
    base_img = base_img.resize((1080, 1920), Image.Resampling.LANCZOS)
    w, h = 1080, 1920
    
    # Pre-render frames with smooth cinematic slow zoom + brightness breathe
    print("Rendering animated frames...")
    for i in range(total_frames):
        t = i / total_frames  # 0.0 to 1.0
        
        # Smooth ease-out zoom factor (from 1.00 to 1.05)
        zoom = 1.00 + 0.05 * (1.0 - math.cos(t * math.pi * 0.5))
        
        # Crop & resize for zoom
        crop_w = int(w / zoom)
        crop_h = int(h / zoom)
        x0 = (w - crop_w) // 2
        y0 = (h - crop_h) // 2
        frame = base_img.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        frame = frame.resize((w, h), Image.Resampling.LANCZOS)
        
        # Subtle glowing pulse in the center button
        pulse = 1.0 + 0.03 * math.sin(i / 30.0 * math.pi * 2 * 1.5)
        enhancer = ImageEnhance.Brightness(frame)
        frame = enhancer.enhance(pulse)
        
        frame_path = os.path.join(TEMP_DIR, f"frame_{i:05d}.jpg")
        frame.convert("RGB").save(frame_path, "JPEG", quality=95)
        
    print("Encoding outro with FFmpeg...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(TEMP_DIR, "frame_%05d.jpg"),
        "-i", AUDIO_PATH,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-shortest",
        OUTPUT_MP4
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"Outro successfully rendered to {OUTPUT_MP4}")
    
    # Clean up
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    if os.path.exists(AUDIO_PATH):
        os.remove(AUDIO_PATH)

if __name__ == "__main__":
    main()
