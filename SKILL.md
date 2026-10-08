---
name: summarizer
description: Processes multimedia files (audio, video, PDFs, slides, images) into comprehensive, deeply detailed, structured markdown summary notes with high coverage, and performs fast offline audio/video transcription.
---

# Summarizer Skill (100% Offline Pipeline & Academic Synthesis)

This skill provides a **100% offline, air-gapped, zero-cloud-token** pipeline for transcribing and summarizing multimedia files (audio, video, PDFs, slides, images).

## Communication & Formatting Style (Humanized & ADHD-Friendly)

- **Tone & Voice**: Conversational, peer-to-peer, and direct. Skip academic or corporate boilerplate.
- **No AI Slop**: Do not use LLM clichés or filler words such as *"delve"*, *"testament"*, *"tapestry"*, *"furthermore"*, *"moreover"*, or *"it's important to remember"*.
- **ADHD-Optimized Scannability**:
  - Lead with the **bottom-line answer / key takeaway first**.
  - Keep paragraphs short (2–3 sentences max) with varied sentence lengths.
  - Rely heavily on bullet points, callout boxes, and **bold keywords** to create visual anchors and prevent cognitive fatigue.
- **Pragmatic Explanations**: Ground complex topics in simple, intuitive analogies that anyone can grasp immediately.

## Storage Architecture & File Save Convention

All transcription outputs and synthesized academic notes are organized under a dynamically resolved cross-platform **Base folder**:
- **Default Resolution**: Dynamically resolves to `<User_Desktop>/Summarizer/` (e.g. `~/Desktop/Summarizer/` on macOS/Linux/Windows). If the Desktop folder does not exist, it automatically falls back to `~/Summarizer/`.
- **Automatic Directory Creation**: Both the base folder and the run subfolder (`<base_dir>/<note_name>/`) are automatically created (`os.makedirs(..., exist_ok=True)` / `mkdir(parents=True, exist_ok=True)`).

Inside this base folder, **each run creates a dedicated subfolder named after the summary note** (e.g. `LPS_8_10`):

```
<base_dir>/
└── <note_name>\                    # Subfolder named after the summary note (e.g. LPS_8_10\)
    ├── <note_name>.md              # Academic zero-information-loss synthesized note (e.g. LPS_8_10.md)
    ├── <note_name>_transcript.txt  # Timestamped text transcript with cleaned dialogue
    ├── <note_name>_transcript.json # Structured JSON with word/segment timestamps & confidence
    ├── <note_name>_transcript_annotated.md # Chronologically grouped markdown dialogue blocks
    └── slides\                     # (Optional) Extracted slide images if PDF deck was provided
        ├── <note_name>_page_001.png
        └── ...
```

---

## 1. 100% Offline Processing Architecture

The offline audio/video pipeline consists of three deterministic, local processing stages before note synthesis:

```
[Media Audio/Video]
       │
       ▼
1. Acoustic Preprocessing (ffmpeg)
   - Bandpass filter (highpass=100Hz, lowpass=7500Hz)
   - FFT noise suppression (afftdn=nf=-25)
   - Dynamic audio normalization (dynaudnorm=p=0.9:s=5)
       │
       ▼
2. whisper.cpp C++ Engine (pywhispercpp)
   - Model: `mjwong/whisper-large-v3-turbo-singlish` (GGUF / whisper.cpp native format)
   - High performance local C++ GGML execution
   - Hotword & Glossary injection (SE standards, AI tools, Singlish particles)
       │
       ▼
3. Deterministic Phonetic Repair (phonetic_repair.py)
   - Rule-based regex mapper targeting Singlish phonetic shifts & technical misrecognitions:
     * clock / crop 5.5 / crop 3.5 ➔ Claude 3.5
     * Germany ➔ Gemini
     * ECOC ➔ INCOSE
     * NRMI ➔ NRMD (Needs and Requirements Manual)
     * apologetic memory ➔ agentic memory
     * pin of sword ➔ pinch of salt
     * ostidian / O-B-S-I-D-I-A-N ➔ Obsidian
     * prom engineering ➔ prompt engineering
     * agent went road ➔ agent went rogue
     * KGPT ➔ ChatGPT
       │
       ▼
4. Academic Zero-Information-Loss Note Generation
   - Destination: `<base_dir>\<note_name>\<note_name>.md`
   - Chronological Topic Chaptering with timestamps (`[MM:SS]`)
   - Detailed Pedagogical Context & Professor mental models
   - Obsidian `[[Wikilinks]]` integration
   - ZERO raw transcript dumps
```

