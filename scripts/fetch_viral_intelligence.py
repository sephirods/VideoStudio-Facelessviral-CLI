#!/usr/bin/env python3
"""
Parallel Viral Market Intelligence Extractor (Pilar 2)
Extrae datos reales del mercado en paralelo (yt-dlp + YouTube Autocomplete simultáneos):
1. Espía videos y Shorts de la competencia con más vistas vía yt-dlp.
2. Extrae consultas de búsqueda reales en vivo desde YouTube Autocomplete API.
3. Extrae palabras clave y patrones con mayor volumen en español o inglés.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
import time
import urllib.parse
import urllib.request

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

STOP_WORDS = {
    "por", "que", "de", "el", "la", "los", "las", "en", "un", "una", "y", "a", "al", "del", "es",
    "para", "con", "sin", "como", "mas", "este", "esta", "shorts", "short", "video", "videos",
    "the", "and", "for", "that", "this", "with", "from", "your", "what", "why", "how", "are", "was"
}


def fetch_competitor_shorts(topic: str, max_results: int = 5) -> list:
    """Busca en YouTube los Shorts y videos más vistos sobre el tema usando yt-dlp (módulo o CLI)."""
    query = f"{topic} shorts"
    try:
        import yt_dlp
        ydl_opts = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
            "skip_download": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            entries = res.get("entries", [])
    except ImportError:
        import shutil
        import subprocess
        ytdlp_bin = shutil.which("yt-dlp") or r"C:\Python314\Scripts\yt-dlp.exe"
        if not os.path.exists(ytdlp_bin) and not shutil.which("yt-dlp"):
            return []
        try:
            proc = subprocess.run(
                [ytdlp_bin, "--flat-playlist", "-J", "--no-warnings", f"ytsearch{max_results}:{query}"],
                capture_output=True, text=True, timeout=12
            )
            entries = json.loads(proc.stdout).get("entries", []) if proc.returncode == 0 and proc.stdout else []
        except Exception:
            return []
    except Exception as e:
        print(f"Aviso al extraer competidores con yt-dlp: {e}", file=sys.stderr)
        return []

    results = []
    for e in entries:
        if not e:
            continue
        results.append({
            "title": e.get("title", ""),
            "view_count": e.get("view_count", 0),
            "url": e.get("url", ""),
            "channel": e.get("uploader") or e.get("channel", "")
        })
    results.sort(key=lambda x: (x["view_count"] or 0), reverse=True)
    return results


def _fetch_single_suggest(seed: str, lang: str) -> list[str]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        encoded = urllib.parse.quote(seed)
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl={lang}&q={encoded}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if len(data) > 1 and isinstance(data[1], list):
                return [item for item in data[1] if isinstance(item, str)]
    except Exception as e:
        print(f"Aviso al consultar YouTube Autocomplete para '{seed}': {e}", file=sys.stderr)
    return []


def fetch_youtube_autocomplete_queries(topic: str, lang: str = "es") -> list:
    """Extrae las consultas predictivas en vivo en paralelo."""
    seed_terms = [topic]
    words = [w for w in topic.split() if w.lower() not in STOP_WORDS]

    if len(words) >= 2:
        seed_terms.append(" ".join(words[:2]))
        seed_terms.append(" ".join(words[-2:]))
    if len(words) >= 3:
        seed_terms.append(" ".join(words[:3]))

    # Deduplicate seeds preserving order
    unique_seeds = list(dict.fromkeys(seed_terms))
    queries = set()
    with ThreadPoolExecutor(max_workers=max(1, len(unique_seeds))) as pool:
        for res_list in pool.map(lambda s: _fetch_single_suggest(s, lang), unique_seeds):
            queries.update(res_list)

    return sorted(queries)


def analyze_market_patterns(competitors: list, queries: list) -> dict:
    """Extrae términos y patrones recurrentes entre los títulos virales y las búsquedas."""
    word_freq = {}
    all_texts = [c["title"].lower() for c in competitors] + [q.lower() for q in queries]
    for text in all_texts:
        for word in text.split():
            clean_word = "".join(ch for ch in word if ch.isalnum())
            if len(clean_word) > 3 and clean_word not in STOP_WORDS:
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1

    top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "top_recurring_keywords": [k[0] for k in top_keywords],
        "top_competitor_title_examples": [c["title"] for c in competitors[:3] if c.get("title")]
    }


def extract_viral_intelligence(topic: str, lang: str = "es", max_competitors: int = 5) -> dict:
    """Ejecuta yt-dlp y YouTube Autocomplete simultáneamente en hilos paralelos."""
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_comp = pool.submit(fetch_competitor_shorts, topic, max_competitors)
        fut_queries = pool.submit(fetch_youtube_autocomplete_queries, topic, lang)
        competitors = fut_comp.result()
        real_queries = fut_queries.result()

    patterns = analyze_market_patterns(competitors, real_queries)
    return {
        "topic": topic,
        "language": lang,
        "elapsed_seconds": round(time.time() - t0, 2),
        "total_competitors_analyzed": len(competitors),
        "competitor_viral_shorts": competitors,
        "live_youtube_search_queries": real_queries,
        "market_patterns": patterns
    }


def main():
    parser = argparse.ArgumentParser(description="Extractor Paralelo de Inteligencia Viral de Mercado")
    parser.add_argument("--topic", required=True, help="Tema o concepto del video")
    parser.add_argument("--lang", default="es", help="Idioma de búsqueda (es, en, mx)")
    parser.add_argument("--max-competitors", type=int, default=5, help="Número de videos competidores a analizar")
    parser.add_argument("--output", default=None, help="Ruta del archivo JSON de salida")

    args = parser.parse_args()
    data = extract_viral_intelligence(
        topic=args.topic,
        lang=args.lang,
        max_competitors=args.max_competitors
    )

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Inteligencia viral guardada exitosamente en {args.output} ({data['elapsed_seconds']}s)")
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
