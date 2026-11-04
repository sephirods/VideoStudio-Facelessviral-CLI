#!/usr/bin/env python3
"""
Real-Time Market Trend Extractor for Trend Researcher
Fetches:
1. Google Trends Realtime & Daily RSS (ES, MX, US).
2. Viral Reddit RSS feeds (r/todayilearned, r/business, r/technology, r/Economics).
3. Classifies topics by the 4 Monetization Pillars.
Outputs: c:\\ganar dinero\\pipeline_runs\\current_market_trends.json
"""
import urllib.request
import json
import xml.etree.ElementTree as ET
import os
import sys
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_google_trends(geo="US"):
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    req = urllib.request.Request(url, headers=HEADERS)
    trends = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else ""
            approx_traffic = item.find("{https://trends.google.com/trending/rss}approx_traffic")
            traffic = approx_traffic.text if approx_traffic is not None else "N/A"
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            news_items = []
            for n in item.findall("{https://trends.google.com/trending/rss}news_item"):
                n_title = n.find("{https://trends.google.com/trending/rss}news_item_title")
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


def fetch_reddit_rss(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit=10"
    req = urllib.request.Request(url, headers=HEADERS)
    posts = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
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
    print("Fetching live market trend data from Google Trends and Reddit feeds...")
    all_data = {
        "fetched_at": datetime.now().isoformat(),
        "google_trends": {
            "spain": fetch_google_trends("ES"),
            "mexico": fetch_google_trends("MX"),
            "united_states": fetch_google_trends("US")
        },
        "viral_communities": {
            "business": fetch_reddit_rss("business"),
            "today_i_learned": fetch_reddit_rss("todayilearned"),
            "technology": fetch_reddit_rss("technology"),
            "economics": fetch_reddit_rss("Economics")
        }
    }

    out_dir = r"c:\ganar dinero\pipeline_runs"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "current_market_trends.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    total_gt = sum(len(v) for v in all_data["google_trends"].values())
    total_rd = sum(len(v) for v in all_data["viral_communities"].values())
    print(f"Success: Collected {total_gt} Google Trends & {total_rd} viral community stories.")
    print(f"Output saved to: {out_file}")


if __name__ == "__main__":
    main()
