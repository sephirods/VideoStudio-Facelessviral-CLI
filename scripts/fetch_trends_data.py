#!/usr/bin/env python3
"""
Parallel Real-Time Market Trend Extractor for Trend Researcher
Fetches concurrently across 7 threads (~1.5s total vs ~10s sequential):
1. Google Trends Realtime & Daily RSS (ES, MX, US).
2. Viral Reddit RSS feeds (r/todayilearned, r/business, r/technology, r/Economics).
Outputs: pipeline_runs/current_market_trends.json
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
REDDIT_HEADERS = {
    "User-Agent": "windows:com.videostudio.trends:v1.2 (by /u/videostudio_cli)"
}


def fetch_google_trends(geo: str = "US") -> list[dict]:
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    req = urllib.request.Request(url, headers=HEADERS)
    trends = []
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        ns = "{https://trends.google.com/trending/rss}"
        for item in root.findall(".//item"):
            title_el = item.find("title")
            title = title_el.text if title_el is not None else ""
            approx_traffic = item.find(f"{ns}approx_traffic")
            traffic = approx_traffic.text if approx_traffic is not None else "N/A"
            pub_date_el = item.find("pubDate")
            pub_date = pub_date_el.text if pub_date_el is not None else ""
            news_items = []
            for n in item.findall(f"{ns}news_item"):
                n_title = n.find(f"{ns}news_item_title")
                if n_title is not None and n_title.text:
                    news_items.append(n_title.text)
            trends.append({
                "source": f"google_trends_{geo}",
                "topic": title,
                "search_volume": traffic,
                "date": pub_date,
                "context_headlines": news_items[:3]
            })
    except Exception as e:
        print(f"Warning: Failed to fetch Google Trends for {geo}: {e}", file=sys.stderr)
    return trends


def fetch_reddit_rss(subreddit: str, stagger_sec: float = 0.0) -> list[dict]:
    if stagger_sec > 0:
        time.sleep(stagger_sec)
    url = f"https://old.reddit.com/r/{subreddit}/top/.json?t=day&limit=8"
    req = urllib.request.Request(url, headers=REDDIT_HEADERS)
    posts = []
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for child in data.get("data", {}).get("children", [])[:8]:
            pdata = child.get("data", {})
            posts.append({
                "source": f"reddit_r_{subreddit}",
                "title": pdata.get("title", ""),
                "score": pdata.get("score", 0),
                "url": f"https://www.reddit.com{pdata.get('permalink', '')}",
                "date": str(pdata.get("created_utc", ""))
            })
        return posts
    except Exception:
        pass
    # Fallback to RSS XML
    rss_url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit=8"
    req = urllib.request.Request(rss_url, headers=REDDIT_HEADERS)
    posts = []
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        atom_ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(f"{atom_ns}entry")[:8]:
            title_el = entry.find(f"{atom_ns}title")
            title = title_el.text if title_el is not None else ""
            link_el = entry.find(f"{atom_ns}link")
            link = link_el.get("href") if link_el is not None else ""
            updated_el = entry.find(f"{atom_ns}updated")
            updated = updated_el.text if updated_el is not None else ""
            posts.append({
                "source": f"reddit_r_{subreddit}",
                "title": title,
                "url": link,
                "date": updated
            })
    except Exception as e:
        print(f"Warning: Failed to fetch Reddit r/{subreddit}: {e}", file=sys.stderr)
    return posts


def main():
    parser = argparse.ArgumentParser(description="Fetch live market trends in parallel.")
    parser.add_argument("--output", default=None, help="Optional custom output JSON path")
    args = parser.parse_args()

    t0 = time.time()
    print("Fetching live market trend data in parallel (7 concurrent feeds)...")

    tasks = {
        "gt_es": (fetch_google_trends, ("ES",)),
        "gt_mx": (fetch_google_trends, ("MX",)),
        "gt_us": (fetch_google_trends, ("US",)),
        "rd_business": (fetch_reddit_rss, ("business", 0.0)),
        "rd_til": (fetch_reddit_rss, ("todayilearned", 0.2)),
        "rd_tech": (fetch_reddit_rss, ("technology", 0.4)),
        "rd_econ": (fetch_reddit_rss, ("Economics", 0.6)),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=7) as pool:
        future_map = {key: pool.submit(fn, *fargs) for key, (fn, fargs) in tasks.items()}
        for key, fut in future_map.items():
            results[key] = fut.result()

    elapsed = round(time.time() - t0, 2)
    all_data = {
        "fetched_at": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "google_trends": {
            "spain": results["gt_es"],
            "mexico": results["gt_mx"],
            "united_states": results["gt_us"]
        },
        "viral_communities": {
            "business": results["rd_business"],
            "today_i_learned": results["rd_til"],
            "technology": results["rd_tech"],
            "economics": results["rd_econ"]
        }
    }

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if args.output:
        out_file = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
    else:
        out_dir = os.path.join(root_dir, "pipeline_runs")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "current_market_trends.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    total_gt = sum(len(v) for v in all_data["google_trends"].values())
    total_rd = sum(len(v) for v in all_data["viral_communities"].values())
    print(f"Success in {elapsed}s: Collected {total_gt} Google Trends & {total_rd} viral community stories.")
    print(f"Output saved to: {out_file}")


if __name__ == "__main__":
    main()
