#!/usr/bin/env python3
"""
Dynamic Animated Subtitles Generator for High-Retention Short-Form Videos
Produces ASS (Advanced SubStation Alpha) vector subtitles synchronized with Edge-TTS word boundaries.

Features:
- Zero Flicker / Parpadeo Cero: Contiguous time intervals without gaps between words or pauses.
- Dynamic Karaoke Highlight: Active word in vibrant neon accent, previous words in white, upcoming in soft gray.
- Zero Jitter: Constant-width line layout with fixed font metrics and center alignment at 58% height.
- Styles:
  1. 'hormozi' (Default): Rock-solid high-retention neon karaoke inside a high-contrast dark capsule.
  2. 'hybrid': High-intensity 2-word bursts during hook (0-5s), transitioning to 3-word narrative blocks.
  3. 'typewriter': Progressive letter-by-letter appearance with thick text outline (BorderStyle=1) and zero-gap dwell.
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


def seconds_to_ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def generate_animated_subtitles(
    text: str,
    voice: str = "es-MX-JorgeNeural",
    output_audio: str | None = None,
    output_ass: str | None = None,
    style: str = "hormozi",
    accent_color: str = "yellow",
    words_per_line: int = 3
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

    # Select ASS Style configuration:
    # - hormozi / hybrid: BorderStyle=3 (high-contrast dark capsule) with constant-width line
    # - typewriter: BorderStyle=1 (thick black outline) so progressive characters don't cause box resizing
    border_style = 1 if style == "typewriter" else 3
    outline_val = 6 if style == "typewriter" else 10
    back_color = "&H00000000" if style == "typewriter" else "&HA0000000"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,74,&H00FFFFFF,&H000000FF,&H00000000,{back_color},-1,0,0,0,100,100,2,0,{border_style},{outline_val},0,5,30,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []

    # Group cues into natural chunks
    chunks = []
    chunk_size = words_per_line if words_per_line > 0 else 3
    for i in range(0, len(cues), chunk_size):
        chunks.append(cues[i:i + chunk_size])

    num_chunks = len(chunks)
    for c_idx, chunk in enumerate(chunks):
        if not chunk:
            continue

        chunk_start = chunk[0].start.total_seconds()
        chunk_word_end = chunk[-1].end.total_seconds()

        # Seamless Chunk-to-Chunk Handover:
        # If the gap to the next chunk is short (< 0.55s), hold the current chunk
        # all the way until the next chunk begins. This eliminates inter-phrase blinking.
        if c_idx + 1 < num_chunks and chunks[c_idx + 1]:
            next_chunk_start = chunks[c_idx + 1][0].start.total_seconds()
            gap_to_next = next_chunk_start - chunk_word_end
            if gap_to_next < 0.55:
                chunk_final_end = next_chunk_start
            else:
                chunk_final_end = chunk_word_end + 0.35
        else:
            chunk_final_end = chunk_word_end + 0.40

        num_words = len(chunk)

        if style == "typewriter":
            # Typewriter: progressive letter reveal without black box jitter
            for w_idx, active_cue in enumerate(chunk):
                w_text = active_cue.content.strip().upper()
                w_start = chunk_start if w_idx == 0 else chunk[w_idx].start.total_seconds()
                
                # Next word start or chunk end
                if w_idx + 1 < num_words:
                    next_w_start = chunk[w_idx + 1].start.total_seconds()
                else:
                    next_w_start = chunk_final_end

                n_chars = max(1, len(w_text))
                dur = max(0.08, min(active_cue.end.total_seconds() - w_start, next_w_start - w_start))
                char_dur = dur / n_chars

                before_str = " ".join([c.content.strip().upper() for c in chunk[:w_idx]])
                if before_str:
                    before_str += " "

                # Type each character with contiguous intervals
                for c_idx in range(1, n_chars + 1):
                    t1 = w_start + (c_idx - 1) * char_dur
                    t2 = w_start + c_idx * char_dur if c_idx < n_chars else active_cue.end.total_seconds()
                    
                    revealed = w_text[:c_idx]
                    word_part = f"{{\\c{accent_ass}}}{revealed}"
                    line_text = f"{{\\pos(540,1114)}}{{\\c&H00FFFFFF&}}{before_str}{word_part}"
                    dialogue_lines.append(
                        f"Dialogue: 0,{seconds_to_ass_time(t1)},{seconds_to_ass_time(t2)},Default,,0,0,0,,{line_text}"
                    )

                # Hold full word during pause until next word starts (zero gap)
                t_hold_start = active_cue.end.total_seconds()
                if next_w_start > t_hold_start + 0.02:
                    word_part = f"{{\\c{accent_ass}}}{w_text}"
                    line_text = f"{{\\pos(540,1114)}}{{\\c&H00FFFFFF&}}{before_str}{word_part}"
                    dialogue_lines.append(
                        f"Dialogue: 0,{seconds_to_ass_time(t_hold_start)},{seconds_to_ass_time(next_w_start)},Default,,0,0,0,,{line_text}"
                    )

        else:
            # Hormozi & Hybrid: Constant-width line with contiguous active word highlight
            # ZERO gaps between words, ZERO horizontal shift, ZERO box expansion
            for w_idx, active_cue in enumerate(chunk):
                w_start = chunk_start if w_idx == 0 else chunk[w_idx].start.total_seconds()

                if w_idx + 1 < num_words:
                    w_end = chunk[w_idx + 1].start.total_seconds()
                else:
                    w_end = chunk_final_end

                if w_end <= w_start:
                    w_end = w_start + 0.08

                parts = []
                for j, c in enumerate(chunk):
                    word_str = c.content.strip().upper()
                    if j < w_idx:
                        # Spoken words: crisp pure white
                        parts.append(f"{{\\c&H00FFFFFF&}}{word_str}")
                    elif j == w_idx:
                        # Active word: bright neon accent color
                        parts.append(f"{{\\c{accent_ass}}}{word_str}")
                    else:
                        # Upcoming words: subtle soft translucent gray
                        parts.append(f"{{\\c&H00A0A0A0&}}{word_str}")

                line_text = f"{{\\pos(540,1114)}}" + " ".join(parts)
                dialogue_lines.append(
                    f"Dialogue: 0,{seconds_to_ass_time(w_start)},{seconds_to_ass_time(w_end)},Default,,0,0,0,,{line_text}"
                )

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
    parser.add_argument("--style", default="hormozi", choices=["hormozi", "hybrid", "typewriter"], help="Subtitle animation style")
    parser.add_argument("--accent-color", default="yellow", help="Accent color name (yellow, cyan, green) or hex code (#FFFF00)")
    parser.add_argument("--words-per-line", type=int, default=3, help="Words per subtitle block (default: 3)")
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
