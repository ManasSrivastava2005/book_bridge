"""Token-budgeted paragraph/sentence packing without document truncation."""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    tokens: int


def clean_text(text: str) -> str:
    # Preserve line boundaries, formulas and Unicode terminology.
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\x00', '')
    return re.sub(r'\n{3,}', '\n\n', re.sub(r'[^\S\n]+', ' ', text)).strip()


def chunk_text(text, tokenizer, budget=400, max_chunks=512):
    if budget < 16:
        raise ValueError('Token budget is too small')
    def count(value):
        return len(tokenizer.encode(value, add_special_tokens=False, verbose=False))

    def split_unit(value):
        if count(value) <= budget:
            yield value
            return
        sentences = re.split(r'(?<=[.!?])\s+|\n', value)
        if len(sentences) > 1:
            for sentence in sentences:
                if sentence.strip():
                    yield from split_unit(sentence.strip())
            return
        words = value.split()
        if len(words) > 1:
            current = ''
            for word in words:
                joined = (current + ' ' + word).strip()
                if count(joined) <= budget:
                    current = joined
                else:
                    if current:
                        yield current
                    if count(word) > budget:
                        yield from split_unit(word)
                        current = ''
                    else:
                        current = word
            if current:
                yield current
            return
        # Only an individual overlong token/word needs character splitting.
        remaining = value
        while remaining:
            # Bound tokenizer work even for a megabyte-long unbroken string.
            low, high = 1, min(len(remaining), budget * 16)
            while low < high:
                mid = (low + high + 1) // 2
                if count(remaining[:mid]) <= budget:
                    low = mid
                else:
                    high = mid - 1
            yield remaining[:low]
            remaining = remaining[low:]

    chunks, current = [], ''
    for paragraph in re.split(r'\n\s*\n', clean_text(text)):
        if not paragraph:
            continue
        for unit in split_unit(paragraph):
            candidate = current + '\n\n' + unit if current else unit
            if count(candidate) <= budget:
                current = candidate
            else:
                chunks.append(TextChunk(current, count(current)))
                if len(chunks) >= max_chunks:
                    raise ValueError('Document exceeds the chunk limit; submit one chapter at a time.')
                current = unit
    if current:
        chunks.append(TextChunk(current, count(current)))
    if len(chunks) > max_chunks:
        raise ValueError('Document exceeds the chunk limit; submit one chapter at a time.')
    return chunks
