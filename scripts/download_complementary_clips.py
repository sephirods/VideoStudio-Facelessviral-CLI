import os
import requests
import subprocess

api_key = '40839781-08845e6cb3305cabe0bc656d3'
target_ids = [
    206783,  # Catfish swimming with whiskers/barbels
    111288,  # Pike freshwater predator hunting underwater
    154653,  # Fisherman on river with fishing rod
    10008,   # Fishing reel and line spinning
    4260,    # Fishermen at river with rods
    44534,   # Angler in small boat fishing
    199308,  # River fish underwater in stream rocks
    199307,  # River fish swimming in current
    931,     # Big river fish underwater riverbed
    211373,  # Giant monster fish underwater
    2263,    # River current and splash over stones
    144934,  # Wild river rushing water
    263131,  # Big freshwater fish swimming near surface
]

dest_dir = r"C:\MoneyPrinterTurbo\storage\cache_videos"
frames_dir = r"C:\Users\Juan\Desktop\CanalesYoutube\pipeline_runs\demo_pesca\frames"
os.makedirs(dest_dir, exist_ok=True)
os.makedirs(frames_dir, exist_ok=True)

downloaded = []

for vid_id in target_ids:
    url = f"https://pixabay.com/api/videos/?key={api_key}&id={vid_id}"
    res = requests.get(url).json()
    hits = res.get("hits", [])
    if not hits:
        print(f"Warning: No hit for ID {vid_id}")
        continue
    hit = hits[0]
    videos = hit.get("videos", {})
    # Choose highest available resolution (large -> medium -> small)
    chosen = videos.get("large") or videos.get("medium") or videos.get("small") or videos.get("tiny")
    if not chosen or not chosen.get("url"):
        print(f"Warning: No video URL for ID {vid_id}")
        continue
    
    file_url = chosen["url"]
    filename = f"vid-pixabay-{vid_id}.mp4"
    dest_path = os.path.join(dest_dir, filename)
    
    print(f"Downloading ID {vid_id} ({chosen.get('width')}x{chosen.get('height')}) to {filename}...")
    r = requests.get(file_url, stream=True, timeout=60)
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
    
    # Extract test frame
    frame_name = f"vid-pixabay-{vid_id}.jpg"
    frame_path = os.path.join(frames_dir, frame_name)
    cmd = [
        'ffmpeg', '-y', '-ss', '00:00:02.000', '-i', dest_path,
        '-vframes', '1', '-q:v', '2', frame_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Saved clip: {dest_path} | Frame: {frame_path} (exists: {os.path.exists(frame_path)})")
    downloaded.append((dest_path, frame_path, hit.get("tags", "")))

print(f"\nSuccessfully downloaded and extracted frames for {len(downloaded)} clips.")
