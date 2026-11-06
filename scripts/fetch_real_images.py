import os
import sys
import json
import urllib.request
import urllib.parse
import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

# Import deduplication module
try:
    from content_deduplication import filter_candidate_images
except ImportError:
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from content_deduplication import filter_candidate_images
    except Exception:
        filter_candidate_images = None

USER_AGENT = "VideoStudio/1.0 (contact@videostudio.local)"

def search_wikimedia(query, limit=10):
    url = (
        f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
        f"&gsrsearch={urllib.parse.quote(query)}&gsrnamespace=6&gsrlimit={limit}"
        f"&prop=imageinfo&iiprop=url|size|mime&format=json"
    )
    headers = {"User-Agent": USER_AGENT}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        results = []
        for pid, page in pages.items():
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            url = info.get("url", "")
            width = info.get("width", 0)
            height = info.get("height", 0)
            mime = info.get("mime", "")
            
            # Filter only standard photograph formats (no vector/audio/pdf)
            ext = os.path.splitext(url.split("?")[0])[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".webp"] and width >= 800 and height >= 600:
                results.append({
                    "title": page.get("title", "").replace("File:", ""),
                    "url": url,
                    "width": width,
                    "height": height,
                    "pixels": width * height
                })
        # Sort by total pixel resolution (highest quality first)
        results.sort(key=lambda x: x["pixels"], reverse=True)
        return results
    except Exception as e:
        print(f"[WARN] Error buscando en Wikimedia Commons: {e}", file=sys.stderr)
        return []

def search_pixabay_photos(query, limit=10):
    # Fallback to Pixabay photos if configured
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
            results.append({
                "title": f"Pixabay {h.get('tags', '')}",
                "url": h.get("largeImageURL") or h.get("webformatURL"),
                "width": h.get("imageWidth", 0),
                "height": h.get("imageHeight", 0),
                "pixels": h.get("imageWidth", 0) * h.get("imageHeight", 0)
            })
        results.sort(key=lambda x: x["pixels"], reverse=True)
        return results
    except Exception as e:
        print(f"[WARN] Error buscando en Pixabay Photos: {e}", file=sys.stderr)
        return []

def download_single_image(item, dest_path):
    headers = {"User-Agent": USER_AGENT}
    req = urllib.request.Request(item["url"], headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp, open(dest_path, "wb") as out:
            out.write(resp.read())
        # Validate with PIL
        with Image.open(dest_path) as img:
            img.verify()
        return True
    except Exception as e:
        if os.path.exists(dest_path):
            try: os.remove(dest_path)
            except: pass
        return False

def create_contact_sheet(candidates, grid_path):
    # 2x2 grid (1200x1200 px total, 600x600 per cell)
    cell_w, cell_h = 600, 600
    grid = Image.new("RGB", (cell_w * 2, cell_h * 2), color=(20, 20, 20))
    draw = ImageDraw.Draw(grid)
    
    positions = [(0, 0), (cell_w, 0), (0, cell_h), (cell_w, cell_h)]
    
    for i, cand in enumerate(candidates[:4]):
        x, y = positions[i]
        try:
            with Image.open(cand["path"]) as img:
                img_rgb = img.convert("RGB")
                # Fit into cell keeping aspect ratio
                img_thumb = img_rgb.copy()
                img_thumb.thumbnail((cell_w - 20, cell_h - 20), Image.Resampling.LANCZOS)
                
                # Center inside cell
                offset_x = x + (cell_w - img_thumb.width) // 2
                offset_y = y + (cell_h - img_thumb.height) // 2
                grid.paste(img_thumb, (offset_x, offset_y))
                
                # Draw high-contrast badge: [1], [2], etc.
                badge_text = f" [{i+1}] "
                # Draw background box for badge
                draw.rectangle([x + 15, y + 15, x + 120, y + 65], fill=(0, 0, 0, 220), outline=(255, 230, 0), width=3)
                draw.text((x + 25, y + 25), badge_text, fill=(255, 255, 0))
                
                # Title snippet
                title_short = (cand["title"][:35] + "..") if len(cand["title"]) > 35 else cand["title"]
                draw.rectangle([x + 10, y + cell_h - 40, x + cell_w - 10, y + cell_h - 10], fill=(0, 0, 0, 200))
                draw.text((x + 15, y + cell_h - 32), title_short, fill=(255, 255, 255))
        except Exception as e:
            draw.rectangle([x + 10, y + 10, x + cell_w - 10, y + cell_h - 10], fill=(50, 20, 20))
            draw.text((x + 30, y + 30), f"Error loading image {i+1}", fill=(255, 100, 100))

    grid.save(grid_path, quality=90)
    return grid_path

def main():
    parser = argparse.ArgumentParser(description="Adquisicion multi-hilo de fotos reales y creacion de cuadricula 2x2")
    parser.add_argument("--query", required=True, help="Termino o sujeto a buscar")
    parser.add_argument("--output-dir", required=True, help="Directorio donde guardar las imagenes")
    parser.add_argument("--count", type=int, default=4, help="Cantidad de candidatos a descargar (default 4)")
    parser.add_argument("--select", type=int, default=None, help="Candidato a seleccionar como hero_image (1 a 4). Si se omite, se usa deduplicación automática.")
    parser.add_argument("--channel", default=None, help="ID del canal para control de deduplicación por grupo")
    parser.add_argument("--grid-only", action="store_true", help="Solo generar la cuadricula sin fijar hero_image")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    candidates_dir = os.path.join(args.output_dir, "real_candidates")
    os.makedirs(candidates_dir, exist_ok=True)

    t0 = time.time()
    # 1. Búsqueda multi-fuente universal
    raw_results = search_wikimedia(args.query, limit=12)
    if len(raw_results) < args.count:
        pix_results = search_pixabay_photos(args.query, limit=12)
        raw_results.extend(pix_results)

    if not raw_results:
        print(json.dumps({"success": False, "error": f"No se encontraron imagenes para: {args.query}"}))
        sys.exit(1)

    # 2. Descarga paralela en 4 hilos
    selected_for_download = raw_results[:args.count * 2]
    downloaded_candidates = []

    def _task(idx_item):
        idx, item = idx_item
        ext = os.path.splitext(item["url"].split("?")[0])[1].lower() or ".jpg"
        dest_filename = f"candidate_{idx+1:02d}{ext}"
        dest_path = os.path.join(candidates_dir, dest_filename)
        ok = download_single_image(item, dest_path)
        if ok:
            return {
                "index": idx + 1,
                "title": item["title"],
                "width": item["width"],
                "height": item["height"],
                "path": os.path.abspath(dest_path),
                "url": item["url"]
            }
        return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = executor.map(_task, enumerate(selected_for_download))
        for res in futures:
            if res and len(downloaded_candidates) < args.count:
                downloaded_candidates.append(res)

    if not downloaded_candidates:
        print(json.dumps({"success": False, "error": "Fallo la descarga de todos los candidatos"}))
        sys.exit(1)

    # 3. Crear hoja de contacto / collage 2x2
    grid_path = os.path.join(args.output_dir, "candidates_grid.jpg")
    create_contact_sheet(downloaded_candidates, grid_path)

    # 4. Evaluación de deduplicación y selección de hero_image
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
        # Save as clean JPEG
        with Image.open(chosen_candidate["path"]) as img:
            img.convert("RGB").save(hero_path, quality=95)

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
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
