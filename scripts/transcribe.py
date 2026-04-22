#!/usr/bin/env python3
"""Download media + transcribe via local Whisper.

Pipeline:
  1. Skip if entry already has transcript (unless --force).
  2. If no media_url, try to resolve via yt-dlp (handles IG reels, YouTube, etc.).
  3. Download audio-only mp3 via yt-dlp.
  4. Transcribe with faster-whisper (preferred) or openai-whisper.
  5. Persist transcript + metadata back to parquet via the CMS upsert path.

Usage:
  python scripts/transcribe.py --all                # all entries without transcripts
  python scripts/transcribe.py --id <entry_id>      # single entry
  python scripts/transcribe.py --limit 5            # first 5 missing
  python scripts/transcribe.py --model small        # whisper model size

Dependencies (install as needed; all local):
  pip install yt-dlp faster-whisper        # preferred
  pip install yt-dlp openai-whisper        # fallback

yt-dlp may need ffmpeg on PATH for audio extraction. On Windows, install
ffmpeg via scoop or direct download and ensure `ffmpeg` resolves in bash.
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from cms import load_entries, write_entries, compute_crosslinks, write_crosslinks, _write_catalog_exports  # noqa


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _has_ytdlp() -> bool:
    return shutil.which("yt-dlp") is not None or _import_ok("yt_dlp")


def _import_ok(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


def download_audio(url: str, out_dir: Path) -> Path | None:
    """Download audio-only as mp3 via yt-dlp. Returns the file path, or None."""
    try:
        import yt_dlp  # type: ignore
    except ImportError:
        print("[transcribe] yt-dlp not installed — `pip install yt-dlp`", file=sys.stderr)
        return None

    out_tmpl = str(out_dir / "%(id)s.%(ext)s")
    opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": out_tmpl,
        "format": "bestaudio/best",
    }
    if _has_ffmpeg() and shutil.which("ffprobe"):
        import subprocess as _sp
        try:
            r = _sp.run(["ffprobe", "-version"], capture_output=True, text=True, timeout=5)
            if "ffprobe" in r.stdout:
                opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}]
        except Exception:
            pass
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        print(f"[transcribe] download failed: {e}", file=sys.stderr)
        return None

    stem = info.get("id") if info else None
    if stem:
        for ext in ("mp3", "m4a", "webm", "ogg", "opus", "wav"):
            cand = out_dir / f"{stem}.{ext}"
            if cand.exists():
                return cand
    audio_files = list(out_dir.glob("*.*"))
    return audio_files[0] if audio_files else None


def _convert_to_wav(audio: Path) -> Path | None:
    """Convert audio to wav using ffmpeg for whisper compatibility."""
    wav = audio.with_suffix(".wav")
    if wav.exists():
        return wav
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            return None
    try:
        subprocess.run([ffmpeg, "-i", str(audio), "-ar", "16000", "-ac", "1", "-y", str(wav)],
                       capture_output=True, timeout=60)
        return wav if wav.exists() else None
    except Exception:
        return None


def transcribe_local(audio: Path, model_size: str = "small") -> str | None:
    """Run faster-whisper first, fall back to openai-whisper."""
    if audio.suffix not in (".wav", ".mp3") and _has_ffmpeg():
        converted = _convert_to_wav(audio)
        if converted:
            audio = converted
    if _import_ok("faster_whisper"):
        try:
            from faster_whisper import WhisperModel  # type: ignore
            print(f"[transcribe] faster-whisper({model_size}) on {audio.name}")
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            segments, _info = model.transcribe(str(audio), vad_filter=True)
            return " ".join(s.text.strip() for s in segments).strip()
        except Exception as e:
            print(f"[transcribe] faster-whisper failed: {e}", file=sys.stderr)

    if _import_ok("whisper"):
        try:
            import whisper  # type: ignore
            print(f"[transcribe] openai-whisper({model_size}) on {audio.name}")
            model = whisper.load_model(model_size)
            result = model.transcribe(str(audio))
            return (result.get("text") or "").strip()
        except Exception as e:
            print(f"[transcribe] openai-whisper failed: {e}", file=sys.stderr)
            return None

    print("[transcribe] no whisper library installed — "
          "`pip install faster-whisper` (preferred) or `pip install openai-whisper`",
          file=sys.stderr)
    return None


def transcribe_one(row: dict, model_size: str, out_dir: Path) -> tuple[dict, str]:
    """Returns (updated_row, action). action ∈ {skipped-has, skipped-no-video, ok, failed}."""
    if row.get("transcript"):
        return row, "skipped-has"
    media_type = (row.get("media_type") or "").lower()
    # Only attempt video-ish entries
    if media_type and media_type not in ("video", "reel", "mp4"):
        return row, "skipped-no-video"

    url = row.get("url")
    if not url:
        return row, "skipped-no-video"

    audio = download_audio(url, out_dir)
    if not audio:
        return row, "failed"

    text = transcribe_local(audio, model_size)
    if text is None:
        return row, "failed"

    row = dict(row)
    row["transcript"] = text or "(no speech detected)"
    row["transcript_source"] = "whisper_local"
    row["transcript_at"] = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
    return row, "ok"


def main(argv=None):
    p = argparse.ArgumentParser(prog="transcribe")
    p.add_argument("--id", help="single entry id")
    p.add_argument("--all", action="store_true", help="all entries missing transcript")
    p.add_argument("--limit", type=int, default=0, help="cap number of entries")
    p.add_argument("--model", default="small", help="whisper model size (tiny/base/small/medium/large)")
    p.add_argument("--force", action="store_true", help="overwrite existing transcripts")
    args = p.parse_args(argv)

    if not _has_ffmpeg():
        print("[transcribe] WARN: ffmpeg not on PATH — yt-dlp audio extraction will fail.",
              file=sys.stderr)
    if not _has_ytdlp():
        print("[transcribe] ERROR: yt-dlp not available. `pip install yt-dlp`", file=sys.stderr)
        return 1

    rows = load_entries()
    if not rows:
        print("[transcribe] no entries — run `python scripts/cms.py migrate` first", file=sys.stderr)
        return 1

    if args.id:
        targets = [r for r in rows if r.get("id") == args.id]
        if not targets:
            print(f"[transcribe] id not found: {args.id}", file=sys.stderr); return 1
    elif args.all:
        targets = [
            r for r in rows
            if (args.force or not r.get("transcript"))
            and (r.get("media_type") or "").lower() in ("video", "reel", "mp4")
        ]
    else:
        print("[transcribe] specify --id <id> or --all", file=sys.stderr); return 1

    if args.limit:
        targets = targets[: args.limit]

    print(f"[transcribe] {len(targets)} target(s), model={args.model}")

    tmp = Path(tempfile.mkdtemp(prefix="dv-transcribe-"))
    try:
        counts = {"ok": 0, "failed": 0, "skipped-has": 0, "skipped-no-video": 0}
        by_id = {r["id"]: r for r in rows}
        for i, row in enumerate(targets, 1):
            print(f"[transcribe] ({i}/{len(targets)}) {row.get('id')} · {(row.get('title') or '')[:60]}")
            new_row, action = transcribe_one(row, args.model, tmp)
            counts[action] = counts.get(action, 0) + 1
            if action == "ok":
                by_id[new_row["id"]] = new_row
                # Persist incrementally so a crash doesn't waste earlier work
                write_entries(list(by_id.values()))
                print(f"  -> {len(new_row['transcript'])} chars transcribed")
            else:
                print(f"  -> {action}")

        new_rows = list(by_id.values())
        write_entries(new_rows)
        links = compute_crosslinks(new_rows)
        write_crosslinks(links)
        _write_catalog_exports(new_rows)
        print(f"[transcribe] done: {counts}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
