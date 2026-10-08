#!/usr/bin/env python3
"""
Audio Preprocessor for Speech & Lecture Transcriptions
Applies acoustic filtering (bandpass, noise reduction, dynamic normalization)
via ffmpeg to optimize speech clarity for Whisper models, removing HVAC drone,
high-frequency microphone hiss, and room reverberation.
"""

import os
import sys
import argparse
import subprocess
from typing import Optional


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


def build_audio_filter(
    highpass: int = 100,
    lowpass: int = 7500,
    afftdn: bool = True,
    afftdn_nf: int = -25,
    dynaudnorm: bool = True
) -> str:
    """
    Constructs an ffmpeg audio filter graph for speech enhancement.
    - Bandpass: highpass removes HVAC/AC drone (<100Hz); lowpass removes hiss (>7500Hz).
    - afftdn: FFT-based noise reduction for classroom hum/background noise.
    - dynaudnorm: Dynamic audio normalization to equalize quiet speech and loud peaks.
    """
    filters = []
    
    # 1. Bandpass filter for human vocal range
    if highpass > 0 and lowpass > 0:
        filters.append(f"highpass=f={highpass},lowpass=f={lowpass}")
    elif highpass > 0:
        filters.append(f"highpass=f={highpass}")
    elif lowpass > 0:
        filters.append(f"lowpass=f={lowpass}")

    # 2. FFT-based adaptive noise suppression
    if afftdn:
        filters.append(f"afftdn=nf={afftdn_nf}")

    # 3. Dynamic audio normalizer (equalizes speaker level and room dynamics)
    if dynaudnorm:
        filters.append("dynaudnorm=p=0.9:s=5")

    return ",".join(filters)


def preprocess_audio(
    input_path: str,
    output_path: Optional[str] = None,
    highpass: int = 100,
    lowpass: int = 7500,
    afftdn: bool = True,
    afftdn_nf: int = -25,
    dynaudnorm: bool = True,
    ffmpeg_bin: Optional[str] = None,
    sample_rate: int = 16000,
    channels: int = 1
) -> str:
    """
    Extracts and filters audio from media file to 16kHz mono 16-bit PCM WAV.
    Returns the path to the processed WAV file.
    """
    if ffmpeg_bin is None:
        ffmpeg_bin = get_ffmpeg_executable()

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_enhanced.wav"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    filter_str = build_audio_filter(
        highpass=highpass,
        lowpass=lowpass,
        afftdn=afftdn,
        afftdn_nf=afftdn_nf,
        dynaudnorm=dynaudnorm
    )

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", input_path,
        "-vn"
    ]

    if filter_str:
        cmd.extend(["-af", filter_str])

    cmd.extend([
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        output_path
    ])

    print(f"[audio_preprocessor] Processing: {os.path.basename(input_path)} -> {os.path.basename(output_path)}", flush=True)
    if filter_str:
        print(f"[audio_preprocessor] Audio filter: {filter_str}", flush=True)

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"ffmpeg audio preprocessing failed for '{input_path}':\n{res.stderr[-600:]}"
        )

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Acoustic preprocessing & enhancement for speech transcription")
    parser.add_argument("input", help="Path to input audio/video file")
    parser.add_argument("--output", "-o", default=None, help="Output WAV path (default: <input>_enhanced.wav)")
    parser.add_argument("--highpass", type=int, default=100, help="Highpass cutoff frequency in Hz (default: 100)")
    parser.add_argument("--lowpass", type=int, default=7500, help="Lowpass cutoff frequency in Hz (default: 7500)")
    parser.add_argument("--no-afftdn", action="store_true", help="Disable FFT noise reduction filter")
    parser.add_argument("--afftdn-nf", type=int, default=-25, help="afftdn noise floor in dB (default: -25)")
    parser.add_argument("--no-dynaudnorm", action="store_true", help="Disable dynamic audio normalization")

    args = parser.parse_args()

    out_file = preprocess_audio(
        input_path=args.input,
        output_path=args.output,
        highpass=args.highpass,
        lowpass=args.lowpass,
        afftdn=not args.no_afftdn,
        afftdn_nf=args.afftdn_nf,
        dynaudnorm=not args.no_dynaudnorm
    )
    print(f"Enhanced audio successfully written to: {out_file}")


if __name__ == "__main__":
    main()
