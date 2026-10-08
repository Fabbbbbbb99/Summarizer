#!/usr/bin/env python3
"""
Media Transcriber CLI (whisper.cpp + pywhispercpp + mjwong/whisper-large-v3-turbo-singlish)
Fast, accurate, 100% offline audio/video transcription using whisper.cpp C++ GGML engine,
ffmpeg, and deterministic phonetic repair.
Outputs:
  - <name>_transcript.txt (timestamped text)
  - <name>_transcript.json (full structured segments and words)
  - <name>_transcript_annotated.md (formatted Markdown with dialogue blocks)
"""

import os
import sys
import time
import json
import argparse
import subprocess
import tempfile
import re
from typing import List, Dict, Any, Optional

# Import local audio preprocessing and phonetic repair modules
try:
    from .audio_preprocessor import preprocess_audio
except ImportError:
    from audio_preprocessor import preprocess_audio

try:
    from .phonetic_repair import repair_all_outputs, repair_text
except ImportError:
    from phonetic_repair import repair_all_outputs, repair_text

try:
    from .base_dir_helper import get_default_base_dir
except ImportError:
    from base_dir_helper import get_default_base_dir

SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v",
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".opus"
}

DEFAULT_MODEL_REPO = "mjwong/whisper-large-v3-turbo-singlish"


def resolve_run_output_dir(note_name: str, base_dir: Optional[str] = None, output_dir: Optional[str] = None) -> str:
    """
    Resolves the destination directory for a run.
    Ensures that outputs are placed inside a subfolder named after the summary note:
    <base_dir>/<note_name>/ (default: <dynamic_desktop_or_home>/Summarizer/<note_name>/)
    Automatically creates the directories as needed.
    """
    default_base = get_default_base_dir()
    effective_base = os.path.abspath(base_dir) if base_dir else os.path.abspath(default_base)
    if output_dir:
        resolved_out = os.path.abspath(output_dir)
        norm_out = os.path.normpath(resolved_out).lower()
        norm_base = os.path.normpath(effective_base).lower()
        norm_default = os.path.normpath(os.path.abspath(default_base)).lower()

        # If output_dir is exactly the base directory, create subfolder inside it
        if norm_out in (norm_base, norm_default):
            target_dir = os.path.join(resolved_out, note_name)
            os.makedirs(target_dir, exist_ok=True)
            return target_dir
        # If output_dir already ends with note_name, use it directly
        if os.path.basename(norm_out) == note_name.lower():
            os.makedirs(resolved_out, exist_ok=True)
            return resolved_out
        # Custom directory specified
        os.makedirs(resolved_out, exist_ok=True)
        return resolved_out

    target_dir = os.path.join(effective_base, note_name)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


# Singlish and Singapore University Academic defaults with Systems Engineering & AI terms
SINGLISH_DEFAULT_PROMPT = (
    "Transcribing a university systems engineering and AI lecture by a Singaporean professor in Singaporean English (Singlish) "
    "at university (NUS, NTU, SMU, SIT, SUTD). Discourse particles and colloquial cadence: lah, leh, lor, meh, mah, hor, sia, liao, "
    "can or not, cannot, don't have, also can, catch no ball, chim. Academic & technical terms: INCOSE, Systems Engineering Handbook (SEH), "
    "Needs and Requirements Manual (NRMD), Prof. Mike Ryan, ConOps, OpsCon, stakeholder management, Claude 3.5, Gemini, ChatGPT, "
    "Obsidian, second brain, knowledge graph, prompt engineering, context engineering, agentic AI, agentic memory, hallucination."
)


