#!/usr/bin/env python3
"""Fail CI when known-bad loose pins appear in requirements files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_DIR = ROOT / "requirements"

BAD_PATTERNS = [
    (re.compile(r"django-stubs\s*>=\s*"), "django-stubs must be pinned in typing-stubs.txt"),
    (
        re.compile(r"djangorestframework-stubs\s*>=\s*3\.17"),
        "djangorestframework-stubs 3.17+ needs django-stubs 6 / Django 5.2+",
    ),
    (
        re.compile(r"djangorestframework-stubs\s*>=\s*3\.15\s*,\s*<\s*4"),
        "use typing-stubs.txt pins instead of a wide djangorestframework-stubs range",
    ),
]

TYPING_STUBS = REQUIREMENTS_DIR / "typing-stubs.txt"
REQUIRED_IN_TYPING = ("django-stubs==5.2.9", "djangorestframework-stubs==3.16.9")


def main() -> int:
    errors: list[str] = []

    if not TYPING_STUBS.is_file():
        errors.append(f"missing {TYPING_STUBS.relative_to(ROOT)}")
    else:
        typing_text = TYPING_STUBS.read_text(encoding="utf-8")
        for line in REQUIRED_IN_TYPING:
            if line not in typing_text:
                errors.append(f"{TYPING_STUBS.name} must contain: {line}")

    for path in sorted(REQUIREMENTS_DIR.glob("*.txt")):
        if path.name == "typing-stubs.txt":
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, message in BAD_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)}: {message}")

    if errors:
        print("Invalid requirements pins:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("Requirements pins OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
