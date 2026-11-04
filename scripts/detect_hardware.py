#!/usr/bin/env python3
"""
CLI Doctor: Auto-detection of Hardware & Video Encoders
Dynamically analyzes CPU cores and GPU VRAM to determine the exact optimal
video encoder and safe concurrency limit for this specific machine.
Persists configuration into config/hardware.json.
"""
import subprocess
import json
import os
import sys

def detect_encoder():
    print("Auditando hardware del sistema y capacidades de codificación de video...")
    
    cpu_cores = os.cpu_count() or 4
    selected_encoder = "libx264"
    hardware_type = "cpu"
    gpu_name = "N/A"
    gpu_vram_mb = 0
    concurrency = 1
    preset = "fast"

    # 1. Auditar GPU NVIDIA via nvidia-smi con VRAM
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True
        )
        lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
        if lines:
            parts = [p.strip() for p in lines[0].split(",")]
            gpu_name = parts[0]
            if len(parts) > 1 and parts[1].isdigit():
                gpu_vram_mb = int(parts[1])

            hardware_type = "nvidia"
            selected_encoder = "h264_nvenc"
            preset = "p4"

            # Cálculo dinámico de concurrencia según VRAM y límites de sesión de driver
            # Cada sesión 1080x1920 @60fps consume ~1.2-1.5 GB VRAM
            if gpu_vram_mb >= 16000:
                concurrency = 5  # Límite máximo de sesiones GeForce
            elif gpu_vram_mb >= 8000:
                concurrency = 4  # Óptimo para 8GB (RTX 3070 / 4060): ~5.5 GB VRAM en uso
            elif gpu_vram_mb >= 4000:
                concurrency = 2  # Óptimo para 4-6GB (GTX 1650 / RTX 3050)
            else:
                concurrency = 1

            print(f"-> GPU NVIDIA detectada: {gpu_name} ({gpu_vram_mb} MB VRAM)")
            print(f"-> Encoder: {selected_encoder} | Concurrencia segura calculada: x{concurrency}")
            return {
                "hardware_type": hardware_type,
                "gpu_name": gpu_name,
                "gpu_vram_mb": gpu_vram_mb,
                "cpu_cores": cpu_cores,
                "video_encoder": selected_encoder,
                "max_concurrency": concurrency,
                "ffmpeg_preset": preset,
                "status": "ready"
            }
    except Exception:
        pass

    # 2. Auditar otros encoders de FFmpeg (AMD AMF, Apple VideoToolbox)
    try:
        ffmpeg_res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        output = ffmpeg_res.stdout
        if "h264_amf" in output:
            selected_encoder = "h264_amf"
            hardware_type = "amd"
            concurrency = 2  # AMD AMF es más sensible a concurrencia alta
            preset = "speed"
            print("-> GPU AMD detectada (AMF). Concurrencia calculada: x2")
        elif "h264_videotoolbox" in output:
            selected_encoder = "h264_videotoolbox"
            hardware_type = "apple_silicon"
            concurrency = 3
            preset = "default"
            print("-> Apple Silicon detectado (VideoToolbox). Concurrencia calculada: x3")
        else:
            selected_encoder = "libx264"
            hardware_type = "cpu"
            preset = "fast"
            # En CPU, se calcula según los núcleos para no congelar el equipo
            if cpu_cores >= 8:
                concurrency = 2
            else:
                concurrency = 1
            print(f"-> Sin GPU acelerada. CPU ({cpu_cores} núcleos) detectada. Concurrencia segura: x{concurrency}")
    except Exception as e:
        print(f"Error comprobando FFmpeg: {e}")

    return {
        "hardware_type": hardware_type,
        "gpu_name": gpu_name,
        "gpu_vram_mb": gpu_vram_mb,
        "cpu_cores": cpu_cores,
        "video_encoder": selected_encoder,
        "max_concurrency": concurrency,
        "ffmpeg_preset": preset,
        "status": "ready"
    }

def main():
    config = detect_encoder()
    out_dir = r"c:\ganar dinero\config"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "hardware.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"Configuración de hardware guardada dinámicamente en: {out_path}")

if __name__ == "__main__":
    main()
