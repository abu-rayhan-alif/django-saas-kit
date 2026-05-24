#!/usr/bin/env python3
"""Fail CI when known-bad loose pins appear in requirements files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_DIR = ROOT / "requirements"

STUB_NAMES = ("django-stubs", "djangorestframework-stubs")

BAD_PATTERNS = [
    (re.compile(r"django-stubs\s*>=\s*"), "django-stubs must be pinned in typing-stubs.txt"),
    (re.compile(r"django-stubs\s*==\s*"), "move django-stubs pin to typing-stubs.txt"),
    (
        re.compile(r"djangorestframework-stubs\s*>=\s*"),
        "djangorestframework-stubs must be pinned in typing-stubs.txt",
    ),
    (
        re.compile(r"djangorestframework-stubs\s*==\s*"),
        "move djangorestframework-stubs pin to typing-stubs.txt",
    ),
]

ALLOW_STUB_FILES = frozenset({"typing-stubs.txt", "constraints.txt"})

TYPING_STUBS = REQUIREMENTS_DIR / "typing-stubs.txt"
LOCAL_TXT = REQUIREMENTS_DIR / "local.txt"
REQUIRED_IN_TYPING = ("django-stubs==5.2.9", "djangorestframework-stubs==3.16.9")
REQUIRED_LOCAL_INCLUDE = "-r typing-stubs.txt"


def main() -> int:
    errors: list[str] = []

    if not TYPING_STUBS.is_file():
        errors.append(f"missing {TYPING_STUBS.relative_to(ROOT)}")
    else:
        typing_text = TYPING_STUBS.read_text(encoding="utf-8")
        for line in REQUIRED_IN_TYPING:
            if line not in typing_text:
                errors.append(f"{TYPING_STUBS.name} must contain: {line}")

    if LOCAL_TXT.is_file():
        local_text = LOCAL_TXT.read_text(encoding="utf-8")
        if REQUIRED_LOCAL_INCLUDE not in local_text:
            errors.append(f"{LOCAL_TXT.name} must include: {REQUIRED_LOCAL_INCLUDE}")
    else:
        errors.append(f"missing {LOCAL_TXT.relative_to(ROOT)}")

    for path in sorted(REQUIREMENTS_DIR.glob("*.txt")):
        if path.name in ALLOW_STUB_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, message in BAD_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)}: {message}")

    if errors:
        print("Invalid requirements pins:", file=sys.stderr)
        print(
            "Merge latest main (typing-stubs.txt) or close Dependabot stubs PRs.",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("Requirements pins OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
