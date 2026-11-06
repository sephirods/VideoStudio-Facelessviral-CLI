#!/usr/bin/env python3
"""
Universal Real Photograph Fetcher & 2x2 Contact Grid Builder
1. Searches real photographs on Wikimedia Commons (using 1920px HD thumbnails for 5x speed)
   with automatic fallback to Pixabay Photos.
2. Filters out non-photographic noise (maps, diagrams, logos, coats of arms, charts, icons).
3. Integrates with content_deduplication.py (dHash + URL cooldown per channel group).
4. Builds a numbered 2x2 visual contact grid (candidates_grid.jpg) + clean hero_image.jpg.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
from PIL import Image, ImageDraw

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from content_deduplication import filter_candidate_images
except ImportError:
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from content_deduplication import filter_candidate_images
    except Exception:
        filter_candidate_images = None

USER_AGENT = "VideoStudio/1.1 (contact@videostudio.local)"

NON_PHOTO_KEYWORDS = (
    "map", "mapa", "locator", "location", "diagram", "diagrama", "chart", "graph",
    "coat of arms", "escudo", "logo", "flag", "bandera", "icon", "icono",
    "signature", "firma", "symbol", "silhouette", "silueta", "stamp",
    "drawing", "sketch", "cartoon", "illustration", "vector", "blank", "range"
)


def _is_clean_photo_title(title: str) -> bool:
    t_low = title.lower()
    return not any(bad in t_low for bad in NON_PHOTO_KEYWORDS)


def search_wikimedia(query: str, limit: int = 16) -> list[dict]:
    url = (
        f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
        f"&gsrsearch={urllib.parse.quote(query)}&gsrnamespace=6&gsrlimit={limit}"
        f"&prop=imageinfo&iiprop=url|size|mime&iiurlwidth=1920&format=json"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        results = []
        for _, page in pages.items():
            title = page.get("title", "").replace("File:", "")
            if not _is_clean_photo_title(title):
                continue
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            orig_url = info.get("url", "")
            dl_url = info.get("thumburl") or orig_url
            width = info.get("width", 0)
            height = info.get("height", 0)
            mime = info.get("mime", "").lower()

            ext = os.path.splitext(orig_url.split("?")[0])[1].lower()
            if (
                ext in [".jpg", ".jpeg", ".png", ".webp"]
                and "svg" not in mime
                and width >= 800
                and height >= 600
                and _is_clean_photo_title(orig_url)
            ):
                results.append({
                    "title": title,
                    "url": dl_url,
                    "original_url": orig_url,
                    "width": info.get("thumbwidth") or width,
                    "height": info.get("thumbheight") or height,
                    "pixels": width * height
                })
        results.sort(key=lambda x: x["pixels"], reverse=True)
        return results
    except Exception as e:
        print(f"[WARN] Error buscando en Wikimedia Commons: {e}", file=sys.stderr)
        return []


def search_pixabay_photos(query: str, limit: int = 12) -> list[dict]:
    creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "stock_credentials.json")
    if not os.path.exists(creds_path):
        return []
    try:
        with open(creds_path, "r", encoding="utf-8") as f:
            creds = json.load(f)
        keys = creds.get("pixabay_api_keys", [])
        if not keys or keys[0] == "TU_PIXABAY_API_KEY_AQUI":
            return []
        key = keys[0]
        url = f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(query)}&image_type=photo&per_page={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
        hits = data.get("hits", [])
        results = []
        for h in hits:
            tags = h.get("tags", "")
            if not _is_clean_photo_title(tags):
                continue
            dl_url = h.get("largeImageURL") or h.get("webformatURL")
            if not dl_url:
                continue
            results.append({
                "title": f"Pixabay {tags}",
                "url": dl_url,
                "original_url": dl_url,
                "width": h.get("imageWidth", 0),
                "height": h.get("imageHeight", 0),
                "pixels": h.get("imageWidth", 0) * h.get("imageHeight", 0)
            })
        results.sort(key=lambda x: x["pixels"], reverse=True)
        return results
    except Exception as e:
        print(f"[WARN] Error buscando en Pixabay Photos: {e}", file=sys.stderr)
        return []


def download_single_image(item: dict, dest_path: str) -> bool:
    req = urllib.request.Request(item["url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp, open(dest_path, "wb") as out:
            out.write(resp.read())
        with Image.open(dest_path) as img:
            img.verify()
        return True
    except Exception:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        return False


def create_contact_sheet(candidates: list[dict], grid_path: str) -> str:
    cell_w, cell_h = 600, 600
    grid = Image.new("RGB", (cell_w * 2, cell_h * 2), color=(20, 20, 20))
    draw = ImageDraw.Draw(grid)
    positions = [(0, 0), (cell_w, 0), (0, cell_h), (cell_w, cell_h)]

    for i, cand in enumerate(candidates[:4]):
        x, y = positions[i]
        try:
            with Image.open(cand["path"]) as img:
                img_thumb = img.convert("RGB")
                img_thumb.thumbnail((cell_w - 20, cell_h - 20), Image.Resampling.LANCZOS)

                offset_x = x + (cell_w - img_thumb.width) // 2
                offset_y = y + (cell_h - img_thumb.height) // 2
                grid.paste(img_thumb, (offset_x, offset_y))

                badge_text = f" [{i + 1}] "
                draw.rectangle([x + 15, y + 15, x + 120, y + 65], fill=(0, 0, 0), outline=(255, 230, 0), width=3)
                draw.text((x + 25, y + 25), badge_text, fill=(255, 255, 0))

                title_short = (cand["title"][:38] + "..") if len(cand["title"]) > 38 else cand["title"]
                draw.rectangle([x + 10, y + cell_h - 40, x + cell_w - 10, y + cell_h - 10], fill=(0, 0, 0))
                draw.text((x + 15, y + cell_h - 32), title_short, fill=(255, 255, 255))
        except Exception:
            draw.rectangle([x + 10, y + 10, x + cell_w - 10, y + cell_h - 10], fill=(50, 20, 20))
            draw.text((x + 30, y + 30), f"Error loading image {i + 1}", fill=(255, 100, 100))

    grid.save(grid_path, quality=90)
    return grid_path


def main():
    parser = argparse.ArgumentParser(description="Adquisicion multi-hilo de fotos reales HD y creacion de cuadricula 2x2")
    parser.add_argument("--query", required=True, help="Termino o sujeto a buscar")
    parser.add_argument("--output-dir", required=True, help="Directorio donde guardar las imagenes")
    parser.add_argument("--count", type=int, default=4, help="Cantidad de candidatos a descargar (default 4)")
    parser.add_argument("--select", type=int, default=None, help="Candidato a seleccionar como hero_image (1 a 4)")
    parser.add_argument("--channel", default=None, help="ID del canal para control de deduplicacion por grupo")
    parser.add_argument("--grid-only", action="store_true", help="Solo generar la cuadricula sin fijar hero_image")
    parser.add_argument("--cleanup-candidates", action="store_true", help="Borrar archivos individuales tras guardar hero_image y grid")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    candidates_dir = os.path.join(args.output_dir, "real_candidates")
    os.makedirs(candidates_dir, exist_ok=True)

    t0 = time.time()
    raw_results = search_wikimedia(args.query, limit=16)
    if len(raw_results) < args.count:
        pix_results = search_pixabay_photos(args.query, limit=12)
        raw_results.extend(pix_results)

    if not raw_results:
        print(json.dumps({"success": False, "error": f"No se encontraron imagenes reales para: {args.query}"}, ensure_ascii=False))
        sys.exit(1)

    # Download at most count + 2 (buffer in case one URL fails), then remove unused extras
    selected_for_download = raw_results[:args.count + 2]

    def _task(idx_item):
        idx, item = idx_item
        ext = os.path.splitext(item["url"].split("?")[0])[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        dest_path = os.path.join(candidates_dir, f"candidate_{idx + 1:02d}{ext}")
        if download_single_image(item, dest_path):
            return {
                "index": idx + 1,
                "title": item["title"],
                "width": item["width"],
                "height": item["height"],
                "path": os.path.abspath(dest_path),
                "url": item.get("original_url") or item["url"]
            }
        return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        results_all = [r for r in executor.map(_task, enumerate(selected_for_download)) if r]

    downloaded_candidates = results_all[:args.count]
    # Remove any extra buffer downloads immediately
    for extra in results_all[args.count:]:
        try:
            os.remove(extra["path"])
        except OSError:
            pass

    for idx, c in enumerate(downloaded_candidates):
        c["index"] = idx + 1

    if not downloaded_candidates:
        print(json.dumps({"success": False, "error": "Fallo la descarga de todos los candidatos"}, ensure_ascii=False))
        sys.exit(1)

    grid_path = os.path.join(args.output_dir, "candidates_grid.jpg")
    create_contact_sheet(downloaded_candidates, grid_path)

    chosen_idx = 1
    dedup_info = None
    if filter_candidate_images and args.channel:
        dedup_info = filter_candidate_images(downloaded_candidates, channel_id=args.channel)
        if args.select is None:
            chosen_idx = dedup_info.get("selected_index", 1)
        else:
            chosen_idx = max(1, min(args.select, len(downloaded_candidates)))
    elif args.select is not None:
        chosen_idx = max(1, min(args.select, len(downloaded_candidates)))

    hero_path = None
    if not args.grid_only:
        chosen_candidate = downloaded_candidates[chosen_idx - 1]
        hero_path = os.path.join(args.output_dir, "hero_image.jpg")
        with Image.open(chosen_candidate["path"]) as img:
            img.convert("RGB").save(hero_path, quality=95)

    if args.cleanup_candidates and hero_path:
        shutil.rmtree(candidates_dir, ignore_errors=True)

    elapsed = time.time() - t0
    report = {
        "success": True,
        "query": args.query,
        "elapsed_seconds": round(elapsed, 2),
        "candidates_count": len(downloaded_candidates),
        "grid_path": os.path.abspath(grid_path),
        "hero_image": os.path.abspath(hero_path) if hero_path else None,
        "selected_index": chosen_idx,
        "deduplication": dedup_info,
        "candidates": downloaded_candidates
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
