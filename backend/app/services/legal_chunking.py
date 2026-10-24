import re
from typing import Iterable

from app.db.models import LegalProvision, LegalSource
from app.schemas.legal_retrieval import LegalTextChunk

DEFAULT_CHUNK_CHARACTERS = 4000
DEFAULT_OVERLAP_CHARACTERS = 500
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?።])\s+")
_CONTINUATION_START = re.compile(
    r"^(?:provided that|except that|unless|notwithstanding|subject to|"
    r"for purposes of|in this article|as used in this article)\b",
    re.I,
)


def _split_long_paragraph(paragraph: str, max_characters: int) -> list[str]:
    sentences = [sentence.strip() for sentence in _SENTENCE_BOUNDARY.split(paragraph) if sentence.strip()]
    grouped_sentences: list[str] = []
    for sentence in sentences:
        if grouped_sentences and _CONTINUATION_START.match(sentence):
            grouped_sentences[-1] = f"{grouped_sentences[-1]} {sentence}"
        else:
            grouped_sentences.append(sentence)
    sentences = grouped_sentences
    if len(sentences) <= 1 and len(paragraph) > max_characters:
        words = paragraph.split()
        pieces: list[str] = []
        current = ""
        for word in words:
            if len(word) > max_characters:
                if current:
                    pieces.append(current)
                    current = ""
                pieces.extend(
                    word[index : index + max_characters]
                    for index in range(0, len(word), max_characters)
                )
            elif len(current) + len(word) + bool(current) <= max_characters:
                current = f"{current} {word}".strip()
            else:
                pieces.append(current)
                current = word
        if current:
            pieces.append(current)
        return pieces
    pieces = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_characters:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_long_paragraph(sentence, max_characters))
        elif len(current) + len(sentence) + bool(current) <= max_characters:
            current = f"{current} {sentence}".strip()
        else:
            pieces.append(current)
            current = sentence
    if current:
        pieces.append(current)
    return pieces


def _pack_paragraphs(
    paragraphs: Iterable[str],
    *,
    max_characters: int,
    overlap_characters: int,
) -> list[str]:
    chunks: list[str] = []
    current_units: list[str] = []
    for unit in paragraphs:
        candidate = "\n\n".join([*current_units, unit])
        if len(candidate) <= max_characters:
            current_units.append(unit)
            continue

        if current_units:
            chunks.append("\n\n".join(current_units))
        carried: list[str] = []
        for previous in reversed(current_units):
            if sum(map(len, [*carried, previous])) + 2 * len(carried) > overlap_characters:
                break
            carried.insert(0, previous)
        while carried and len("\n\n".join([*carried, unit])) > max_characters:
            carried.pop(0)
        current_units = [*carried, unit]
    if current_units:
        chunks.append("\n\n".join(current_units))
    return chunks


def chunk_legal_provision(
    source: LegalSource,
    provision: LegalProvision,
    *,
    max_characters: int = DEFAULT_CHUNK_CHARACTERS,
    overlap_characters: int = DEFAULT_OVERLAP_CHARACTERS,
) -> list[LegalTextChunk]:
    if max_characters < 256:
        raise ValueError("max_characters must be at least 256.")
    if overlap_characters < 0 or overlap_characters >= max_characters:
        raise ValueError("overlap_characters must be non-negative and less than max_characters.")

    header_parts = [f"Article {provision.article_number}"]
    if provision.sub_article_reference:
        header_parts.append(f"Sub-article {provision.sub_article_reference}")
    if provision.section_title:
        header_parts.append(provision.section_title)
    header = " — ".join(header_parts)
    body_limit = max_characters - len(header) - 2
    if body_limit < 1:
        raise ValueError("Article metadata exceeds the configured chunk size.")

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", provision.text.strip())
        if paragraph.strip()
    ]
    grouped_paragraphs: list[str] = []
    for paragraph in paragraphs:
        if grouped_paragraphs and _CONTINUATION_START.match(paragraph):
            grouped_paragraphs[-1] = f"{grouped_paragraphs[-1]}\n\n{paragraph}"
        else:
            grouped_paragraphs.append(paragraph)
    units: list[str] = []
    for paragraph in grouped_paragraphs:
        if len(paragraph) <= body_limit:
            units.append(paragraph)
        else:
            units.extend(_split_long_paragraph(paragraph, body_limit))

    bodies = _pack_paragraphs(
        units,
        max_characters=body_limit,
        overlap_characters=overlap_characters,
    )
    return [
        LegalTextChunk(
            source_id=source.id,
            provision_id=provision.id,
            article_number=provision.article_number,
            sub_article_reference=provision.sub_article_reference,
            heading=provision.section_title,
            version_label=source.version_label,
            page_number=provision.page_number,
            chunk_index=index,
            text=f"{header}\n\n{body}",
        )
        for index, body in enumerate(bodies)
    ]
