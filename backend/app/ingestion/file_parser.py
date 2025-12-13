from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from bs4 import BeautifulSoup
from docx import Document
from ebooklib import ITEM_DOCUMENT, epub


@dataclass(frozen=True)
class ParsedBlock:
    text: str
    rich_text: str
    metadata: dict[str, Any]


def _decode_best_effort(raw: bytes) -> str:
    for enc in ("utf-8", "utf-16", "utf-16le", "utf-16be", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


_ALLOWED_INLINE_TAGS = {"b", "strong", "i", "em", "h1", "h2", "h3", "p", "br", "li"}


def _html_to_text_and_rich(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(True):
        if tag.name not in _ALLOWED_INLINE_TAGS:
            tag.unwrap()

    rich = str(soup.body or soup)
    rich = re.sub(r"^<(body|html)[^>]*>|</(body|html)>$", "", rich).strip()

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, rich


def _html_to_blocks(*, html: str, filename: str) -> list[ParsedBlock]:
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup

    # Strip all but basic formatting tags, while keeping textual content.
    for tag in root.find_all(True):
        if tag.name not in _ALLOWED_INLINE_TAGS:
            tag.unwrap()

    blocks: list[ParsedBlock] = []
    current_heading: str | None = None

    for el in root.find_all(["h1", "h2", "h3", "p", "li"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue

        if el.name in {"h1", "h2", "h3"}:
            current_heading = text
            blocks.append(
                ParsedBlock(
                    text=text,
                    rich_text=f"<h3>{text}</h3>",
                    metadata={
                        "source": filename,
                        "kind": "heading",
                        "chapter_title": text,
                        "heading_level": 1 if el.name == "h1" else 2 if el.name == "h2" else 3,
                    },
                )
            )
            continue

        blocks.append(
            ParsedBlock(
                text=text,
                rich_text=str(el),
                metadata={
                    "source": filename,
                    "kind": "paragraph",
                    "chapter_title": current_heading,
                },
            )
        )

    if blocks:
        return blocks

    # Fallback: plain text splitting.
    text, _rich = _html_to_text_and_rich(html)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [
        ParsedBlock(
            text=p,
            rich_text=p,
            metadata={"source": filename, "kind": "paragraph", "chapter_title": None},
        )
        for p in paragraphs
    ]


class FileParser:
    """
    Best-effort file parsing for ERR.

    Output is a list of ParsedBlock items that preserve rough section/chapter metadata
    (when detectable) while keeping raw text blocks paragraph-like.
    """

    def parse(self, *, filename: str, content: bytes) -> list[ParsedBlock]:
        name = filename.lower().strip()
        if name.endswith(".txt"):
            return self._parse_txt(filename=filename, content=content)
        if name.endswith(".md"):
            return self._parse_md(filename=filename, content=content)
        if name.endswith(".docx"):
            return self._parse_docx(filename=filename, content=content)
        if name.endswith(".epub"):
            return self._parse_epub(filename=filename, content=content)
        if name.endswith(".mobi"):
            # ebooklib does not reliably support MOBI; try best-effort anyway.
            return self._parse_mobi_best_effort(filename=filename, content=content)
        raise ValueError(f"Unsupported file type for: {filename}")

    def _parse_txt(self, *, filename: str, content: bytes) -> list[ParsedBlock]:
        text = _decode_best_effort(content)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return [
            ParsedBlock(
                text=p,
                rich_text=p,
                metadata={"source": filename, "kind": "paragraph"},
            )
            for p in paragraphs
        ]

    def _parse_md(self, *, filename: str, content: bytes) -> list[ParsedBlock]:
        text = _decode_best_effort(content)
        lines = [ln.rstrip() for ln in text.splitlines()]

        blocks: list[ParsedBlock] = []
        current_heading: str | None = None
        buffer: list[str] = []

        def flush() -> None:
            nonlocal buffer, blocks
            raw = "\n".join(buffer).strip()
            if not raw:
                buffer = []
                return
            blocks.append(
                ParsedBlock(
                    text=raw,
                    rich_text=raw,
                    metadata={
                        "source": filename,
                        "kind": "markdown_block",
                        "chapter_title": current_heading,
                    },
                )
            )
            buffer = []

        for ln in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", ln)
            if heading_match:
                flush()
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                current_heading = title
                blocks.append(
                    ParsedBlock(
                        text=title,
                        rich_text=f"<h3>{title}</h3>" if level <= 3 else title,
                        metadata={
                            "source": filename,
                            "kind": "heading",
                            "heading_level": level,
                            "chapter_title": title,
                        },
                    )
                )
                continue

            if ln.strip() == "":
                flush()
                continue

            buffer.append(ln)

        flush()
        return blocks

    def _parse_docx(self, *, filename: str, content: bytes) -> list[ParsedBlock]:
        doc = Document(BytesIO(content))

        blocks: list[ParsedBlock] = []
        current_heading: str | None = None

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style_name = (para.style.name or "").lower() if para.style else ""
            is_heading = style_name.startswith("heading")

            rich_parts: list[str] = []
            for run in para.runs:
                run_text = run.text
                if not run_text:
                    continue
                if run.bold:
                    run_text = f"<b>{run_text}</b>"
                if run.italic:
                    run_text = f"<i>{run_text}</i>"
                rich_parts.append(run_text)

            rich = "".join(rich_parts).strip() or text

            if is_heading:
                current_heading = text
                blocks.append(
                    ParsedBlock(
                        text=text,
                        rich_text=f"<h3>{rich}</h3>",
                        metadata={
                            "source": filename,
                            "kind": "heading",
                            "chapter_title": text,
                            "style": para.style.name if para.style else None,
                        },
                    )
                )
                continue

            blocks.append(
                ParsedBlock(
                    text=text,
                    rich_text=rich,
                    metadata={
                        "source": filename,
                        "kind": "paragraph",
                        "chapter_title": current_heading,
                        "style": para.style.name if para.style else None,
                    },
                )
            )

        return blocks

    def _parse_epub(self, *, filename: str, content: bytes) -> list[ParsedBlock]:
        # ebooklib expects a filesystem path; use a temp file to stay "ephemeral"
        # while still supporting the library's API.
        with tempfile.NamedTemporaryFile(suffix=".epub") as tmp:
            tmp.write(content)
            tmp.flush()
            book = epub.read_epub(tmp.name)

        all_blocks: list[ParsedBlock] = []

        for item in book.get_items():
            if item.get_type() != ITEM_DOCUMENT:
                continue
            html = item.get_content().decode("utf-8", errors="replace")
            blocks = _html_to_blocks(html=html, filename=filename)
            if blocks:
                all_blocks.extend(blocks)

        return all_blocks

    def _parse_mobi_best_effort(self, *, filename: str, content: bytes) -> list[ParsedBlock]:
        try:
            # Some MOBI files may still be readable via epub.read_epub, depending on container.
            return self._parse_epub(filename=filename, content=content)
        except Exception as e:  # noqa: BLE001
            raise ValueError(
                f"Best-effort MOBI parsing failed for {filename}. Consider converting to EPUB. Error: {e}"
            ) from e