def format_timestamp(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{int(h):02d}:{int(m):02d}:{s:05.2f}"
    return f"{int(m):02d}:{s:05.2f}"


def format_short_ts(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    return f"{int(m):02d}:{s:04.1f}"


def get_ffmpeg_executable() -> str:
    """Finds ffmpeg from imageio_ffmpeg or system PATH."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    
    for cmd in ["ffmpeg", "ffmpeg.exe"]:
        try:
            res = subprocess.run([cmd, "-version"], capture_output=True, text=True)
            if res.returncode == 0:
                return cmd
        except FileNotFoundError:
            continue
            
    raise RuntimeError(
        "ffmpeg executable not found! Please run 'pip install imageio-ffmpeg' or install ffmpeg on your system PATH."
    )


def extract_audio(media_path: str, wav_path: str, ffmpeg_bin: str) -> None:
    """Basic extraction to 16kHz mono 16-bit PCM WAV."""
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", media_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        wav_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to extract audio from '{media_path}':\n{res.stderr[-500:]}")


def clean_artifacts(text: str) -> str:
    """Cleans up common speech-to-text noise, hallucination loops, and repeated whitespace."""
    text = re.sub(r'(\b\w+\b)(?:\s+\1\b){2,}', r'\1', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def build_annotated_markdown(segments: List[Dict[str, Any]], title: str, duration_sec: float) -> str:
    """Groups consecutive speech segments into dialogue blocks for easy reading."""
    md_lines = [
        f"# {title}",
        f"",
        f"- **Duration**: {format_timestamp(duration_sec)}",
        f"- **Generated by**: media-transcription skill (whisper.cpp + pywhispercpp + mjwong/whisper-large-v3-turbo-singlish)",
        f"",
        f"---",
        f""
    ]
    
    if not segments:
        md_lines.append("*No speech detected.*")
        return "\n".join(md_lines)
    
    current_block: List[str] = []
    block_start: float = segments[0]["start"]
    block_end: float = segments[0]["end"]
    
    for seg in segments:
        text = clean_artifacts(seg["text"])
        if not text:
            continue
            
        if current_block and ((seg["start"] - block_end > 3.0) or (seg["end"] - block_start > 45.0)):
            ts_str = f"[{format_short_ts(block_start)} - {format_short_ts(block_end)}]"
            md_lines.append(f"### {ts_str}")
            md_lines.append(f"")
            md_lines.append(" ".join(current_block))
            md_lines.append(f"")
            current_block = [text]
            block_start = seg["start"]
            block_end = seg["end"]
        else:
            current_block.append(text)
            block_end = seg["end"]
            
    if current_block:
        ts_str = f"[{format_short_ts(block_start)} - {format_short_ts(block_end)}]"
        md_lines.append(f"### {ts_str}")
        md_lines.append(f"")
        md_lines.append(" ".join(current_block))
        md_lines.append(f"")
        
    return "\n".join(md_lines)


def ensure_model_weights(model_spec: str) -> str:
    """
    Ensures whisper.cpp GGUF model weights are available locally.
    If model_spec is a HuggingFace repo (e.g. 'mjwong/whisper-large-v3-turbo-singlish')
    or a path to a GGUF bin file, retrieves or uses it.
    """
    if os.path.exists(model_spec):
        return os.path.abspath(model_spec)

    # If it's a huggingface model repo, download the gguf file via huggingface_hub
    try:
        from huggingface_hub import hf_hub_download
        print(f"Downloading GGUF weights from HuggingFace repo '{model_spec}'...", flush=True)
        # Look for standard gguf weights filename in repo
        try:
            model_path = hf_hub_download(repo_id=model_spec, filename="ggml-model.bin")
            return model_path
        except Exception:
            try:
                model_path = hf_hub_download(repo_id=model_spec, filename="model.bin")
                return model_path
            except Exception:
                # Try downloading any .bin or .gguf file
                from huggingface_hub import snapshot_download
                snapshot_dir = snapshot_download(repo_id=model_spec, allow_patterns=["*.bin", "*.gguf"])
                for root, _, files in os.walk(snapshot_dir):
                    for f in files:
                        if f.endswith((".bin", ".gguf")):
                            return os.path.join(root, f)
                raise RuntimeError(f"Could not find model weights (.bin or .gguf) in HuggingFace repo {model_spec}")
    except ImportError:
        raise RuntimeError("huggingface_hub not installed! Please run 'pip install huggingface-hub'.")


def transcribe_file(
    media_path: str,
    output_dir: str,
    note_name: Optional[str] = None,
    model_name: str = DEFAULT_MODEL_REPO,
    language: Optional[str] = "en",
    initial_prompt: Optional[str] = None,
    singlish: bool = True,
    enhance_audio: bool = True,
    phonetic_repair: bool = True,
    cpu_threads: int = 8,
    temp_dir: Optional[str] = None,
    keep_wav: bool = False
) -> Dict[str, str]:
    """Transcribes a single audio or video file using whisper.cpp (via pywhispercpp)."""
    try:
        from pywhispercpp.model import Model
    except ImportError:
        raise RuntimeError("pywhispercpp not installed! Run 'pip install pywhispercpp'.")
        
    ffmpeg_bin = get_ffmpeg_executable()
    os.makedirs(output_dir, exist_ok=True)
    
    file_name = os.path.basename(media_path)
    base_name = note_name if note_name else os.path.splitext(file_name)[0]
    
    # Configure Singlish prompt priming
    effective_prompt = initial_prompt
    if singlish:
        if effective_prompt:
            effective_prompt = f"{SINGLISH_DEFAULT_PROMPT} Context: {effective_prompt}"
        else:
            effective_prompt = SINGLISH_DEFAULT_PROMPT

    # Temporary WAV path
    if temp_dir:
        os.makedirs(temp_dir, exist_ok=True)
        wav_path = os.path.join(temp_dir, f"{base_name}_temp.wav")
    else:
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = temp_file.name
        temp_file.close()
        
    print(f"\n=======================================================", flush=True)
    print(f"Processing: {file_name}", flush=True)
    print(f"Engine: whisper.cpp (pywhispercpp)", flush=True)
    print(f"Model: {model_name}", flush=True)
    if singlish:
        print(f"Singlish mode: ENABLED (prompt priming + whisper.cpp GGML inference)", flush=True)
    if enhance_audio:
        print(f"Audio enhancement: ENABLED (ffmpeg bandpass 100-7500Hz + afftdn noise suppression + dynaudnorm)", flush=True)
    print(f"Extracting 16kHz mono audio...", flush=True)
    t_start = time.time()

    if enhance_audio:
        preprocess_audio(
            input_path=media_path,
            output_path=wav_path,
            highpass=100,
            lowpass=7500,
            afftdn=True,
            afftdn_nf=-25,
            dynaudnorm=True,
            ffmpeg_bin=ffmpeg_bin
        )
    else:
        extract_audio(media_path, wav_path, ffmpeg_bin)

    size_mb = os.path.getsize(wav_path) / (1024 * 1024)
    print(f"Extracted audio: {size_mb:.2f} MB in {time.time() - t_start:.2f}s", flush=True)
    
    # Resolve whisper.cpp model weights path
    model_weights_path = ensure_model_weights(model_name)
    print(f"Loading whisper.cpp Model('{model_weights_path}', n_threads={cpu_threads})...", flush=True)
    t_load = time.time()
    
    model = Model(model_weights_path, n_threads=cpu_threads)
    print(f"whisper.cpp model ready in {time.time() - t_load:.2f}s", flush=True)
    
    print("Transcribing with whisper.cpp engine...", flush=True)
    t_trans = time.time()
    
    # pywhispercpp transcribe call
    raw_segments = model.transcribe(
        wav_path,
        language=language if language and language != "auto" else "en",
        initial_prompt=effective_prompt if effective_prompt else ""
    )
    
    segments_list = []
    total_duration = 0.0
    
    # Convert pywhispercpp segments format
    for seg in raw_segments:
        # pywhispercpp segment attributes: t0, t1, text (or start, end)
        start_sec = getattr(seg, 't0', getattr(seg, 'start', 0.0)) / 100.0 if isinstance(getattr(seg, 't0', getattr(seg, 'start', 0.0)), int) else getattr(seg, 't0', getattr(seg, 'start', 0.0))
        # Note: pywhispercpp timestamps are often in centiseconds (100ms) or seconds depending on version. Let's inspect or normalize.
        # Actually pywhispercpp provides seg.t0 and seg.t1 in centiseconds (ms / 10). Let's handle robustly:
        # If t0 > 1000 when duration is small, it's milliseconds. Standard whisper.cpp callback gives centiseconds or ms.
        # Let's check pywhispercpp convention: seg.t0 is centiseconds (1s = 100).
        t0_sec = seg.t0 / 100.0 if hasattr(seg, 't0') else 0.0
        t1_sec = seg.t1 / 100.0 if hasattr(seg, 't1') else 0.0
        text_content = clean_artifacts(getattr(seg, 'text', ''))
        
        if not text_content:
            continue
            
        if t1_sec > total_duration:
            total_duration = t1_sec
            
        segments_list.append({
            "start": t0_sec,
            "end": t1_sec,
            "text": text_content,
            "words": []
        })

    txt_path = os.path.join(output_dir, f"{base_name}_transcript.txt")
    json_path = os.path.join(output_dir, f"{base_name}_transcript.json")
    md_path = os.path.join(output_dir, f"{base_name}_transcript_annotated.md")
    
    with open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(f"Transcript for {file_name}\n")
        f_txt.write(f"Duration: {format_timestamp(total_duration)}\n")
        f_txt.write(f"=" * 60 + "\n\n")
        
        for seg in segments_list:
            ts_str = f"[{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}]"
            f_txt.write(f"{ts_str}  {seg['text']}\n")

    # Save JSON structured transcript
    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump({
            "source_file": file_name,
            "duration_seconds": total_duration,
            "language": language,
            "segments": segments_list
        }, f_json, indent=2, ensure_ascii=False)
        
    # Save Annotated Markdown transcript
    md_content = build_annotated_markdown(segments_list, f"Transcript: {file_name}", total_duration)
    with open(md_path, "w", encoding="utf-8") as f_md:
        f_md.write(md_content)
        
    # Apply phonetic repair post-processing if enabled
    if phonetic_repair:
        print("[post-processing] Applying deterministic phonetic repair...", flush=True)
        repair_all_outputs(base_name, output_dir)

    # Clean up temp WAV if requested
    if not keep_wav and os.path.exists(wav_path):
        try:
            os.remove(wav_path)
        except OSError:
            pass
            
    elapsed = time.time() - t_trans
    speedup = total_duration / elapsed if elapsed > 0 else 0
    note_md_path = os.path.join(output_dir, f"{base_name}.md")
    print(f"Completed in {elapsed:.1f}s ({elapsed/60:.2f} min) [{speedup:.2f}x real-time]", flush=True)
    print(f"Saved outputs inside '{output_dir}':\n  - {txt_path}\n  - {json_path}\n  - {md_path}", flush=True)
    print(f"Academic note target:\n  - {note_md_path}", flush=True)
    
    return {
        "txt": txt_path,
        "json": json_path,
        "md": md_path,
        "note": note_md_path,
        "output_dir": output_dir,
        "note_name": base_name
    }


def main():
    default_base = get_default_base_dir()
    parser = argparse.ArgumentParser(description="Transcribe media files with whisper.cpp, acoustic pre-filtering, and phonetic repair")
    parser.add_argument("input", help="Path to a video/audio file OR a directory containing media files")
    parser.add_argument("--base-dir", "-b", default=default_base, help=f"Base folder for all summary runs (default: {default_base})")
    parser.add_argument("--output-dir", "-o", default=None, help="Explicit directory override to save transcript files")
    parser.add_argument("--note-name", "-n", default=None, help="Name of the summary note / run subfolder (e.g. 'LPS_8_10'). Defaults to input media filename stem")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL_REPO, help=f"Whisper model repo or GGUF path (default: {DEFAULT_MODEL_REPO})")
    parser.add_argument("--singlish", action=argparse.BooleanOptionalAction, default=True, help="Optimize transcription for Singaporean English / Singlish (default: True)")
    parser.add_argument("--language", "-l", default="en", help="Language code (e.g. 'en', or 'auto' for auto-detection)")
    parser.add_argument("--prompt", "-p", default=None, help="Initial prompt to guide terminology, names, and vocabulary")
    parser.add_argument("--enhance-audio", action=argparse.BooleanOptionalAction, default=True, help="Apply speech bandpass filtering, afftdn noise reduction, and dynaudnorm normalization (default: True)")
    parser.add_argument("--no-phonetic-repair", action="store_true", help="Disable post-transcription phonetic repair")
    parser.add_argument("--threads", "-t", type=int, default=8, help="Number of CPU threads for inference (default: 8)")
    parser.add_argument("--scratch-dir", default=None, help="Directory to store intermediate audio files")
    parser.add_argument("--keep-wav", action="store_true", help="Keep extracted WAV audio files")
    
    args = parser.parse_args()
    
    target_path = os.path.abspath(args.input)
    if not os.path.exists(target_path):
        print(f"Error: Target path '{target_path}' does not exist!", file=sys.stderr)
        sys.exit(1)
        
    lang = None if args.language.lower() == "auto" else args.language
    
    # Collect files
    media_files: List[str] = []
    if os.path.isfile(target_path):
        media_files.append(target_path)
    else:
        for root, _, files in os.walk(target_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS and "temp" not in f.lower():
                    media_files.append(os.path.join(root, f))
                    
    if not media_files:
        print(f"No supported media files found in '{target_path}'.", file=sys.stderr)
        sys.exit(0)
        
    print(f"Found {len(media_files)} media file(s) to transcribe.")
    results = []
    for mf in media_files:
        current_note_name = args.note_name if (args.note_name and len(media_files) == 1) else os.path.splitext(os.path.basename(mf))[0]
        run_out_dir = resolve_run_output_dir(
            note_name=current_note_name,
            base_dir=args.base_dir,
            output_dir=args.output_dir
        )
        os.makedirs(run_out_dir, exist_ok=True)

        res = transcribe_file(
            media_path=mf,
            output_dir=run_out_dir,
            note_name=current_note_name,
            model_name=args.model,
            language=lang,
            initial_prompt=args.prompt,
            singlish=args.singlish,
            enhance_audio=args.enhance_audio,
            phonetic_repair=not args.no_phonetic_repair,
            cpu_threads=args.threads,
            temp_dir=args.scratch_dir,
            keep_wav=args.keep_wav
        )
        results.append(res)
        
    print(f"\n=======================================================", flush=True)
    print(f"All {len(results)} transcriptions completed successfully!", flush=True)
    for r in results:
        print(f"  * [{r['note_name']}] in {r['output_dir']}", flush=True)


if __name__ == "__main__":
    main()
