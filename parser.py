"""
Smart Exam-Prep Scheduler — Phase 2: Syllabus PDF Parser

Goal: extract topic headings from a syllabus/manual PDF.
Approach: headings in this document are BOLD, body text is not —
so we detect headings by font weight, not font size.
"""

import pdfplumber
import re


def extract_lines(pdf_path: str) -> list[dict]:
    """
    Reads the PDF and returns a list of lines, each as:
    {"text": "...", "bold": True/False}
    """
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chars_by_line = {}
            for char in page.chars:
                key = round(char["top"], 1)   # groups characters sitting on the same line
                chars_by_line.setdefault(key, []).append(char)

            for top in sorted(chars_by_line):
                chars = chars_by_line[top]
                text = "".join(c["text"] for c in chars).strip()
                if not text:
                    continue
                is_bold = "700" in chars[0]["fontname"] or "Bold" in chars[0]["fontname"]
                font_size = round(chars[0]["size"], 1)
                lines.append({"text": text, "bold": is_bold, "size": font_size})
    return lines

def extract_topics(pdf_path: str) -> list[str]:
    """
    Returns only top-level topic headings.
    A line qualifies if it's bold AND starts with a recognized
    top-level marker like 'Practical N', 'Unit N', 'Chapter N', or 'Module N'.
    """
    lines = extract_lines(pdf_path)
    topics = []

    top_level_pattern = re.compile(
        r"^(Practical|Unit|Chapter|Module|Topic)[\s\x00]+\d+[\s\x00.:\-]*(.+)$",
        re.IGNORECASE
    )

    for line in lines:
        if not line["bold"]:
            continue
        match = top_level_pattern.match(line["text"])
        if match:
            clean_title = match.group(2).replace("\x00", " ").strip()
            clean_title = " ".join(clean_title.split())
            if clean_title:
                topics.append(clean_title)

    return topics

def extract_topics_by_aim(pdf_path: str) -> list[str]:
    """
    Extracts topic titles from lines starting with 'Aim:'.
    Since the aim description can span multiple lines, this keeps
    reading forward until it hits a stop marker like 'Code:-' or 'Output:-'.
    """
    lines = extract_lines(pdf_path)
    topics = []

    aim_pattern = re.compile(r"^Aim\s*[:\-]*\s*(.+)$", re.IGNORECASE)
    stop_pattern = re.compile(r"^(Code|Output|\d+\s*\([a-zA-Z]\)|\d+[a-zA-Z]?\s*[:\-])", re.IGNORECASE)

    i = 0
    while i < len(lines):
        match = aim_pattern.match(lines[i]["text"])
        if match:
            collected = [match.group(1)]
            j = i + 1
            while j < len(lines) and not stop_pattern.match(lines[j]["text"]):
                collected.append(lines[j]["text"])
                j += 1

            full_title = " ".join(collected)
            full_title = full_title.replace("\x00", " ").strip()
            full_title = " ".join(full_title.split())
            if full_title:
                topics.append(full_title)

            i = j   # jump ahead — skip the lines we just consumed
        else:
            i += 1

    return topics

def get_topics_manually() -> list[str]:
    """
    Fallback when extraction fails: ask the student to type topic names.
    Empty input ends the loop.
    """
    print("No topics could be extracted. Please enter them manually.")
    topics = []
    while True:
        name = input("Topic name (blank to finish): ").strip()
        if not name:
            break
        topics.append(name)
    return topics

def clean_topic_name(name: str) -> str:
    """
    Strips stray leading punctuation (dashes, bullets, colons)
    that sometimes survives from PDF text extraction.
    """
    return re.sub(r"^[\s\-\u2013\u2014:.\u2022]+", "", name).strip()


def extract_topics_auto(pdf_path: str) -> list[str]:
    """
    Tries multiple extraction strategies and returns whichever
    one successfully found topics. Tries bold-heading detection first,
    then falls back to 'Aim:' line detection.
    """
    topics = extract_topics(pdf_path)
    if not topics:
        topics = extract_topics_by_aim(pdf_path)

    return [clean_topic_name(t) for t in topics]


if __name__ == "__main__":
    topics = extract_topics_auto("sample_syllabus3.pdf")
    print(f"\nFound {len(topics)} topics:\n")
    for t in topics:
        print(" -", t)