---

## 2. CLI Execution Instructions

### Environment Verification
Ensure dependencies are available:
```powershell
python -c "import pywhispercpp, imageio_ffmpeg, huggingface_hub; print('Ready!')"
```

### Full Offline Transcription Pipeline
Run `transcribe.py` with acoustic filtering and Singlish mode enabled by default:

```powershell
python scripts/transcribe.py `
    "path\to\LPS_8_10.m4a" `
    --note-name "LPS_8_10" `
    --model "mjwong/whisper-large-v3-turbo-singlish" `
    --singlish `
    --enhance-audio `
    --threads 8
```

Outputs generated inside `~/Desktop/Summarizer/LPS_8_10/` (Windows: `%USERPROFILE%\Desktop\Summarizer\LPS_8_10\`):
1. `LPS_8_10_transcript.txt`: Timestamped text transcript with cleaned dialogue.
2. `LPS_8_10_transcript.json`: Full structured JSON with timestamps and confidence scores.
3. `LPS_8_10_transcript_annotated.md`: Chronologically grouped markdown dialogue blocks.

> **Note on Parameters**:
> - If `--note-name` is omitted, it defaults to the stem of the input media file.
> - `--base-dir` defaults to `~/Desktop/Summarizer` (Windows: `%USERPROFILE%\Desktop\Summarizer`).
> - If `--output-dir` is explicitly passed, it can override the directory location.

### Standalone Phonetic Repair
To run phonetic repair on any transcript file or run folder independently:
```powershell
python scripts/phonetic_repair.py "~\Desktop\Summarizer\LPS_8_10"
```

---

## 3. Academic Zero-Information-Loss Note Generation Protocol

When synthesizing lecture notes, strictly adhere to the **Zero-Information-Loss** standard:

### File Save Location:
Always write the synthesized summary note directly inside the run subfolder:
**`<base_dir>\<note_name>\<note_name>.md`**  
*(e.g. `~/Desktop/Summarizer/LPS_8_10/LPS_8_10.md` or `%USERPROFILE%\Desktop\Summarizer\LPS_8_10\LPS_8_10.md`)*

### Core Rules:
1. **ZERO Raw Transcript Dumps**: Never paste raw transcript text or huge uncurated quotes into the summary note. Every piece of information must be parsed, structured, and synthesized into high-density conceptual explanations.
2. **Chronological Topic Chaptering**: Divide the lecture into distinct, chronological chapters labeled with clear timestamp ranges (e.g. `### [01:30 - 05:40] Theme Title`).
3. **Deep Pedagogical Context & Caveats**:
   - Explicitly highlight the professor's core thesis, underlying philosophy, and mental models.
   - Capture exam traps, quiz warnings, viva defense expectations, and grading rubrics.
   - Explain analogies, industry war stories, and practical examples (e.g. healthcare robotics, defense projects, interview scenarios).
4. **Obsidian [[Wikilinks]]**: Wrap all key technical terms, standards, models, frameworks, and persons in Obsidian wikilinks (e.g. `[[INCOSE]]`, `[[Claude 3.5]]`, `[[Gemini]]`, `[[Obsidian]]`, `[[Agentic Memory]]`, `[[Needs and Requirements Manual (NRMD)]]`, `[[Concept of Operations (ConOps)]]`).
5. **Architectural & Comparative Analysis**: Contrast static versus dynamic structures, prompt engineering versus second brain systems engineering, and model benchmarks.
6. **NO Pipeline or Tooling Metadata**: Never include sections or metadata lines detailing the transcription stack (e.g. Whisper model, acoustic preprocessors, ffmpeg, phonetic repair) in study notes. The note should focus purely on lecture content and start directly with the overview/content.

---

## 4. Standard Note Structure

Always format the synthesized markdown note using this schema and save to `<base_dir>\<note_name>\<note_name>.md`:

```markdown
# Comprehensive Lecture/Document Summary: [Topic Title]

**Source Transcript / File:** `[Filename]`  
**Original Source / Duration:** `[Duration]`  
**Date:** [YYYY-MM-DD]

---

## Executive Overview
[2-3 dense paragraphs summarizing the foundational premise, strategic thesis, and core takeaways of the lecture.]

---

## Core Architectural & Conceptual Frameworks
[System-level mental models, 2x2 matrices, 70/30 domain-system balance, Anthropic 4D framework, static vs dynamic knowledge graphs.]

---

## Chronological In-Depth Lecture Breakdown

### 1. [00:00 - MM:SS] [Section Title]
- **Core Concept & Definitions**: ...
- **Detailed Mechanics & Arguments**: ...
- **Professor's Pedagogical Emphasis & Exam/Viva Traps**: ...
- **Practical Examples & Analogies**: ...

### 2. [MM:SS - MM:SS] [Section Title]
...

---

## Systems Engineering & AI Integration Principles
[Synthesis of INCOSE standards, NRMD, ConOps vs OpsCon, LLM context window limits ("lost in the middle"), and Second Brain querying.]

---

## Action Items, Study Guide & Viva Preparation
- [ ] **Viva Defense Trap**: ...
- [ ] **Key Concepts to Internalize**: ...
- [ ] **Practical Architecture Implementation**: ...
```

---

## 5. Hybrid PDF Pipeline & Document Ingestion

> **AUTOMATIC SLIDE EXTRACTION RULE (Default Behavior)**: Whenever a user uploads or provides a PDF identified as a slide deck, presentation, or visual material (via triage or layout characteristics), the summarizer skill **ALWAYS automatically extracts and saves slide images into `~/Desktop/Summarizer/<note_name>/slides/` by default** without requiring the user to prompt for it.

The summarizer skill provides a robust hybrid PDF processing workflow supporting triage, fast markdown extraction, high-fidelity LaTeX/math extraction, and automatic slide image extraction:

### 1. PDF Triage (`pdf_triage.py`)
Inspects a PDF to determine its document type and recommend the optimal processing engine/workflow:
```powershell
python scripts/pdf_triage.py "path\to\document.pdf"
```

### 2. PDF to Markdown Extraction (`pdf_to_markdown.py`)
Converts a PDF to clean markdown, saved as `<note_name>_source.md` in `<base_dir>\<note_name>\`:
- **`pymupdf4llm` (Default)**: Fast, lightweight markdown extraction for text-dense papers and documents.
  ```powershell
  python scripts/pdf_to_markdown.py "path\to\document.pdf" --engine pymupdf4llm --note-name "DocName"
  ```
- **`docling`**: High-fidelity LaTeX, math formulas, and complex table parsing engine.
  ```powershell
  python scripts/pdf_to_markdown.py "path\to\document.pdf" --engine docling --note-name "DocName"
  ```

### 3. Slide Decks & Flowcharts (`pdf_to_images.py`) - AUTOMATIC BY DEFAULT
For slide decks and flowchart-heavy presentations, slide extraction is triggered automatically:
```powershell
python scripts/pdf_to_images.py "path\to\slides.pdf" --note-name "SlidesName"
```
Images are extracted directly to `<base_dir>\<note_name>\slides\`. The extracted slide images are then passed to vision-capable models for visual alignment and synthesis into `<base_dir>\<note_name>\<note_name>.md`.

---