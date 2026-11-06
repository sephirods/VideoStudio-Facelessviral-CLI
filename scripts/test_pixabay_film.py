import os
import requests
import json

api_key = '40839781-08845e6cb3305cabe0bc656d3'
queries = [
    'river fish',
    'fishing rod river',
    'fisherman boat',
    'freshwater fish underwater',
    'river current stream',
    'wild river nature',
    'predator fish water'
]

results = {}
for q in queries:
    url = f"https://pixabay.com/api/videos/?key={api_key}&q={requests.utils.quote(q)}&video_type=film&per_page=15"
    res = requests.get(url).json()
    hits = res.get('hits', [])
    print(f"Query: '{q}' -> {len(hits)} hits")
    for h in hits[:3]:
        tags = h.get('tags', '')
        dur = h.get('duration', 0)
        vid_id = h.get('id')
        print(f"  ID: {vid_id} | dur: {dur}s | tags: {tags}")
