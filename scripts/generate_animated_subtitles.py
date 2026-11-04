#!/usr/bin/env python3
"""
Dynamic Animated Subtitles Generator for High-Retention Short-Form Videos
Produces ASS (Advanced SubStation Alpha) vector subtitles synchronized with Edge-TTS word boundaries.
Supports:
1. 'hybrid': First 5s (Beat 1 gancho) uses stable typewriter (letter-by-letter), remainder uses Hormozi neon highlight.
2. 'hormozi': Multi-word context block (3-5 words) with real-time popped neon active word.
3. 'typewriter': Progressive letter-by-letter appearance with ASS alpha-masking (zero horizontal jitter).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

try:
    import edge_tts
    from edge_tts import SubMaker
except ImportError:
    edge_tts = None
    SubMaker = None


COLOR_MAP = {
    "yellow": "&H0000FFFF&",    # RGB #FFFF00 -> ASS BGR &H0000FFFF&
    "cyan": "&H00FFFF00&",      # RGB #00FFFF -> ASS BGR &H00FFFF00&
    "green": "&H0066FF00&",     # RGB #00FF66 -> ASS BGR &H0066FF00&
    "gold": "&H0020D0FF&",      # RGB #FFD020 -> ASS BGR &H0020D0FF&
    "white": "&H00FFFFFF&",     # RGB #FFFFFF -> ASS BGR &H00FFFFFF&
}


def hex_to_ass_color(hex_str: str) -> str:
    h = hex_str.strip().lstrip("#")
    if len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
        return f"&H00{b}{g}{r}&"
    return COLOR_MAP.get(hex_str.lower(), "&H0000FFFF&")


def timedelta_to_ass_time(td: datetime.timedelta) -> str:
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    secs = int(total_seconds % 60)
    centis = int(round((total_seconds - int(total_seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def generate_animated_subtitles(
    text: str,
    voice: str = "es-MX-JorgeNeural",
    output_audio: str | None = None,
    output_ass: str | None = None,
    style: str = "hybrid",
    accent_color: str = "yellow",
    words_per_line: int = 4
) -> dict:
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed in the active environment.")

    accent_ass = COLOR_MAP.get(accent_color.lower(), hex_to_ass_color(accent_color))
    
    print(f"Synthesizing voice with Edge-TTS (voice: '{voice}', boundary: 'WordBoundary')...")
    comm = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    sub_maker = SubMaker()
    audio_bytes = bytearray()

    for chunk in comm.stream_sync():
        chunk_type = chunk.get("type")
        if chunk_type == "audio":
            audio_bytes.extend(chunk.get("data", b""))
        elif chunk_type in ("WordBoundary", "SentenceBoundary"):
            sub_maker.feed(chunk)

    if output_audio:
        os.makedirs(os.path.dirname(os.path.abspath(output_audio)), exist_ok=True)
        with open(output_audio, "wb") as f:
            f.write(audio_bytes)

    cues = getattr(sub_maker, "cues", [])
    if not cues and hasattr(sub_maker, "subs"):
        cues = sub_maker.subs

    total_duration_sec = cues[-1].end.total_seconds() if cues else 0.0
    print(f"Captured {len(cues)} word cues. Audio duration: {total_duration_sec:.2f}s ({len(audio_bytes)} bytes).")

    # ASS Header with high-contrast semi-transparent black capsule (BorderStyle=3)
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,74,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,2,0,3,10,0,5,30,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []
    
    # Group cues into natural chunks (3 to 5 words per line)
    chunks = []
    for i in range(0, len(cues), words_per_line):
        chunks.append(cues[i:i + words_per_line])

    for chunk in chunks:
        if not chunk:
            continue

        chunk_start_sec = chunk[0].start.total_seconds()
        
        # Determine whether this chunk uses typewriter effect:
        # - "typewriter": all chunks
        # - "hybrid": first 5 seconds (Beat 1 gancho) only, then switches to Hormozi
        # - "hormozi": none
        is_typewriter = (style == "typewriter") or (style == "hybrid" and chunk_start_sec < 5.0)

        if is_typewriter:
            # Typewriter (letter by letter) with ASS alpha-masking
            for idx, active_cue in enumerate(chunk):
                w_text = active_cue.content.strip().upper()
                w_start = active_cue.start.total_seconds()
                w_end = active_cue.end.total_seconds()
                dur = max(0.08, w_end - w_start)
                n_chars = max(1, len(w_text))
                char_dur = dur / n_chars

                # Words already completed before active word in this chunk
                before_str = " ".join([c.content.strip().upper() for c in chunk[:idx]])
                if before_str:
                    before_str += " "

                # Words remaining after active word in this chunk
                after_words = [c.content.strip().upper() for c in chunk[idx + 1:]]
                after_str = (" " + " ".join(after_words)) if after_words else ""

                for c_idx in range(1, n_chars + 1):
                    t1 = w_start + (c_idx - 1) * char_dur
                    t2 = w_start + c_idx * char_dur
                    if c_idx == n_chars:
                        t2 = w_end

                    s_td = datetime.timedelta(seconds=t1)
                    e_td = datetime.timedelta(seconds=t2)

                    revealed = w_text[:c_idx]
                    masked = w_text[c_idx:]

                    # Target word: revealed part in accent color, unrevealed in alpha &HFF&
                    word_part = f"{{\\c{accent_ass}}}{revealed}{{\\alpha&HFF&}}{masked}{{\\alpha&H00&}}"
                    line_text = f"{{\\pos(540,1114)}}{{\\c&H00FFFFFF&}}{before_str}{word_part}{{\\alpha&HFF&}}{after_str}"
                    dialogue_lines.append(f"Dialogue: 0,{timedelta_to_ass_time(s_td)},{timedelta_to_ass_time(e_td)},Default,,0,0,0,,{line_text}")
        else:
            # Hormozi style: full phrase shown, active word pops and glows in neon accent
            for idx, active_cue in enumerate(chunk):
                s_td = active_cue.start
                e_td = active_cue.end

                parts = []
                for j, c in enumerate(chunk):
                    word_str = c.content.strip().upper()
                    if j < idx:
                        # Already spoken: crisp pure white
                        parts.append(f"{{\\fscx100\\fscy100\\c&H00FFFFFF&}}{word_str}")
                    elif j == idx:
                        # Active: popped 15% in accent color
                        parts.append(f"{{\\fscx115\\fscy115\\c{accent_ass}}}{word_str}")
                    else:
                        # Upcoming: subtle translucent gray
                        parts.append(f"{{\\fscx100\\fscy100\\c&H00808080&}}{word_str}")

                line_text = f"{{\\pos(540,1114)}}" + " ".join(parts)
                dialogue_lines.append(f"Dialogue: 0,{timedelta_to_ass_time(s_td)},{timedelta_to_ass_time(e_td)},Default,,0,0,0,,{line_text}")

    ass_content = ass_header + "\n".join(dialogue_lines) + "\n"
    if output_ass:
        os.makedirs(os.path.dirname(os.path.abspath(output_ass)), exist_ok=True)
        with open(output_ass, "w", encoding="utf-8") as f:
            f.write(ass_content)

    return {
        "audio_path": output_audio,
        "ass_path": output_ass,
        "duration_seconds": total_duration_sec,
        "word_cues_count": len(cues),
        "dialogue_events_count": len(dialogue_lines)
    }


def main():
    parser = argparse.ArgumentParser(description="Generate dynamic animated subtitles (.ass) and audio via Edge-TTS.")
    parser.add_argument("--script-json", default=None, help="Path to video_script.json")
    parser.add_argument("--text", default=None, help="Raw script text")
    parser.add_argument("--voice", default="es-MX-JorgeNeural", help="Edge-TTS voice")
    parser.add_argument("--style", default="hybrid", choices=["hybrid", "hormozi", "typewriter"], help="Subtitle animation style")
    parser.add_argument("--accent-color", default="yellow", help="Accent color name (yellow, cyan, green) or hex code (#FFFF00)")
    parser.add_argument("--words-per-line", type=int, default=4, help="Words per subtitle block (default: 4)")
    parser.add_argument("--output-audio", required=True, help="Destination mp3 audio path")
    parser.add_argument("--output-ass", required=True, help="Destination ASS subtitle path")
    args = parser.parse_args()

    full_text = args.text
    voice = args.voice

    if args.script_json and os.path.exists(args.script_json):
        with open(args.script_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        full_text = data.get("full_script") or full_text
        voice = data.get("voice_name") or voice

    if not full_text:
        print("ERROR: Either --script-json or --text must be provided.", file=sys.stderr)
        sys.exit(1)

    res = generate_animated_subtitles(
        text=full_text,
        voice=voice,
        output_audio=args.output_audio,
        output_ass=args.output_ass,
        style=args.style,
        accent_color=args.accent_color,
        words_per_line=args.words_per_line
    )
    print(f"Animated subtitles generated successfully: {res['ass_path']} ({res['dialogue_events_count']} events, {res['duration_seconds']:.2f}s)")


if __name__ == "__main__":
    main()
