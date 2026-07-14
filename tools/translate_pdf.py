#!/usr/bin/env python3
"""Split an OCR'd PDF into 30-page sections and optionally translate EN->KO."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

import requests
from pypdf import PdfReader

DEFAULT_CHUNK_SIZE = 30


def chunk_ranges(total_pages: int, chunk_size: int) -> List[range]:
    ranges = []
    for start in range(1, total_pages + 1, chunk_size):
        end = min(start + chunk_size - 1, total_pages)
        ranges.append(range(start, end + 1))
    return ranges


def extract_text(reader: PdfReader, pages: Iterable[int]) -> str:
    chunks = []
    for page_number in pages:
        page = reader.pages[page_number - 1]
        text = page.extract_text() or ""
        chunks.append(text)
    return "\n\n".join(chunks).strip()


def translate_text(
    text: str,
    *,
    url: str,
    source: str = "en",
    target: str = "ko",
    timeout_s: int = 60,
) -> str:
    response = requests.post(
        url,
        json={
            "q": text,
            "source": source,
            "target": target,
            "format": "text",
        },
        timeout=timeout_s,
    )
    response.raise_for_status()
    payload = response.json()
    if "translatedText" not in payload:
        raise ValueError(f"Unexpected response: {payload}")
    return payload["translatedText"]


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split OCR PDF into sections and translate EN->KO.",
    )
    parser.add_argument(
        "pdf",
        type=Path,
        help="Path to the OCR PDF file (e.g. ./input/your.pdf)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("input"),
        help="Optional input directory to store PDFs",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Number of pages per section",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Translate each chunk (requires --libretranslate-url)",
    )
    parser.add_argument(
        "--libretranslate-url",
        type=str,
        default="",
        help="LibreTranslate API endpoint (e.g. http://localhost:5000/translate)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.translate and not args.libretranslate_url:
        raise SystemExit("--translate requires --libretranslate-url")

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    args.input_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(args.pdf))
    total_pages = len(reader.pages)

    ranges = chunk_ranges(total_pages, args.chunk_size)
    manifest = {
        "source_pdf": str(args.pdf),
        "total_pages": total_pages,
        "chunk_size": args.chunk_size,
        "sections": [],
    }

    for index, page_range in enumerate(ranges, start=1):
        start_page = page_range.start
        end_page = page_range.stop - 1
        text = extract_text(reader, page_range)
        en_name = f"part_{index:02d}_p{start_page:03d}-{end_page:03d}_en.txt"
        en_path = output_dir / en_name
        write_text(en_path, text)

        section_entry = {
            "index": index,
            "start_page": start_page,
            "end_page": end_page,
            "english_file": en_name,
            "korean_file": None,
        }

        if args.translate:
            translated = translate_text(text, url=args.libretranslate_url)
            ko_name = f"part_{index:02d}_p{start_page:03d}-{end_page:03d}_ko.txt"
            ko_path = output_dir / ko_name
            write_text(ko_path, translated)
            section_entry["korean_file"] = ko_name

        manifest["sections"].append(section_entry)

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved {len(ranges)} sections to {output_dir}")


if __name__ == "__main__":
    main()
