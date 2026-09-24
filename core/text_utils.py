# -*- coding: utf-8 -*-
"""Deterministic Persian text normalization for local search."""
import re

_ARABIC_TO_PERSIAN = str.maketrans({
    'ي': 'ی', 'ى': 'ی', 'ك': 'ک', 'ۀ': 'ه', 'ة': 'ه',
    'ؤ': 'و', 'إ': 'ا', 'أ': 'ا', 'ٱ': 'ا', 'ـ': '',
    '\u200c': ' ', '\u200f': '', '\u200e': '',
})

def normalize_persian(value):
    value = (value or '').translate(_ARABIC_TO_PERSIAN)
    return re.sub(r'\s+', ' ', value).strip()

def search_variants(value):
    normalized = normalize_persian(value)
    variants = {value.strip(), normalized}
    if ' ' in normalized:
        variants.add(normalized.replace(' ', '\u200c'))
    return tuple(v for v in variants if v)
