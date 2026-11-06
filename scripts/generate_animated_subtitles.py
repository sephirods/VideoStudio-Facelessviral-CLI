#!/usr/bin/env python3
"""
Dynamic Animated Subtitles Generator for High-Retention Short-Form Videos
Produces ASS (Advanced SubStation Alpha) vector subtitles synchronized with Edge-TTS word boundaries.

Features:
- Zero Flicker / Parpadeo Cero: Contiguous time intervals without gaps between words or pauses.
- Dynamic Karaoke Highlight: Active word in vibrant neon accent, previous words in white, upcoming in soft gray.
- Zero Jitter & Mobile Width Guard: Smart character-budget chunking (max 20 chars) + auto-scale for long words
  so text never collides with TikTok/Reels/Shorts right-side UI icons on 1080x1920 screens.
- Styles:
  1. 'hormozi' (Default): Clean black stroke (Outline=7, Shadow=2) at 58% height with neon karaoke highlight.
  2. 'hybrid': High-intensity 1-2 word bursts during the Hook (0-5s), transitioning to width-safe 3-word blocks.
  3. 'typewriter': Progressive letter-by-letter appearance with thick text outline (BorderStyle=1) and zero-gap dwell.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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


def _probe_audio_duration(audio_path: str | None, fallback: float) -> float:
    if not audio_path or not os.path.exists(audio_path):
        return fallback
    try:
        res = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", audio_path
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            return max(fallback, float(res.stdout.strip()))
    except Exception:
        pass
    return fallback


def _build_smart_chunks(cues: list, style: str, words_per_line: int, max_chars: int = 20) -> list[list]:
    """
    Groups word cues into width-safe mobile subtitle chunks:
    - Respects character budget (`max_chars`, default 20 at Impact 74pt) to prevent horizontal overflow
      or collision with right-hand TikTok/Shorts UI buttons.
    - In 'hybrid' mode, uses rapid 1-2 word bursts (max 16 chars) during the first 5.0s (Hook),
      then transitions to up to `words_per_line` words (max 20 chars).
    """
    base_max_words = words_per_line if words_per_line > 0 else 3
    chunks: list[list] = []
    current: list = []
    current_len = 0

    for cue in cues:
        w_str = cue.content.strip().upper()
        if not w_str:
            continue
        cue_start = cue.start.total_seconds()

        if style == "hybrid" and cue_start < 5.0:
            limit_words = min(2, base_max_words)
            limit_chars = min(16, max_chars)
        else:
            limit_words = base_max_words
            limit_chars = max_chars

        added_len = len(w_str) if not current else (current_len + 1 + len(w_str))

        if current and (len(current) >= limit_words or added_len > limit_chars):
            chunks.append(current)
            current = [cue]
            current_len = len(w_str)
        else:
            current.append(cue)
            current_len = added_len

    if current:
        chunks.append(current)
    return chunks


def _line_scale_prefix(chunk_text: str, safe_chars: int = 19) -> str:
    """Auto-scales ultra-long single words or phrases so they always stay within safe mobile margins."""
    n = len(chunk_text)
    if n <= safe_chars:
        return ""
    pct = max(70, min(96, int((safe_chars / n) * 100)))
    return f"{{\\fscx{pct}\\fscy{pct}}}"


def generate_animated_subtitles(
    text: str,
    voice: str = "es-MX-JorgeNeural",
    output_audio: str | None = None,
    output_ass: str | None = None,
    style: str = "hormozi",
    accent_color: str = "yellow",
    words_per_line: int = 3,
    box_background: bool = False,
    max_chars_per_line: int = 20,
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

    cues_duration_sec = cues[-1].end.total_seconds() if cues else 0.0
    total_duration_sec = _probe_audio_duration(output_audio, cues_duration_sec)
    print(f"Captured {len(cues)} word cues. Audio duration: {total_duration_sec:.2f}s ({len(audio_bytes)} bytes).")

    # Select ASS Style configuration:
    # - Default (box_background=False): BorderStyle=1 with heavy black stroke (Outline=7, Shadow=2)
    #   Cleaner, modern TikTok/Hormozi look without blocking background footage.
    # - box_background=True: BorderStyle=3 (high-contrast dark capsule box)
    if box_background:
        border_style = 3
        outline_val = 10
        shadow_val = 0
        back_color = "&HA0000000"
    else:
        border_style = 1
        outline_val = 7
        shadow_val = 2
        back_color = "&H80000000"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,74,&H00FFFFFF,&H000000FF,&H00000000,{back_color},-1,0,0,0,100,100,2,0,{border_style},{outline_val},{shadow_val},5,60,90,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []
    chunks = _build_smart_chunks(cues, style=style, words_per_line=words_per_line, max_chars=max_chars_per_line)

    num_chunks = len(chunks)
    for c_idx, chunk in enumerate(chunks):
        if not chunk:
            continue

        chunk_start = chunk[0].start.total_seconds()
        chunk_word_end = chunk[-1].end.total_seconds()
        full_chunk_str = " ".join(c.content.strip().upper() for c in chunk)
        scale_tag = _line_scale_prefix(full_chunk_str)

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
            chunk_final_end = min(total_duration_sec, chunk_word_end + 0.40) if total_duration_sec > 0 else chunk_word_end + 0.40

        num_words = len(chunk)

        if style == "typewriter":
            for w_idx, active_cue in enumerate(chunk):
                w_text = active_cue.content.strip().upper()
                w_start = chunk_start if w_idx == 0 else chunk[w_idx].start.total_seconds()

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

                for char_i in range(1, n_chars + 1):
                    t1 = w_start + (char_i - 1) * char_dur
                    t2 = w_start + char_i * char_dur if char_i < n_chars else active_cue.end.total_seconds()

                    revealed = w_text[:char_i]
                    word_part = f"{{\\c{accent_ass}}}{revealed}"
                    line_text = f"{{\\pos(540,1114)}}{scale_tag}{{\\c&H00FFFFFF&}}{before_str}{word_part}"
                    dialogue_lines.append(
                        f"Dialogue: 0,{seconds_to_ass_time(t1)},{seconds_to_ass_time(t2)},Default,,0,0,0,,{line_text}"
                    )

                t_hold_start = active_cue.end.total_seconds()
                if next_w_start > t_hold_start + 0.02:
                    word_part = f"{{\\c{accent_ass}}}{w_text}"
                    line_text = f"{{\\pos(540,1114)}}{scale_tag}{{\\c&H00FFFFFF&}}{before_str}{word_part}"
                    dialogue_lines.append(
                        f"Dialogue: 0,{seconds_to_ass_time(t_hold_start)},{seconds_to_ass_time(next_w_start)},Default,,0,0,0,,{line_text}"
                    )

        else:
            # Hormozi & Hybrid: Constant-width line with contiguous active word highlight
            # ZERO gaps between words, ZERO horizontal shift, ZERO mobile UI collision
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
                        parts.append(f"{{\\c&H00FFFFFF&}}{word_str}")
                    elif j == w_idx:
                        parts.append(f"{{\\c{accent_ass}}}{word_str}")
                    else:
                        parts.append(f"{{\\c&H00A0A0A0&}}{word_str}")

                line_text = f"{{\\pos(540,1114)}}{scale_tag}" + " ".join(parts)
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
        "cues_duration_seconds": cues_duration_sec,
        "word_cues_count": len(cues),
        "chunks_count": len(chunks),
        "dialogue_events_count": len(dialogue_lines)
    }


def main():
    parser = argparse.ArgumentParser(description="Generate dynamic animated subtitles (.ass) and audio via Edge-TTS.")
    parser.add_argument("--script-json", default=None, help="Path to video_script.json")
    parser.add_argument("--text", default=None, help="Raw script text")
    parser.add_argument("--voice", default="es-MX-JorgeNeural", help="Edge-TTS voice")
    parser.add_argument("--style", default="hormozi", choices=["hormozi", "hybrid", "typewriter"], help="Subtitle animation style")
    parser.add_argument("--accent-color", default="yellow", help="Accent color name (yellow, cyan, green) or hex code (#FFFF00)")
    parser.add_argument("--words-per-line", type=int, default=3, help="Max words per subtitle block (default: 3)")
    parser.add_argument("--max-chars", type=int, default=20, help="Max characters per line to prevent mobile UI overlap (default: 20)")
    parser.add_argument("--box-background", action="store_true", help="Enable semi-transparent dark box background instead of clean outline")
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
        words_per_line=args.words_per_line,
        box_background=args.box_background,
        max_chars_per_line=args.max_chars
    )
    print(f"Animated subtitles generated successfully: {res['ass_path']} ({res['dialogue_events_count']} events, {res['chunks_count']} blocks, {res['duration_seconds']:.2f}s)")


if __name__ == "__main__":
    main()
