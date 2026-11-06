#!/usr/bin/env python3
"""
High-Speed Hardware-Accelerated Pipeline Job Runner
Executes pipeline stages ensuring:
1. 100% native UTF-8 encoding for scripts, subtitles, and voices.
2. Direct FFmpeg + NVENC/AMF GPU rendering in '--mode render' (~18-25s vs ~213s legacy MoviePy):
   - Strict SEQUENTIAL clip order (approved_clips[0] / hero_clip.mp4 guaranteed in 0-4s Hook).
   - Parallel GPU clip normalization + parallel in-memory personalized outro generation.
   - Single final GPU pass: burns .ass subtitles (58%, clean stroke), mixes voice + BGM (0.20)
     without volume halving (normalize=0), and concatenates personalized outro.
   - Automatic render_manifest.json telemetry emission.
3. Full backward compatibility via '--legacy-engine' fallback to MoneyPrinterTurbo CLI.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import glob
import json
import os
import random
import shutil
import subprocess
import sys
import time
import uuid

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

INITIAL_CWD = os.getcwd()
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

ENGINE_CANDIDATES = [
    os.path.join(ROOT_DIR, "engine", "MoneyPrinterTurbo"),
    r"C:\MoneyPrinterTurbo" if sys.platform.startswith("win") else "/opt/MoneyPrinterTurbo"
]
ENGINE_DIR = next((p for p in ENGINE_CANDIDATES if os.path.exists(p)), ENGINE_CANDIDATES[0])


def _ensure_python_deps(require_mpt_cli: bool = False):
    """Switches to MoneyPrinterTurbo .venv transparently only if active Python lacks required packages."""
    if not os.path.exists(ENGINE_DIR):
        return
    venv_py = (
        os.path.join(ENGINE_DIR, ".venv", "Scripts", "python.exe")
        if sys.platform.startswith("win")
        else os.path.join(ENGINE_DIR, ".venv", "bin", "python")
    )
    if not os.path.exists(venv_py) or os.path.abspath(sys.executable).lower() == os.path.abspath(venv_py).lower():
        return
    try:
        import edge_tts  # noqa: F401
        from PIL import Image  # noqa: F401
        if require_mpt_cli:
            import loguru  # noqa: F401
    except ImportError:
        res = subprocess.run([venv_py] + sys.argv)
        sys.exit(res.returncode)


def _load_mpt_cli():
    _ensure_python_deps(require_mpt_cli=True)
    if not os.path.exists(ENGINE_DIR):
        return None
    if ENGINE_DIR not in sys.path:
        sys.path.insert(0, ENGINE_DIR)
    os.chdir(ENGINE_DIR)
    import cli
    return cli


def get_hardware_encoder() -> tuple[str, str, int]:
    hw_file = os.path.join(ROOT_DIR, "config", "hardware.json")
    if os.path.exists(hw_file):
        try:
            with open(hw_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            enc = data.get("video_encoder", "libx264")
            preset = data.get("ffmpeg_preset", "p4" if "nvenc" in enc else "fast")
            conc = int(data.get("max_concurrency", 4))
            return enc, preset, max(1, min(conc, 4))
        except Exception:
            pass
    return "libx264", "veryfast", 2


def get_encoder_args_candidates() -> list[list[str]]:
    enc, preset, _ = get_hardware_encoder()
    candidates: list[list[str]] = []
    if enc != "libx264":
        if "nvenc" in enc:
            candidates.append(["-c:v", enc, "-preset", preset, "-cq", "21"])
        else:
            candidates.append(["-c:v", enc, "-preset", preset])
    candidates.append(["-c:v", "libx264", "-preset", "veryfast", "-crf", "21"])
    return candidates


def escape_ffmpeg_filter_path(file_path: str) -> str:
    abs_p = os.path.abspath(file_path).replace("\\", "/")
    return abs_p.replace(":", r"\:").replace("'", r"\'")


def probe_media_duration(file_path: str, default: float = 4.0) -> float:
    try:
        res = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", file_path
            ],
            capture_output=True,
            text=True,
            timeout=6
        )
        if res.returncode == 0 and res.stdout.strip():
            val = float(res.stdout.strip())
            if val > 0:
                return val
    except Exception:
        pass
    return default


def assemble_final_video(
    main_video: str,
    output_path: str,
    ass_path: str | None = None,
    outro_video: str | None = None,
):
    encoder, preset, _ = get_hardware_encoder()
    print(f"Assembling video (Encoder: '{encoder}', Subtitles: '{bool(ass_path)}', Outro: '{bool(outro_video)}')...")

    if ass_path and outro_video:
        escaped_ass = escape_ffmpeg_filter_path(ass_path)
        filter_complex = f"[0:v:0]ass='{escaped_ass}'[subv];[subv][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]"
        map_args = ["-map", "[outv]", "-map", "[outa]", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]
        inputs = ["-i", main_video, "-i", outro_video]
    elif ass_path:
        escaped_ass = escape_ffmpeg_filter_path(ass_path)
        filter_complex = f"[0:v:0]ass='{escaped_ass}'[outv]"
        map_args = ["-map", "[outv]", "-map", "0:a:0", "-c:a", "copy"]
        inputs = ["-i", main_video]
    elif outro_video:
        filter_complex = "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]"
        map_args = ["-map", "[outv]", "-map", "[outa]", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]
        inputs = ["-i", main_video, "-i", outro_video]
    else:
        shutil.copy2(main_video, output_path)
        return

    last_err = ""
    for enc_args in get_encoder_args_candidates():
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            *map_args,
            *enc_args,
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-movflags", "+faststart",
            output_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_path):
            print(f"Final video created: {output_path}")
            return
        last_err = res.stderr[-400:]

    raise RuntimeError(f"FFmpeg assembly failed: {last_err}")


def append_outro(main_video: str, outro_video: str, output_path: str):
    assemble_final_video(
        main_video=main_video,
        output_path=output_path,
        ass_path=None,
        outro_video=outro_video
    )


def _build_sequential_timeline(
    valid_clips: list[str],
    clip_durations: dict[str, float],
    target_duration: float,
    slot_sec: float = 4.0,
    beats_data: list[dict] | None = None,
    hero_clip: str | None = None,
    verified_hero: bool = False,
) -> list[dict]:
    """
    Builds a strictly sequential, beat-synchronized timeline covering `target_duration` seconds:
    - If beats_data is provided: aligns visuals strictly to each narration beat's real audio duration.
      Clips belonging to Beat N NEVER spill over into Beat N+1, preventing narration/visual desync.
    - All cuts are clean, native documentary cuts with zero artificial digital zoom distortion (zoom_factor = 1.0).
    - Uses all available unique clips in natural sequential order without prematurely repeating a clip when unplayed clips exist.
    - Index 0 (hero_clip.mp4) is guaranteed first at 0.0s - 4.0s (Hook) when verified.
    """
    timeline: list[dict] = []

    # 1. Beat-synchronized timeline when beats_data is present
    if beats_data and isinstance(beats_data, list):
        for b in beats_data:
            if "duration" not in b and "start" in b and "end" in b:
                try:
                    b["duration"] = max(0.5, float(b["end"]) - float(b["start"]))
                except (ValueError, TypeError):
                    pass

        has_real_timestamps = all("duration" in b and float(b.get("duration", 0)) > 0 for b in beats_data)
        if has_real_timestamps:
            beat_durations = [round(float(b["duration"]), 3) for b in beats_data]
            delta = round(target_duration - sum(beat_durations), 3)
            if beat_durations:
                beat_durations[-1] = max(0.5, round(beat_durations[-1] + delta, 3))
        else:
            n_beats = max(1, len(beats_data))
            base_beat_dur = round(target_duration / n_beats, 3)
            beat_durations = [base_beat_dur] * n_beats
            delta = round(target_duration - sum(beat_durations), 3)
            if beat_durations:
                beat_durations[-1] = max(0.5, round(beat_durations[-1] + delta, 3))

        clip_usage_global: dict[str, int] = {}
        all_unique_clips = [os.path.abspath(c) for c in valid_clips if os.path.exists(c)]
        played_globally: set[str] = set()

        reserved_by_beat = {
            i: [os.path.abspath(c) for c in b.get("clips", []) if os.path.exists(c)]
            for i, b in enumerate(beats_data)
        }

        for b_idx, (b, b_target_dur) in enumerate(zip(beats_data, beat_durations)):
            b_rem_dur = b_target_dur

            # Special case for Beat 0 (Hook): hero clip placed first
            if b_idx == 0 and verified_hero and hero_clip and os.path.exists(hero_clip):
                h_path = os.path.abspath(hero_clip)
                h_dur = min(4.0, max(2.5, round(b_rem_dur * 0.5, 3)))
                if b_rem_dur - h_dur < 1.5:
                    h_dur = b_rem_dur
                timeline.append({
                    "index": len(timeline),
                    "clip_path": h_path,
                    "ss": 0.0,
                    "duration": h_dur,
                    "beat_idx": 0,
                    "zoom_factor": 1.0,
                })
                clip_usage_global[h_path] = clip_usage_global.get(h_path, 0) + 1
                played_globally.add(h_path)
                b_rem_dur = round(b_rem_dur - h_dur, 3)
                if b_rem_dur <= 0.2:
                    continue

            # Clips belonging specifically to this beat
            raw_b_clips = reserved_by_beat[b_idx]
            if not raw_b_clips:
                unplayed = [c for c in all_unique_clips if c not in played_globally]
                raw_b_clips = unplayed if unplayed else all_unique_clips

            n_clips = len(raw_b_clips)
            num_cuts = max(n_clips, max(1, round(b_rem_dur / 4.0)))
            cut_duration = round(b_rem_dur / num_cuts, 3)

            # Future clips reserved for subsequent beats
            future_reserved = set()
            for future_idx in range(b_idx + 1, len(beats_data)):
                future_reserved.update(reserved_by_beat[future_idx])

            b_accum = 0.0
            for cut_idx in range(num_cuts):
                if cut_idx < n_clips:
                    clip_path = raw_b_clips[cut_idx]
                else:
                    # Extra cut needed: use available unique clips in natural sequential order
                    # without prematurely repeating a clip when unplayed clips exist
                    available_unplayed = [
                        c for c in all_unique_clips
                        if c not in played_globally and c not in future_reserved
                    ]
                    if available_unplayed:
                        clip_path = available_unplayed[0]
                    else:
                        clip_path = raw_b_clips[cut_idx % n_clips]

                src_dur = max(0.5, clip_durations.get(clip_path, 4.0))

                if cut_idx == num_cuts - 1:
                    seg_dur = max(0.5, round(b_rem_dur - b_accum, 3))
                else:
                    seg_dur = min(b_rem_dur - b_accum, cut_duration)

                times_used = clip_usage_global.get(clip_path, 0)
                max_offset = max(0.0, src_dur - seg_dur)
                if times_used > 0 and max_offset > 0.5:
                    ss = min(max_offset, round((times_used * 4.5) % (max_offset + 0.01), 2))
                else:
                    ss = 0.0

                # Clean native documentary cuts: zoom_factor is strictly 1.0
                timeline.append({
                    "index": len(timeline),
                    "clip_path": clip_path,
                    "ss": ss,
                    "duration": seg_dur,
                    "beat_idx": b_idx,
                    "zoom_factor": 1.0,
                })
                clip_usage_global[clip_path] = times_used + 1
                played_globally.add(clip_path)
                b_accum = round(b_accum + seg_dur, 3)

        return timeline

    # 2. Fallback when beats_data is None: strict sequential + clean cuts without zoom distortion
    accumulated = 0.0
    needed_with_pad = target_duration + 0.15
    clip_usage: dict[str, int] = {}
    played_globally: set[str] = set()

    for idx, clip_path in enumerate(valid_clips):
        if accumulated >= needed_with_pad:
            break
        src_dur = max(0.5, clip_durations.get(clip_path, slot_sec))
        seg_dur = min(slot_sec, src_dur)
        timeline.append({
            "index": len(timeline),
            "clip_path": clip_path,
            "ss": 0.0,
            "duration": seg_dur,
            "zoom_factor": 1.0,
        })
        clip_usage[clip_path] = 1
        played_globally.add(clip_path)
        accumulated += seg_dur

    while accumulated < needed_with_pad:
        support_pool = [c for c in valid_clips if c not in played_globally] or (valid_clips[1:] if len(valid_clips) > 1 else valid_clips)
        if not support_pool:
            break
        for clip_path in support_pool:
            if accumulated >= needed_with_pad:
                break
            src_dur = max(0.5, clip_durations.get(clip_path, slot_sec))
            seg_dur = min(slot_sec, src_dur)
            times_used = clip_usage.get(clip_path, 1)
            max_offset = max(0.0, src_dur - seg_dur)
            ss = min(max_offset, round((times_used * 4.5) % (max_offset + 0.01), 2)) if max_offset > 0.5 else 0.0
            timeline.append({
                "index": len(timeline),
                "clip_path": clip_path,
                "ss": ss,
                "duration": seg_dur,
                "zoom_factor": 1.0,
            })
            clip_usage[clip_path] = times_used + 1
            played_globally.add(clip_path)
            accumulated += seg_dur

    return timeline


def _normalize_single_segment(seg: dict, work_dir: str) -> str:
    out_seg = os.path.join(work_dir, f"seg_{seg['index']:03d}.mp4")
    dur_s = seg["duration"]
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,fps=30,setsar=1,"
        f"tpad=stop_mode=clone:stop_duration=1.0,trim=0:{dur_s:.3f},setpts=PTS-STARTPTS,format=yuv420p"
    )
    last_err = ""
    for enc_args in get_encoder_args_candidates():
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{seg['ss']:.3f}",
            "-i", seg["clip_path"],
            "-t", f"{dur_s:.3f}",
            "-vf", vf,
            "-an",
            *enc_args,
            "-r", "30",
            "-video_track_timescale", "15360",
            out_seg
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(out_seg):
            return out_seg
        last_err = res.stderr[-300:]
    raise RuntimeError(f"Failed normalizing clip {seg['clip_path']}: {last_err}")


def _pick_random_bgm() -> str | None:
    candidates = []
    songs_dirs = [
        os.path.join(ENGINE_DIR, "resource", "songs"),
        os.path.join(ROOT_DIR, "assets", "bgm"),
        os.path.join(ROOT_DIR, "assets", "songs"),
    ]
    for sdir in songs_dirs:
        if os.path.exists(sdir):
            candidates.extend(glob.glob(os.path.join(sdir, "*.mp3")))
    return random.choice(candidates) if candidates else None


def fast_ffmpeg_render(
    *,
    task_id: str,
    full_script: str,
    final_voice: str,
    language: str,
    subtitle_style: str,
    subtitle_color: str,
    subtitle_box: bool,
    approved_clips: list[str],
    dest_path: str,
    script_json_path: str,
    channel_name: str | None,
    niche: str | None,
    no_outro: bool,
    bgm_volume: float = 0.20,
    voice_rate: str = "+0%",
    beats_data: list[dict] | None = None,
    hero_clip: str | None = None,
    verified_hero: bool = False,
) -> int:
    _ensure_python_deps(require_mpt_cli=False)
    t_start = time.time()
    timings: dict[str, float] = {}

    valid_clips = [os.path.abspath(c) for c in approved_clips if os.path.exists(c)]
    if not valid_clips:
        raise FileNotFoundError("Ninguno de los clips en approved_materials.json existe en disco.")

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    work_dir = os.path.join(os.path.dirname(dest_path), f".render_work_{task_id[:8]}")
    os.makedirs(work_dir, exist_ok=True)

    try:
        # Phase 1 & 2 (CONCURRENT): Edge-TTS + Subtitles IN PARALLEL WITH Clip Probing & Personalized Outro!
        t0 = time.time()
        from generate_animated_subtitles import generate_animated_subtitles

        speech_audio = os.path.join(work_dir, "speech.mp3")
        ass_path = os.path.join(work_dir, "dynamic_subtitles.ass")
        outro_path = os.path.join(work_dir, "dynamic_outro.mp4")
        last_clip_frame = os.path.join(work_dir, "last_clip_frame.jpg")

        def _tts_and_subs_task(rate_val: str = voice_rate) -> dict:
            print(f"[1/3] Generating Edge-TTS voice & '{subtitle_style}' subtitles (Voice: {final_voice}, Rate: {rate_val})...")
            res_s = generate_animated_subtitles(
                text=full_script,
                voice=final_voice,
                output_audio=speech_audio,
                output_ass=ass_path,
                style=subtitle_style,
                accent_color=subtitle_color,
                words_per_line=3,
                box_background=subtitle_box,
                voice_rate=rate_val,
                script_data={"full_script": full_script, "visual_beats": beats_data} if beats_data else None,
            )
            res_s["probed_duration"] = probe_media_duration(speech_audio, default=res_s.get("duration_seconds", 60.0))
            return res_s

        def _probe_and_outro_task() -> tuple[dict[str, float], str | None]:
            with ThreadPoolExecutor(max_workers=8) as probe_pool:
                durs = list(probe_pool.map(probe_media_duration, valid_clips))
            c_durs = dict(zip(valid_clips, durs))

            if no_outro:
                return c_durs, None

            # Extract background frame from the last approved clip so outro renders simultaneously with TTS
            bg_clip = valid_clips[-1]
            bg_ts = max(0.0, min(3.5, c_durs.get(bg_clip, 4.0) - 0.3))
            subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", f"{bg_ts:.2f}", "-i", bg_clip,
                    "-frames:v", "1", "-q:v", "2", last_clip_frame
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            try:
                from create_generic_outro import create_outro_video
                create_outro_video(
                    output_path=outro_path,
                    source_frame=last_clip_frame if os.path.exists(last_clip_frame) else None,
                    channel_name=channel_name,
                    niche=niche,
                    language=language,
                    voice=final_voice
                )
                if os.path.exists(outro_path):
                    return c_durs, outro_path
            except Exception as e:
                print(f"Warning: Dynamic outro failed ({e}), checking fallback...")
            fallback = os.path.join(ROOT_DIR, "assets", "outro_generico.mp4")
            return c_durs, (fallback if os.path.exists(fallback) else None)

        with ThreadPoolExecutor(max_workers=2) as prep_pool:
            fut_tts = prep_pool.submit(_tts_and_subs_task)
            fut_outro = prep_pool.submit(_probe_and_outro_task)
            sub_res = fut_tts.result()
            clip_durations, outro_to_use = fut_outro.result()

        # Align beats_data to exact audio timestamps returned from Edge-TTS cues
        if beats_data and sub_res.get("beat_timestamps"):
            for i, b in enumerate(beats_data):
                if i < len(sub_res["beat_timestamps"]):
                    bt = sub_res["beat_timestamps"][i]
                    b["duration"] = bt["duration"]
                    b["start"] = bt["start"]
                    b["end"] = bt["end"]

        speech_dur = sub_res["probed_duration"]
        outro_dur = probe_media_duration(outro_to_use, default=4.2) if (outro_to_use and os.path.exists(outro_to_use)) else 0.0
        predicted_total = speech_dur + outro_dur

        # Automatic Pre-Render Monetization Window Calibration (62.0s - 72.0s, target ~66.8s)
        if voice_rate == "+0%" and (predicted_total < 62.8 or predicted_total > 71.2):
            ideal_speech = max(55.0, 66.8 - outro_dur)
            ratio = speech_dur / ideal_speech
            # If within natural speech cadence (-20% to +25%), auto-recalibrate TTS + ASS before GPU render!
            if 0.78 <= ratio <= 1.26:
                pct_delta = max(-20, min(25, int(round((ratio - 1.0) * 100))))
                if pct_delta != 0:
                    auto_rate = f"{pct_delta:+d}%"
                    print(
                        f"[Auto-Pacing] Predicted total {predicted_total:.2f}s outside safe 62.8-71.2s window. "
                        f"Recalibrating Edge-TTS + ASS with rate='{auto_rate}'..."
                    )
                    sub_res = _tts_and_subs_task(auto_rate)
                    speech_dur = sub_res["probed_duration"]
                    voice_rate = auto_rate
                    if beats_data and sub_res.get("beat_timestamps"):
                        for i, b in enumerate(beats_data):
                            if i < len(sub_res["beat_timestamps"]):
                                bt = sub_res["beat_timestamps"][i]
                                b["duration"] = bt["duration"]
                                b["start"] = bt["start"]
                                b["end"] = bt["end"]

        timings["parallel_tts_subs_and_outro"] = round(time.time() - t0, 2)

        # Phase 2: Build Strict Sequential Beat-Synchronized Timeline & Single-Generation Direct GPU Filtergraph
        t2 = time.time()
        timeline = _build_sequential_timeline(
            valid_clips=valid_clips,
            clip_durations=clip_durations,
            target_duration=speech_dur,
            slot_sec=4.0,
            beats_data=beats_data,
            hero_clip=hero_clip,
            verified_hero=verified_hero,
        )
        print(f"[2/3] Single-pass GPU assembly of {len(timeline)} sequential slots (Hook #0: {os.path.basename(timeline[0]['clip_path'])}, beat_sync={bool(beats_data)})...")

        inputs: list[str] = []
        filter_parts: list[str] = []
        v_labels: list[str] = []

        for idx, seg in enumerate(timeline):
            dur_s = seg["duration"]
            # Cap input demuxer read to dur_s + 0.5s for instant pull-based decoding
            inputs.extend([
                "-ss", f"{seg['ss']:.3f}",
                "-t", f"{dur_s + 0.5:.3f}",
                "-i", seg["clip_path"]
            ])
            # Clean native documentary cuts: always 1080x1920 cover-crop (no zoom jump-cuts)
            scale_crop_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

            filter_parts.append(
                f"[{idx}:v]{scale_crop_filter},fps=30,setsar=1,"
                f"tpad=stop_mode=clone:stop_duration=1.0,trim=0:{dur_s:.3f},setpts=PTS-STARTPTS,"
                f"format=yuv420p[v{idx}]"
            )
            v_labels.append(f"[v{idx}]")

        speech_idx = len(timeline)
        inputs.extend(["-i", speech_audio])

        bgm_path = _pick_random_bgm()
        escaped_ass = escape_ffmpeg_filter_path(ass_path)

        filter_parts.append(
            f"{''.join(v_labels)}concat=n={len(timeline)}:v=1:a=0,"
            f"trim=0:{speech_dur:.3f},setpts=PTS-STARTPTS,fps=30,format=yuv420p,ass='{escaped_ass}'[mainv]"
        )
        filter_parts.append(
            f"[{speech_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"apad=whole_dur={speech_dur:.3f},atrim=0:{speech_dur:.3f},asetpts=PTS-STARTPTS[voicea]"
        )

        next_idx = speech_idx + 1
        if bgm_path and os.path.exists(bgm_path):
            inputs.extend(["-stream_loop", "-1", "-i", bgm_path])
            filter_parts.append(
                f"[{next_idx}:a]atrim=0:{speech_dur:.3f},asetpts=PTS-STARTPTS,aresample=44100,"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo,volume={bgm_volume:.2f}[bgma]"
            )
            filter_parts.append(
                "[voicea][bgma]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[maina]"
            )
            next_idx += 1
        else:
            filter_parts.append("[voicea]acopy[maina]")

        if outro_to_use and os.path.exists(outro_to_use):
            inputs.extend(["-i", outro_to_use])
            filter_parts.append(
                f"[{next_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,fps=30,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[outrov]"
            )
            filter_parts.append(
                f"[{next_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[outroa]"
            )
            filter_parts.append("[mainv][maina][outrov][outroa]concat=n=2:v=1:a=1[outv][outa]")
            final_v, final_a = "[outv]", "[outa]"
        else:
            final_v, final_a = "[mainv]", "[maina]"

        filter_complex = ";".join(filter_parts)

        used_encoder = "libx264"
        assembled_ok = False
        last_err = ""
        for enc_args in get_encoder_args_candidates():
            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", final_v,
                "-map", final_a,
                *enc_args,
                "-pix_fmt", "yuv420p",
                "-r", "30",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-ac", "2",
                "-movflags", "+faststart",
                dest_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(dest_path):
                assembled_ok = True
                used_encoder = enc_args[1]
                break
            last_err = res.stderr[-500:]

        if not assembled_ok:
            raise RuntimeError(f"Final GPU assembly failed: {last_err}")

        timings["final_gpu_pass"] = round(time.time() - t2, 2)
        total_elapsed = round(time.time() - t_start, 2)
        final_dur = round(probe_media_duration(dest_path, default=speech_dur), 2)

        # Phase 4: Emit render_manifest.json alongside video_script.json
        manifest = {
            "task_id": task_id,
            "engine": "fast_ffmpeg_gpu",
            "video_encoder": used_encoder,
            "output_video": dest_path,
            "measured_duration_seconds": final_dur,
            "speech_duration_seconds": round(speech_dur, 2),
            "outro_duration_seconds": round(outro_dur, 2),
            "voice_rate": voice_rate,
            "resolution": "1080x1920",
            "fps": 30,
            "voice_name": final_voice,
            "subtitle_style": subtitle_style,
            "subtitle_box": subtitle_box,
            "bgm_track": os.path.basename(bgm_path) if bgm_path else None,
            "bgm_volume": bgm_volume,
            "outro_included": bool(outro_to_use),
            "sequential_order_enforced": True,
            "hook_first_clip": timeline[0]["clip_path"],
            "clips_used_count": len(timeline),
            "beat_synchronized": bool(beats_data),
            "phase_timings_seconds": timings,
            "total_render_seconds": total_elapsed
        }
        manifest_path = os.path.join(os.path.dirname(os.path.abspath(script_json_path)), "render_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2, ensure_ascii=False)

        print(f"[4/4] Render complete in {total_elapsed}s ({used_encoder}) | Duration: {final_dur}s -> {dest_path}")
        print(f"Manifest saved: {manifest_path}")
        return 0
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Run video production pipeline with native UTF-8 & GPU acceleration.")
    parser.add_argument("--mode", choices=["materials", "render"], required=True)
    parser.add_argument("--script-json", required=True, help="Path to video_script.json")
    parser.add_argument("--materials-json", default=None, help="Path to approved_materials.json (for render mode)")
    parser.add_argument("--task-id", default=None, help="Task UUID")
    parser.add_argument("--output-video", default=None, help="Destination MP4 path (e.g. videos/slug.mp4)")
    parser.add_argument("--channel", default=None, help="Channel identifier or name for personalized outro")
    parser.add_argument("--no-outro", action="store_true", help="Disable automatic outro appending")
    parser.add_argument("--subtitle-style", choices=["hybrid", "hormozi", "typewriter", "mpt_legacy"], default=None, help="Dynamic subtitle style")
    parser.add_argument("--subtitle-color", default=None, help="Accent color (e.g. yellow, cyan, green)")
    parser.add_argument("--subtitle-box", action="store_true", help="Enable semi-transparent dark box background (default is clean outline)")
    parser.add_argument("--voice-rate", default="+0%", help="Edge-TTS speech rate adjustment (e.g. +10%%, -8%%)")
    parser.add_argument("--legacy-engine", action="store_true", help="Fallback to legacy MoneyPrinterTurbo MoviePy render engine")
    args = parser.parse_args()

    if args.script_json and not os.path.isabs(args.script_json):
        args.script_json = os.path.abspath(os.path.join(INITIAL_CWD, args.script_json))
    if args.materials_json and not os.path.isabs(args.materials_json):
        args.materials_json = os.path.abspath(os.path.join(INITIAL_CWD, args.materials_json))
    if args.output_video and not os.path.isabs(args.output_video):
        args.output_video = os.path.abspath(os.path.join(INITIAL_CWD, args.output_video))

    with open(args.script_json, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    full_script = script_data["full_script"]
    voice_name = script_data.get("voice_name", "es-MX-JorgeNeural")
    task_id = args.task_id or str(uuid.uuid4())

    if args.mode == "materials":
        cli = _load_mpt_cli()
        if cli is None:
            print(f"ERROR: Motor de video no encontrado en {ENGINE_DIR}.", file=sys.stderr)
            return 1

        terms_csv = script_data.get("video_terms_csv", "")
        try:
            import configure_stock_api
            stock_source = configure_stock_api.get_active_stock_source()
            creds = configure_stock_api.load_stock_credentials()
            is_both_mode = (
                creds.get("provider_mode") == "both"
                and bool(creds.get("pexels_api_keys"))
                and bool(creds.get("pixabay_api_keys"))
            )
        except Exception:
            stock_source = "pixabay"
            is_both_mode = False

        base_argv = [
            "--task-id", task_id,
            "--video-script", full_script,
            "--video-aspect", "9:16",
            "--video-clip-duration", "4",
            "--video-concat-mode", "sequential",
        ]
        argv_materials = base_argv + [
            "--video-source", stock_source,
            "--video-terms", terms_csv,
            "--stop-at", "materials"
        ]
        ret = cli.run_cli(argv_materials)

        if is_both_mode and ret != 0 and stock_source == "pexels":
            print("Aviso: Reintentando descarga con Pixabay como respaldo automático...")
            argv_fallback = base_argv + [
                "--video-source", "pixabay",
                "--video-terms", terms_csv,
                "--stop-at", "materials"
            ]
            return cli.run_cli(argv_fallback)
        return ret

    elif args.mode == "render":
        if not args.materials_json:
            raise ValueError("--materials-json is required in render mode")
        with open(args.materials_json, "r", encoding="utf-8") as f:
            materials_data = json.load(f)
        approved_clips = materials_data["approved_clips"]

        # Resolve channel metadata and styling preferences
        channel_name = None
        niche = None
        channel_voice = None
        channel_lang = None
        channel_sub_style = None
        channel_sub_color = None
        channels_file = os.path.join(ROOT_DIR, "config", "channels.json")
        if os.path.exists(channels_file):
            try:
                with open(channels_file, "r", encoding="utf-8") as f:
                    ch_data = json.load(f)
                active_id = args.channel or script_data.get("channel") or ch_data.get("active_default_channel")
                channels = ch_data.get("channels", {})
                if active_id and active_id in channels:
                    ch_info = channels[active_id]
                elif len(channels) == 1:
                    ch_info = next(iter(channels.values()))
                else:
                    ch_info = {}
                channel_name = ch_info.get("name")
                niche = ch_info.get("niche")
                channel_voice = ch_info.get("voice_preference")
                channel_lang = ch_info.get("language")
                channel_sub_style = ch_info.get("subtitle_style")
                channel_sub_color = ch_info.get("subtitle_color")
            except Exception:
                pass

        if not channel_name and script_data.get("channel_name"):
            channel_name = script_data.get("channel_name")
        if not channel_name and script_data.get("channel"):
            channel_name = str(script_data.get("channel")).replace("_", " ").title()
        if not niche and script_data.get("niche"):
            niche = script_data.get("niche")

        language = script_data.get("language", channel_lang or "es")
        final_voice = script_data.get("voice_name", channel_voice or voice_name)
        subtitle_style = args.subtitle_style or script_data.get("subtitle_style") or channel_sub_style or "hormozi"
        subtitle_color = args.subtitle_color or script_data.get("subtitle_color") or channel_sub_color or "yellow"

        default_out = os.path.join(ROOT_DIR, "videos", f"render_{task_id[:8]}.mp4")
        dest_path = os.path.abspath(args.output_video) if args.output_video else default_out

        # Extract beat-synchronization and hero assets if present
        beats_data = materials_data.get("beats")
        hero_clip = materials_data.get("hero_clip")
        verified_hero = bool(materials_data.get("verified_real_photo") and hero_clip and os.path.exists(hero_clip))

        # Default fast path: Direct FFmpeg + GPU Engine
        if not args.legacy_engine and subtitle_style != "mpt_legacy":
            return fast_ffmpeg_render(
                task_id=task_id,
                full_script=full_script,
                final_voice=final_voice,
                language=language,
                subtitle_style=subtitle_style,
                subtitle_color=subtitle_color,
                subtitle_box=args.subtitle_box,
                approved_clips=approved_clips,
                dest_path=dest_path,
                script_json_path=args.script_json,
                channel_name=channel_name,
                niche=niche,
                no_outro=args.no_outro,
                voice_rate=args.voice_rate,
                beats_data=beats_data,
                hero_clip=hero_clip,
                verified_hero=verified_hero,
            )

        # Fallback path: Legacy MoneyPrinterTurbo CLI (with sequential order enforced)
        cli = _load_mpt_cli()
        if cli is None:
            print(f"ERROR: Motor de video no encontrado en {ENGINE_DIR}.", file=sys.stderr)
            return 1

        clips_csv = ",".join(approved_clips)
        argv = [
            "--task-id", task_id,
            "--video-script", full_script,
            "--video-aspect", "9:16",
            "--video-clip-duration", "4",
            "--video-concat-mode", "sequential",
            "--bgm-type", "random",
            "--bgm-volume", "0.2",
        ]

        dynamic_ass_path = None
        if subtitle_style != "mpt_legacy":
            from generate_animated_subtitles import generate_animated_subtitles
            task_dir = os.path.join(ENGINE_DIR, "storage", "tasks", task_id)
            os.makedirs(task_dir, exist_ok=True)
            custom_speech_audio = os.path.join(task_dir, "speech.mp3")
            dynamic_ass_path = os.path.join(task_dir, "dynamic_subtitles.ass")

            generate_animated_subtitles(
                text=full_script,
                voice=final_voice,
                output_audio=custom_speech_audio,
                output_ass=dynamic_ass_path,
                style=subtitle_style,
                accent_color=subtitle_color,
                words_per_line=3,
                box_background=args.subtitle_box
            )
            argv.extend([
                "--video-source", "local",
                "--video-materials", clips_csv,
                "--custom-audio-file", custom_speech_audio,
                "--no-subtitle-enabled",
                "--stop-at", "video"
            ])
        else:
            argv.extend([
                "--subtitle-enabled",
                "--subtitle-position", "custom",
                "--custom-position", "58.0",
                "--video-source", "local",
                "--video-materials", clips_csv,
                "--voice-name", final_voice,
                "--stop-at", "video"
            ])
            if args.subtitle_box:
                argv.extend([
                    "--subtitle-background-enabled",
                    "--subtitle-background-color", "#000000",
                    "--rounded-subtitle-background",
                ])
            else:
                argv.append("--no-subtitle-background-enabled")

        ret = cli.run_cli(argv)
        if ret != 0:
            return ret

        raw_final = os.path.join(ENGINE_DIR, "storage", "tasks", task_id, "final-1.mp4")
        if not os.path.exists(raw_final):
            print(f"Warning: Expected final video not found at {raw_final}")
            return ret

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        outro_to_use = None
        temp_dynamic_outro = None
        if not args.no_outro:
            temp_dynamic_outro = raw_final + ".dynamic_outro.mp4"
            try:
                from create_generic_outro import create_outro_video
                create_outro_video(
                    output_path=temp_dynamic_outro,
                    video_path=raw_final,
                    channel_name=channel_name,
                    niche=niche,
                    language=language,
                    voice=final_voice
                )
                if os.path.exists(temp_dynamic_outro):
                    outro_to_use = temp_dynamic_outro
            except Exception as e:
                print(f"Warning: Failed to generate personalized outro ({e}).")
            if not outro_to_use:
                generic_fallback = os.path.join(ROOT_DIR, "assets", "outro_generico.mp4")
                if os.path.exists(generic_fallback):
                    outro_to_use = generic_fallback

        temp_assembled = raw_final + ".assembled.mp4"
        assemble_final_video(
            main_video=raw_final,
            output_path=temp_assembled,
            ass_path=dynamic_ass_path,
            outro_video=outro_to_use
        )
        shutil.move(temp_assembled, dest_path)
        if temp_dynamic_outro and os.path.exists(temp_dynamic_outro):
            try:
                os.remove(temp_dynamic_outro)
            except OSError:
                pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
