#!/usr/bin/env python3
"""
Storage Management, LRU Cache Trimmer & Publication Archiver
1. Packages approved deliverables into the official channel folder structure:
   videos/publicaciones/[CANAL]/[YYYY-MM-DD]_[slug]/
   generating copy_publicacion.txt and package_manifest.json.
2. Registers the publication in config/history/publication_history.json (30-day topic & dHash cooldown).
3. Archives approved stock clips into assets/b-roll/<category>/.
4. Enforces automatic disk hygiene:
   - Purges C:\\MoneyPrinterTurbo\\storage\\local_videos
   - Purges orphaned task folders in C:\\MoneyPrinterTurbo\\storage\\tasks
   - Purges temporary test folders (videos/test_*) and real_candidates/
   - Enforces an automatic 1.5 GB (1500 MB) LRU cap on C:\\MoneyPrinterTurbo\\storage\\cache_videos.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import glob
import json
import os
import re
import shutil
import sys
import time

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from content_deduplication import register_publication
except ImportError:
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from content_deduplication import register_publication
    except Exception:
        register_publication = None

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VIDEOS_DIR = os.path.join(WORKSPACE, "videos")
PUBLICACIONES_DIR = os.path.join(VIDEOS_DIR, "publicaciones")
BROLL_DIR = os.path.join(WORKSPACE, "assets", "b-roll")
ENGINE_STORAGE = (
    r"C:\MoneyPrinterTurbo\storage"
    if sys.platform.startswith("win")
    else "/opt/MoneyPrinterTurbo/storage"
)

os.makedirs(PUBLICACIONES_DIR, exist_ok=True)
os.makedirs(BROLL_DIR, exist_ok=True)


def _slugify(text: str) -> str:
    t = text.lower().strip()
    for src, dst in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        t = t.replace(src, dst)
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t[:45] or "video_viral"


def _dir_size_bytes(path: str) -> int:
    total = 0
    if not os.path.exists(path):
        return 0
    for root, _, files in os.walk(path):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def organize_run_into_publication(
    run_dir: str,
    channel: str | None = None,
    slug: str | None = None,
    category: str | None = None,
    video_override: str | None = None,
    thumbnail_override: str | None = None,
) -> dict | None:
    """Packages a completed pipeline run into videos/publicaciones/[CANAL]/[YYYY-MM-DD]_[slug]/."""
    if not os.path.exists(run_dir):
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")

    script_path = os.path.join(run_dir, "video_script.json")
    qa_path = os.path.join(run_dir, "qa_certificate.json")
    meta_path = os.path.join(run_dir, "viral_metadata.json")
    legacy_pkg_path = os.path.join(run_dir, "viral_packaging.json")
    render_manifest_path = os.path.join(run_dir, "render_manifest.json")
    bench_path = os.path.join(run_dir, "benchmarks.json")

    sdata = {}
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            sdata = json.load(f)

    pkg = {}
    active_meta_file = meta_path if os.path.exists(meta_path) else (legacy_pkg_path if os.path.exists(legacy_pkg_path) else None)
    if active_meta_file:
        with open(active_meta_file, "r", encoding="utf-8") as f:
            pkg = json.load(f)

    # Resolve channel ID
    ch_id = channel or sdata.get("channel") or pkg.get("channel")
    if not ch_id:
        channels_cfg = os.path.join(WORKSPACE, "config", "channels.json")
        if os.path.exists(channels_cfg):
            try:
                with open(channels_cfg, "r", encoding="utf-8") as cf:
                    cdata = json.load(cf)
                ch_id = cdata.get("active_default_channel")
            except Exception:
                pass
    ch_id = _slugify(ch_id or "modo_prueba")

    # Resolve slug
    if not slug:
        base_name = os.path.basename(os.path.abspath(run_dir))
        cleaned = re.sub(r"^(run_\d+_|auto_\d+_\d+|demo_\d+_\d+|test_run_)", "", base_name).strip("_")
        slug = _slugify(cleaned or pkg.get("primary_title") or sdata.get("topic") or "video")
    else:
        slug = _slugify(slug)

    today_str = datetime.now().strftime("%Y-%m-%d")
    pub_dir = os.path.join(PUBLICACIONES_DIR, ch_id, f"{today_str}_{slug}")
    os.makedirs(pub_dir, exist_ok=True)

    # Resolve video & thumbnail paths
    rm_video = None
    if os.path.exists(render_manifest_path):
        try:
            with open(render_manifest_path, "r", encoding="utf-8") as rmf:
                rm_video = json.load(rmf).get("output_video")
        except Exception:
            pass

    video_candidates = [
        video_override,
        os.path.join(run_dir, "video_final.mp4"),
        rm_video,
        pkg.get("video_path"),
    ]
    src_video = next((p for p in video_candidates if p and os.path.exists(p)), None)

    thumb_manifest_path = os.path.join(run_dir, "thumbnail_manifest.json")
    tm_thumb = None
    if os.path.exists(thumb_manifest_path):
        try:
            with open(thumb_manifest_path, "r", encoding="utf-8") as tmf:
                tm_thumb = json.load(tmf).get("thumbnail_path")
        except Exception:
            pass

    thumb_candidates = [
        thumbnail_override,
        os.path.join(run_dir, "miniatura_viral.jpg"),
        tm_thumb,
        pkg.get("thumbnail_path"),
    ]
    src_thumb = next((p for p in thumb_candidates if p and os.path.exists(p)), None)

    dest_video = os.path.join(pub_dir, "video_final.mp4")
    dest_thumb = os.path.join(pub_dir, "miniatura_viral.jpg")
    dest_copy = os.path.join(pub_dir, "copy_publicacion.txt")

    if src_video and os.path.abspath(src_video) != os.path.abspath(dest_video):
        shutil.copy2(src_video, dest_video)
    if src_thumb and os.path.abspath(src_thumb) != os.path.abspath(dest_thumb):
        shutil.copy2(src_thumb, dest_thumb)

    if active_meta_file:
        shutil.copy2(active_meta_file, os.path.join(pub_dir, "viral_metadata.json"))
    if os.path.exists(qa_path):
        shutil.copy2(qa_path, os.path.join(pub_dir, "qa_certificate.json"))
    if os.path.exists(render_manifest_path):
        shutil.copy2(render_manifest_path, os.path.join(pub_dir, "render_manifest.json"))
    if os.path.exists(bench_path):
        shutil.copy2(bench_path, os.path.join(pub_dir, "datos_produccion.json"))

    # Generate copy_publicacion.txt
    primary_title = pkg.get("primary_title") or pkg.get("title") or sdata.get("topic", "")
    raw_desc = pkg.get("description", "").replace("\\n", "\n").strip()
    pinned = pkg.get("pinned_comment", "")
    all_tags = pkg.get("tags", []) or (pkg.get("niche_tags", []) + pkg.get("universal_tags", []))
    tags_str = " ".join(t if str(t).startswith("#") else f"#{t}" for t in all_tags)

    copy_text = (
        "============================================================\n"
        f"TITULO PRINCIPAL (<70 chars):\n{primary_title}\n"
        "============================================================\n\n"
        f"DESCRIPCIÓN:\n{raw_desc}\n\n"
        "============================================================\n"
        f"COMENTARIO FIJADO (PINNED COMMENT):\n{pinned}\n\n"
        "============================================================\n"
        f"HASHTAGS / ETIQUETAS:\n{tags_str}\n"
        "============================================================\n"
    )
    with open(dest_copy, "w", encoding="utf-8") as f:
        f.write(copy_text)

    # Register in 30-day deduplication & cooldown history
    if register_publication:
        try:
            top_name = sdata.get("topic") or primary_title or slug
            hero_img = os.path.join(run_dir, "hero_image.jpg")
            img_for_hash = hero_img if os.path.exists(hero_img) else (dest_thumb if os.path.exists(dest_thumb) else None)
            register_publication(
                channel_id=ch_id,
                topic=top_name,
                keywords=top_name,
                image_path=img_for_hash,
                thumbnail_path=dest_thumb if os.path.exists(dest_thumb) else None,
                video_path=dest_video if os.path.exists(dest_video) else None
            )
        except Exception as e:
            print(f"[WARN] Error registrando en historial: {e}", file=sys.stderr)

    # Archive approved B-roll clips & remove temporary candidate photos
    approved_path = os.path.join(run_dir, "approved_materials.json")
    broll_cat = _slugify(category or sdata.get("niche") or ch_id or "general")
    if os.path.exists(approved_path):
        cat_dir = os.path.join(BROLL_DIR, broll_cat)
        os.makedirs(cat_dir, exist_ok=True)
        with open(approved_path, "r", encoding="utf-8") as f:
            app_data = json.load(f)
        for clip in app_data.get("approved_clips", []):
            # Skip synthetic Ken Burns hero_clip when archiving reusable stock footage
            if os.path.exists(clip) and "hero_clip" not in os.path.basename(clip).lower():
                dest_clip = os.path.join(cat_dir, os.path.basename(clip))
                if not os.path.exists(dest_clip):
                    shutil.copy2(clip, dest_clip)

    shutil.rmtree(os.path.join(run_dir, "real_candidates"), ignore_errors=True)

    package_manifest = {
        "channel": ch_id,
        "slug": slug,
        "publication_folder": pub_dir,
        "video_path": dest_video if os.path.exists(dest_video) else None,
        "thumbnail_path": dest_thumb if os.path.exists(dest_thumb) else None,
        "copy_path": dest_copy,
        "metadata_path": os.path.join(pub_dir, "viral_metadata.json") if active_meta_file else None,
        "qa_certificate_path": os.path.join(pub_dir, "qa_certificate.json") if os.path.exists(qa_path) else None,
        "packaged_at": datetime.now().isoformat(),
        "status": "ready_for_distribution"
    }
    manifest_out = os.path.join(pub_dir, "package_manifest.json")
    with open(manifest_out, "w", encoding="utf-8") as mf:
        json.dump(package_manifest, mf, indent=2, ensure_ascii=False)

    print(f"[OK] Publication packaged: {pub_dir}")
    return package_manifest


def purge_redundant_storage(
    max_cache_mb: float = 1500.0,
    task_max_age_minutes: float = 15.0,
    purge_test_dirs: bool = True,
) -> dict:
    """
    Cleans redundant storage:
    1. Empties storage/local_videos
    2. Deletes orphaned storage/tasks/* older than `task_max_age_minutes`
    3. Removes temporary videos/test_* directories if `purge_test_dirs` is True
    4. Trims storage/cache_videos via LRU (oldest modified first) down to `max_cache_mb` (default 1500 MB / 1.5 GB)
    """
    freed_local = 0
    freed_tasks = 0
    freed_tests = 0
    freed_cache = 0
    now = time.time()

    # 1. local_videos
    local_videos_dir = os.path.join(ENGINE_STORAGE, "local_videos")
    if os.path.exists(local_videos_dir):
        for entry in glob.glob(os.path.join(local_videos_dir, "*")):
            try:
                if os.path.isfile(entry):
                    sz = os.path.getsize(entry)
                    os.remove(entry)
                    freed_local += sz
                elif os.path.isdir(entry):
                    sz = _dir_size_bytes(entry)
                    shutil.rmtree(entry, ignore_errors=True)
                    freed_local += sz
            except OSError:
                pass

    # 2. Orphaned storage/tasks/*
    tasks_dir = os.path.join(ENGINE_STORAGE, "tasks")
    if os.path.exists(tasks_dir):
        cutoff = now - (task_max_age_minutes * 60.0)
        for t_folder in glob.glob(os.path.join(tasks_dir, "*")):
            try:
                mtime = os.path.getmtime(t_folder)
                if mtime <= cutoff:
                    sz = _dir_size_bytes(t_folder) if os.path.isdir(t_folder) else os.path.getsize(t_folder)
                    if os.path.isdir(t_folder):
                        shutil.rmtree(t_folder, ignore_errors=True)
                    else:
                        os.remove(t_folder)
                    freed_tasks += sz
            except OSError:
                pass

    # 3. Temporary videos/test_* folders
    if purge_test_dirs and os.path.exists(VIDEOS_DIR):
        for test_p in glob.glob(os.path.join(VIDEOS_DIR, "test_*")):
            try:
                sz = _dir_size_bytes(test_p) if os.path.isdir(test_p) else os.path.getsize(test_p)
                if os.path.isdir(test_p):
                    shutil.rmtree(test_p, ignore_errors=True)
                else:
                    os.remove(test_p)
                freed_tests += sz
            except OSError:
                pass

    # 4. LRU cap on storage/cache_videos (1.5 GB = 1500 MB default)
    cache_dirs_to_check = [
        os.path.join(WORKSPACE, "storage", "cache_videos"),
    ]
    if ENGINE_STORAGE and os.path.exists(os.path.join(ENGINE_STORAGE, "cache_videos")):
        if os.path.abspath(os.path.join(ENGINE_STORAGE, "cache_videos")) != os.path.abspath(os.path.join(WORKSPACE, "storage", "cache_videos")):
            cache_dirs_to_check.append(os.path.join(ENGINE_STORAGE, "cache_videos"))

    remaining_cache_bytes = 0
    for cache_dir in cache_dirs_to_check:
        if os.path.exists(cache_dir) and max_cache_mb >= 0:
            max_bytes = int(max_cache_mb * 1024 * 1024)
            files_info = []
            total_bytes = 0
            for root, _, files in os.walk(cache_dir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    try:
                        st = os.stat(fp)
                        files_info.append((st.st_mtime, st.st_size, fp))
                        total_bytes += st.st_size
                    except OSError:
                        pass

            if total_bytes > max_bytes:
                # Sort oldest first (LRU eviction)
                files_info.sort(key=lambda x: x[0])
                for _, sz, fp in files_info:
                    if total_bytes <= max_bytes:
                        break
                    try:
                        os.remove(fp)
                        total_bytes -= sz
                        freed_cache += sz
                    except OSError:
                        pass
            remaining_cache_bytes += total_bytes

    total_freed_mb = round((freed_local + freed_tasks + freed_tests + freed_cache) / (1024 * 1024), 2)
    summary = {
        "freed_total_mb": total_freed_mb,
        "freed_local_videos_mb": round(freed_local / (1024 * 1024), 2),
        "freed_orphan_tasks_mb": round(freed_tasks / (1024 * 1024), 2),
        "freed_test_dirs_mb": round(freed_tests / (1024 * 1024), 2),
        "freed_lru_cache_mb": round(freed_cache / (1024 * 1024), 2),
        "remaining_cache_videos_mb": round(remaining_cache_bytes / (1024 * 1024), 2),
        "cache_cap_mb": max_cache_mb
    }
    print(
        f"[STORAGE] Freed {total_freed_mb} MB "
        f"(cache_videos now {summary['remaining_cache_videos_mb']} MB / {max_cache_mb} MB cap)."
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description="Package approved video runs & enforce 1.5 GB LRU storage hygiene.")
    parser.add_argument("--run-dir", default=None, help="Pipeline run directory to package")
    parser.add_argument("--channel", default=None, help="Channel ID (e.g. mente_oculta)")
    parser.add_argument("--slug", default=None, help="Short slug for publication folder")
    parser.add_argument("--category", default=None, help="B-Roll archive category")
    parser.add_argument("--video-path", default=None, help="Explicit final video MP4 path")
    parser.add_argument("--thumbnail-path", default=None, help="Explicit viral thumbnail JPG path")
    parser.add_argument("--max-cache-mb", type=float, default=1500.0, help="LRU cap in MB for cache_videos (default: 1500)")
    parser.add_argument("--task-max-age-minutes", type=float, default=15.0, help="Delete storage/tasks older than N minutes (default: 15)")
    parser.add_argument("--keep-tests", action="store_true", help="Keep videos/test_* folders")
    parser.add_argument("--purge-only", action="store_true", help="Only run storage purge without packaging a run")
    args = parser.parse_args()

    result = {}
    if args.run_dir and not args.purge_only:
        pkg_manifest = organize_run_into_publication(
            run_dir=args.run_dir,
            channel=args.channel,
            slug=args.slug,
            category=args.category,
            video_override=args.video_path,
            thumbnail_override=args.thumbnail_path,
        )
        result["package_manifest"] = pkg_manifest

    storage_summary = purge_redundant_storage(
        max_cache_mb=args.max_cache_mb,
        task_max_age_minutes=args.task_max_age_minutes,
        purge_test_dirs=not args.keep_tests,
    )
    result["storage_cleanup"] = storage_summary
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
