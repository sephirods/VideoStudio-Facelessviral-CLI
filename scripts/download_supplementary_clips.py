import os
import sys
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE_DIR = r"C:\MoneyPrinterTurbo"
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

from app.services import material

terms = [
    "galaxy space stars",
    "deep space nebula",
    "alien planet atmosphere",
    "solar flare sun",
    "cosmic storm space",
    "space starfield universe",
    "exoplanet cosmic orbit"
]

downloaded_files = []
# Existing already approved clips
approved_existing = [
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-70855c1fd4ef84001f380363d1fe7926.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-d3e3851862b5120006bc1b43d61657c7.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-cf866822b812402b33fe3747cfc51305.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-0e8ff1d6ddcef85b53ea51b050bc2222.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-abfddeceb66b88ef21b549688548db12.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-47d6f5afac211dd1bf22ae6b1dbee16b.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-d7e0c46fb3ef4de52348ec7a0442afe2.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-f3654477730c0c1e571ccfbeff46b1c4.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-8a6e45e895362c0ae572a51ba61427c3.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-63d9ae6f799e10f1151a4ba26f442c80.mp4"
]

seen_files = set(approved_existing)

for t in terms:
    res = material.search_videos_pixabay(t, minimum_duration=4)
    for r in res[:2]:
        try:
            print(f"Downloading from {t}: {r.url}")
            saved = material.save_video(r.url)
            if saved and os.path.exists(saved) and saved not in seen_files:
                downloaded_files.append(saved)
                seen_files.add(saved)
                print(f"  -> Saved: {saved} ({os.path.getsize(saved)/1024/1024:.2f} MB)")
            if len(downloaded_files) >= 8:
                break
        except Exception as e:
            print(f"Error downloading {r.url}: {e}")
    if len(downloaded_files) >= 8:
        break

output_json = os.path.join(ROOT_DIR, "pipeline_runs", "demo_espacio", "supplementary_clips.json")
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(downloaded_files, f, indent=2)

print(f"Downloaded {len(downloaded_files)} supplementary clips.")
