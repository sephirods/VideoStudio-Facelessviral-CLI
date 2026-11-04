#!/usr/bin/env python3
"""
Storage Management & Archive Organizer for Video Production
1. Organizes finished videos into standalone publication folders:
   videos/publicaciones/YYYY-MM-DD_<slug>/
2. Copies approved high-quality clips into a categorized local B-roll library:
   assets/b-roll/<categoria>/
3. Cleans up redundant temporary files (local_videos duplicates, old task caches).
"""
import os
import shutil
import json
import glob
from datetime import datetime

WORKSPACE = r"c:\ganar dinero"
VIDEOS_DIR = os.path.join(WORKSPACE, "videos")
PUBLICACIONES_DIR = os.path.join(VIDEOS_DIR, "publicaciones")
BROLL_DIR = os.path.join(WORKSPACE, "assets", "b-roll")
ENGINE_STORAGE = r"C:\MoneyPrinterTurbo\storage"

os.makedirs(PUBLICACIONES_DIR, exist_ok=True)
os.makedirs(BROLL_DIR, exist_ok=True)


def organize_run_into_publication(run_dir: str, category: str):
    """Packages a completed pipeline run into a clean publication folder."""
    if not os.path.exists(run_dir):
        return

    script_path = os.path.join(run_dir, "video_script.json")
    qa_path = os.path.join(run_dir, "qa_certificate.json")
    pkg_path = os.path.join(run_dir, "viral_packaging.json")
    bench_path = os.path.join(run_dir, "benchmarks.json")

    run_name = os.path.basename(run_dir)
    # Extract slug
    slug = run_name.replace("run_", "").replace("001_", "").replace("002_", "").replace("003_", "").replace("004_", "")
    
    # Target publication directory
    today_str = datetime.now().strftime("%Y-%m-%d")
    pub_dir = os.path.join(PUBLICACIONES_DIR, f"{today_str}_{slug}")
    os.makedirs(pub_dir, exist_ok=True)

    # Copy packaging json & create copy_publicacion.txt
    if os.path.exists(pkg_path):
        with open(pkg_path, "r", encoding="utf-8") as f:
            pkg = json.load(f)

        copy_text = f"""=== METADATOS DE PUBLICACIÓN ===
TÍTULO:
{pkg.get('primary_title', '')}

DESCRIPCIÓN:
{pkg.get('description', '')}

COMENTARIO FIJADO:
{pkg.get('pinned_comment', '')}

HASHTAGS / ETIQUETAS:
{', '.join(pkg.get('tags', []))}
"""
        with open(os.path.join(pub_dir, "copy_publicacion.txt"), "w", encoding="utf-8") as f:
            f.write(copy_text)

        # Copy video and thumbnail
        v_path = pkg.get("video_path")
        if v_path and os.path.exists(v_path):
            shutil.copy2(v_path, os.path.join(pub_dir, "video_final.mp4"))

        t_path = pkg.get("thumbnail_path")
        if t_path and os.path.exists(t_path):
            shutil.copy2(t_path, os.path.join(pub_dir, "miniatura_viral.jpg"))

    if os.path.exists(qa_path):
        shutil.copy2(qa_path, os.path.join(pub_dir, "qa_report.json"))

    if os.path.exists(bench_path):
        shutil.copy2(bench_path, os.path.join(pub_dir, "datos_produccion.json"))

    print(f"Publication packaged: {pub_dir}")

    # Copy approved clips to B-roll category
    approved_path = os.path.join(run_dir, "approved_materials.json")
    if os.path.exists(approved_path):
        cat_dir = os.path.join(BROLL_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)
        with open(approved_path, "r", encoding="utf-8") as f:
            app_data = json.load(f)
        for clip in app_data.get("approved_clips", []):
            if os.path.exists(clip):
                dest_clip = os.path.join(cat_dir, os.path.basename(clip))
                if not os.path.exists(dest_clip):
                    shutil.copy2(clip, dest_clip)
        print(f"Archived approved clips into: {cat_dir}")


def purge_redundant_storage():
    """Removes temporary duplicate files in local_videos and old task temp files."""
    local_videos_dir = os.path.join(ENGINE_STORAGE, "local_videos")
    freed_bytes = 0

    if os.path.exists(local_videos_dir):
        for f in glob.glob(os.path.join(local_videos_dir, "*")):
            try:
                sz = os.path.getsize(f)
                os.remove(f)
                freed_bytes += sz
            except Exception:
                pass

    print(f"Freed {freed_bytes / (1024 * 1024):.2f} MB of duplicate temp files in local_videos.")
    return freed_bytes


if __name__ == "__main__":
    # 1. Organize run_004 (Espacio Exterior)
    organize_run_into_publication(
        os.path.join(WORKSPACE, "pipeline_runs", "run_004_espacio_exterior"),
        category="espacio"
    )

    # 2. Organize run_003 (Por qué el mar es salado)
    organize_run_into_publication(
        os.path.join(WORKSPACE, "pipeline_runs", "run_003_mar_salado"),
        category="oceano"
    )

    # 3. Clean redundant duplicate cache
    purge_redundant_storage()
