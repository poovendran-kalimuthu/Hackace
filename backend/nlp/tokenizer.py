"""
High-Speed Offline Tokenizer and Linguistic Analyzer.

Operates without external cloud NLP APIs or network downloads.
Provides sentence segmentation, word tokenization, and linguistic statistics.
"""

from __future__ import annotations
import re
from typing import Dict, List, Tuple


class OfflineTokenizer:
    """
    Deterministic, high-throughput offline tokenizer and linguistic feature extractor.
    """

    # Clean regex splitting on sentence-ending punctuation followed by whitespace and capital letter
    SENTENCE_SPLIT_REGEX = re.compile(
        r"(?<=[.?!])\s+(?=[A-Z0-9\"'“‘])",
        re.UNICODE,
    )
    # Known abbreviation tokens to re-merge if split
    ABBREVIATIONS = {"mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "vs.", "etc.", "e.g.", "i.e."}
    WORD_REGEX = re.compile(r"\b\w+\b", re.UNICODE)
    PUNCTUATION_REGEX = re.compile(r"[^\w\s]", re.UNICODE)

    @classmethod
    def split_sentences(cls, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        parts = cls.SENTENCE_SPLIT_REGEX.split(text.strip())
        return [p.strip() for p in parts if p.strip()]

    @classmethod
    def tokenize_words(cls, text: str) -> List[str]:
        if not text:
            return []
        return cls.WORD_REGEX.findall(text)

    @classmethod
    def extract_linguistic_stats(cls, text: str) -> Dict[str, float]:
        if not text:
            return {
                "word_count": 0.0,
                "char_count": 0.0,
                "sentence_count": 0.0,
                "avg_sentence_len": 0.0,
                "uppercase_ratio": 0.0,
                "digit_ratio": 0.0,
                "punctuation_density": 0.0,
                "is_single_sentence": 0.0,
                "ends_with_colon": 0.0,
                "ends_with_question": 0.0,
            }

        length = len(text)
        words = cls.tokenize_words(text)
        word_count = len(words)
        sentences = cls.split_sentences(text)
        sentence_count = max(1, len(sentences))

        uppercase_chars = sum(1 for c in text if c.isupper())
        digits = sum(1 for c in text if c.isdigit())
        punct_count = len(cls.PUNCTUATION_REGEX.findall(text))

        stripped = text.strip()

        return {
            "word_count": float(word_count),
            "char_count": float(length),
            "sentence_count": float(sentence_count),
            "avg_sentence_len": float(word_count / sentence_count),
            "uppercase_ratio": float(uppercase_chars / max(1, length)),
            "digit_ratio": float(digits / max(1, length)),
            "punctuation_density": float(punct_count / max(1, length)),
            "is_single_sentence": 1.0 if sentence_count == 1 else 0.0,
            "ends_with_colon": 1.0 if stripped.endswith(":") else 0.0,
            "ends_with_question": 1.0 if stripped.endswith("?") else 0.0,
        }
