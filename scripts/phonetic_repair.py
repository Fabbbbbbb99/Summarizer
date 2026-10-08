#!/usr/bin/env python3
"""
Phonetic & Domain Lexicon Repair for Academic / Technical Lectures
Deterministically corrects phonetic misrecognitions, Singlish transcript shifts,
and whisper acoustic artifacts (e.g. Singaporean accented English, LLM technical terms,
Systems Engineering standards, and anti-hallucination cleanup).
"""

import os
import sys
import re
import json
import argparse
from typing import List, Dict, Any, Tuple, Pattern


# Ordered list of (regex_pattern, replacement, description)
PHONETIC_REPAIR_RULES: List[Tuple[Pattern, str, str]] = [
    # 1. Hallucination stripping (Whisper artifact loops on dead air/noise)
    (re.compile(r'\b(?:INTRANANTERA\s*)+', re.IGNORECASE), '', 'Whisper phantom Latin token hallucination'),
    (re.compile(r'\bA MUShhhh\b', re.IGNORECASE), '', 'Microphone hiss artifact'),
    (re.compile(r'\blor mihiFlabi\b', re.IGNORECASE), '', 'Acoustic mic rattle artifact'),
    
    # 2. Systems Engineering standards & documents (INCOSE, SEH, NRMD)
    (re.compile(r'\bECOC\b', re.IGNORECASE), 'INCOSE', 'INCOSE standards body'),
    (re.compile(r'\bNRMI\b', re.IGNORECASE), 'NRMD', 'Needs and Requirements Manual Document'),
    (re.compile(r'\bSEH\b', re.IGNORECASE), 'SEH', 'Systems Engineering Handbook'),
    (re.compile(r'\bcon ops\b', re.IGNORECASE), 'ConOps', 'Concept of Operations'),
    (re.compile(r'\bops con\b', re.IGNORECASE), 'OpsCon', 'Operational Concept'),
    (re.compile(r'\bthis fellow called Ryan\b', re.IGNORECASE), 'this fellow called Prof. Mike Ryan', 'Prof. Mike Ryan (INCOSE requirements)'),
    (re.compile(r'\bby this fellow called Mike Ryan\b', re.IGNORECASE), 'by this fellow called Prof. Mike Ryan', 'Mike Ryan attribution'),

    # 3. Frontier AI Models & Tools (Claude, Gemini, ChatGPT, Obsidian, Agentic Memory)
    (re.compile(r'\b(?:crop|clock)\s*5\.5\b', re.IGNORECASE), 'Claude 3.5', 'Claude 3.5 model reference'),
    (re.compile(r'\b(?:crop|clock)\s*3\.5\b', re.IGNORECASE), 'Claude 3.5', 'Claude 3.5 model reference'),
    (re.compile(r'\b(?:crop|clock)\s*3\.5\s*sonnet\b', re.IGNORECASE), 'Claude 3.5 Sonnet', 'Claude 3.5 Sonnet model reference'),
    (re.compile(r'\bclock or security\b', re.IGNORECASE), 'Claude or Perplexity', 'Claude/Perplexity comparison'),
    (re.compile(r'\bclock tokens\b', re.IGNORECASE), 'Claude tokens', 'Claude token consumption'),
    (re.compile(r'\btokens from clock\b', re.IGNORECASE), 'tokens from Claude', 'Claude tokens'),
    (re.compile(r'\bclock powerful\b', re.IGNORECASE), 'Claude powerful', 'Claude model capabilities'),
    (re.compile(r'\buse clock\b', re.IGNORECASE), 'use Claude', 'Use Claude model'),
    (re.compile(r'\bwith clock\b', re.IGNORECASE), 'with Claude', 'With Claude model'),
    (re.compile(r'\bin power with clock\b', re.IGNORECASE), 'on par with Claude', 'Benchmark parity with Claude'),
    (re.compile(r'\bon par with clock\b', re.IGNORECASE), 'on par with Claude', 'Benchmark parity with Claude'),
    (re.compile(r'\b(?:I think\s+)?clock came up with\b', re.IGNORECASE), 'Claude (Anthropic) came up with', 'Anthropic 4D framework attribution'),
    (re.compile(r'\bclock\s+give me reasons\b', re.IGNORECASE), 'Claude give me reasons', 'Claude query in viva demo'),
    (re.compile(r'\bwindow clock\b', re.IGNORECASE), 'window Claude', 'Context window Claude'),
    (re.compile(r'\bKGPT\b', re.IGNORECASE), 'ChatGPT', 'ChatGPT reference'),
    (re.compile(r'\bwhat by Google is what Germany also come in\b', re.IGNORECASE), 'what by Google is Gemini also coming in', 'Google Gemini release'),
    (re.compile(r'\bGermany also come in\b', re.IGNORECASE), 'Gemini also coming in', 'Google Gemini reference'),
    (re.compile(r'\bby Google is what Germany\b', re.IGNORECASE), 'by Google is Gemini', 'Google Gemini'),
    (re.compile(r'\bostidian\b', re.IGNORECASE), 'Obsidian', 'Obsidian note-taking app'),
    (re.compile(r'\bO-B-S-I-D-I-A-N\b', re.IGNORECASE), 'Obsidian (O-B-S-I-D-I-A-N)', 'Spelled Obsidian'),
    (re.compile(r'\bapologetic memory\b', re.IGNORECASE), 'agentic memory', 'Agentic memory systems'),
    (re.compile(r'\bagentik\b', re.IGNORECASE), 'agentic', 'Agentic typo'),
    
    # 4. Rogue AI / English idioms / Singlish idioms
    (re.compile(r'\bagent went road\b', re.IGNORECASE), 'agent went rogue', 'Agent went rogue idiom'),
    (re.compile(r'\bagent is going road\b', re.IGNORECASE), 'agent is going rogue', 'Agent going rogue idiom'),
    (re.compile(r'\bpin of sword\b', re.IGNORECASE), 'pinch of salt', 'Pinch of salt idiom'),
    (re.compile(r'\btau kwan\b', re.IGNORECASE), 'talk cock / tricks', 'Hokkien/Singlish trickery idiom'),
    (re.compile(r'\bCatch no ball\b', re.IGNORECASE), 'catch no ball', 'Singlish idiom: catch no ball (cannot understand)'),
    (re.compile(r'\bChim\b', re.IGNORECASE), 'chim', 'Singlish: chim (profound/difficult)'),
    (re.compile(r'\bchui\b', re.IGNORECASE), 'chui', 'Singlish: chui (weak/bad)'),
    
    # 5. GenAI terminology & Acronyms
    (re.compile(r'\bprom engineering\b', re.IGNORECASE), 'prompt engineering', 'Prompt engineering'),
    (re.compile(r'\bprom engineer\b', re.IGNORECASE), 'prompt engineer', 'Prompt engineer'),
    (re.compile(r'\bbeyond prom\b', re.IGNORECASE), 'beyond prompt', 'Beyond prompt engineering'),
    (re.compile(r'\bmove beyond prom\b', re.IGNORECASE), 'move beyond prompt', 'Beyond prompt engineering'),
    (re.compile(r'\bJNAI\b', re.IGNORECASE), 'GenAI', 'GenAI abbreviation'),
    (re.compile(r'\bGNI\b', re.IGNORECASE), 'GenAI', 'GenAI abbreviation'),
    (re.compile(r'\bGNAI\b', re.IGNORECASE), 'GenAI', 'GenAI abbreviation'),
    (re.compile(r'\bgen EI\b', re.IGNORECASE), 'GenAI', 'GenAI phonetic typo'),
    (re.compile(r'\bJenny I\b', re.IGNORECASE), 'GenAI', 'GenAI phonetic typo'),
    (re.compile(r'\bfrom DNA possible\b', re.IGNORECASE), 'from GenAI possible', 'GenAI phonetic typo'),
    (re.compile(r'\bIOM\b(?=.*next token)', re.IGNORECASE), 'LLM', 'LLM next token typo'),
    (re.compile(r'\bwhat is LAM\b', re.IGNORECASE), 'what is LLM', 'LLM language model'),
    (re.compile(r'\blm wiki\b', re.IGNORECASE), 'LLM Wiki', 'LLM Wiki / Second Brain'),
    (re.compile(r'\bLM wiki\b', re.IGNORECASE), 'LLM Wiki', 'LLM Wiki / Second Brain'),
    (re.compile(r'\bJeff GEE\b', re.IGNORECASE), 'LLM Router/Gateway (e.g. LiteLLM/OpenRouter)', 'Model router/gateway tool'),

    # 6. Course & University references
    (re.compile(r'\bSES\b', re.IGNORECASE), 'SES (Systems Engineering Studio)', 'Systems Engineering Studio'),
    (re.compile(r'\bSEP2\b', re.IGNORECASE), 'SEP 2', 'Systems Engineering Project 2'),
    (re.compile(r'\bnad 4d non not 4d as in Qatar\b', re.IGNORECASE), 'Anthropic 4D framework (not 4D lottery)', 'Anthropic 4D framework disambiguation'),
    (re.compile(r'\b1% Q10\b', re.IGNORECASE), 'top 1% / Q1', 'Grade quantile reference')
]


