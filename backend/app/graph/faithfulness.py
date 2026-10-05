from __future__ import annotations

import re

NUM_PATTERN = re.compile(r"\b\d[\d,]*\.?\d*\b")


def extract_numbers(text: str) -> list[float]:
    """Extract all numeric literals from a text string, ignoring comma thousands separators."""
    raw = NUM_PATTERN.findall(text)
    numbers = []
    for s in raw:
        try:
            val = float(s.replace(",", ""))
            numbers.append(val)
        except ValueError:
            continue
    return numbers


def unfaithful_numbers(
    text: str,
    allowed: set[float],
    tol: float = 0.5,
) -> list[float]:
    """Identify numbers present in the generated text that do not match any known ground truth
    solver output or domain entity count within the given numerical tolerance.
    """
    found = extract_numbers(text)
    unfaithful = []
    for num in found:
        # Check if num matches any allowed number within tolerance
        matched = any(abs(num - a) <= tol for a in allowed)
        if not matched:
            unfaithful.append(num)
    return unfaithful


def check_faithfulness(
    text: str,
    allowed: set[float],
    tol: float = 0.5,
) -> tuple[bool, list[float]]:
    """Convenience wrapper returning (is_faithful, unfaithful_numbers)."""
    bad_nums = unfaithful_numbers(text, allowed, tol=tol)
    return (len(bad_nums) == 0, bad_nums)

