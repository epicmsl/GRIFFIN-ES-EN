#!/usr/bin/env python3
"""Apply ``en_overrides`` to an existing language pack (maintainers only).

Use it after editing ``data/en-*.json`` when a full rebuild is not needed: it
rewrites ``data/language-pack-v2.json.gz`` and its SHA-256 in place.

    python apply_en_overrides.py            # apply, keep official descriptions
    python apply_en_overrides.py --dry-run  # show what would change
    python apply_en_overrides.py --force-text  # sheet text replaces official too
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import en_overrides
import language_pack


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=language_pack.DEFAULT_PACK)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-text", action="store_true",
                        help="replace official skill descriptions with the curated text too")
    args = parser.parse_args()

    pack = language_pack.load_pack(args.pack, verify=False)
    report = en_overrides.apply(pack, force_text=args.force_text)
    print(en_overrides.summary(report) or "Nothing to apply.")
    if args.dry_run:
        print("Dry run: the pack was not written.")
        return 0
    if not report["applied"]:
        print("The pack already has every override; nothing written.")
        return 0
    path = language_pack.write_pack(pack, args.pack)
    print(f"Pack: {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except en_overrides.OverrideError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