def repair_text(text: str) -> str:
    """Applies all phonetic and technical repairs to a text string."""
    repaired = text
    for pattern, replacement, _ in PHONETIC_REPAIR_RULES:
        repaired = pattern.sub(replacement, repaired)
    
    # Clean redundant spaces caused by deletions
    repaired = re.sub(r'[ \t]{2,}', ' ', repaired)
    repaired = re.sub(r'\n{3,}', '\n\n', repaired)
    return repaired.strip()


def repair_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Applies phonetic repairs across Whisper segment structures."""
    repaired_segments = []
    for seg in segments:
        text = seg.get("text", "")
        repaired_text = repair_text(text)
        
        # Skip segments that become completely empty (e.g. stripped hallucination loops)
        if not repaired_text.strip():
            continue
            
        new_seg = dict(seg)
        new_seg["text"] = repaired_text
        repaired_segments.append(new_seg)
    return repaired_segments


def repair_transcript_file(file_path: str, output_path: str = None) -> str:
    """
    Repairs a transcript file (.txt, .json, or .md) in-place or to output_path.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Transcript file not found: {file_path}")

    target_out = output_path or file_path
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "segments" in data:
            data["segments"] = repair_segments(data["segments"])
        with open(target_out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    elif ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        repaired_content = repair_text(content)
        with open(target_out, "w", encoding="utf-8") as f:
            f.write(repaired_content)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    print(f"[phonetic_repair] Repaired {os.path.basename(file_path)} -> {os.path.basename(target_out)}")
    return target_out


def repair_all_outputs(base_name: str, directory: str) -> Dict[str, str]:
    """
    Finds and repairs all three output files (_transcript.txt, _transcript.json, _transcript_annotated.md).
    """
    results = {}
    for suffix, ext in [("_transcript.txt", ".txt"), ("_transcript.json", ".json"), ("_transcript_annotated.md", ".md")]:
        filename = f"{base_name}{suffix}"
        full_path = os.path.join(directory, filename)
        if os.path.exists(full_path):
            repair_transcript_file(full_path)
            results[ext] = full_path
    return results


def main():
    parser = argparse.ArgumentParser(description="Repair phonetic misrecognitions and Singlish lecture terms in transcripts")
    parser.add_argument("input", help="Path to transcript file (.txt, .json, .md) or directory")
    parser.add_argument("--output", "-o", default=None, help="Output file path (defaults to in-place edit)")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if os.path.isdir(input_path):
        count = 0
        for f in os.listdir(input_path):
            if any(f.endswith(ext) for ext in [".txt", ".json", ".md"]):
                repair_transcript_file(os.path.join(input_path, f))
                count += 1
        print(f"Repaired {count} files in {input_path}")
    else:
        repair_transcript_file(input_path, args.output)


if __name__ == "__main__":
    main()
