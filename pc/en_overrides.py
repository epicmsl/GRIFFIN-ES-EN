"""Hand-curated English for Doll skills and weapon names (maintainers only).

Most of the English the patch shows comes from the Global client's own tables.
Three kinds of lines need a curated English instead, and they are kept here so the
release never depends on the community sheet at runtime:

* the offline Argos fallback of Dolls and weapons newer than the pinned Global
  build (for example Asteria, Eagletta, Cecilia, Agent, Colphne: Doppelgänger,
  Igla and Destroyer), whose machine text is unusable;
* the naming the community sheet *GFL2 Official Release Info Compilation* settles
  on where Global is ambiguous or outdated (``Stellar Pursuit`` there is
  ``Constellation Pursuit`` in the sheet, ``Battlefield Glow`` is ``Faint Glow of
  the Battlefield``...);
* lines with no translation at all, which would otherwise stay Chinese.

The same file set also fixes stat labels (``暴击`` -> ``Crit Rate``, ``暴击伤害`` ->
``Crit DMG``, ``生命`` -> ``HP``...) that the offline models read as ordinary words
("Riot", "Assault injuries", "Life.").

The files are UTF-8 JSON objects ``{chinese source: english}``. The key is the
exact Chinese text of the table row, the same text the pack is keyed by, so an
override keeps working across client builds. Spanish is never touched here: the
Spanish pack keeps its own text and its own quality filter.

``build_language_pack.py`` applies these while building the release pack, and
``apply_en_overrides.py`` applies them to an existing pack without rebuilding it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import language_pack

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"

SECTIONS = {
    "skill_names": "en-skill-names.json",
    "skill_text": "en-skill-text.json",
    "weapon_names": "en-weapon-names.json",
    "key_names": "en-key-names.json",
    "key_text": "en-key-text.json",
    "stat_names": "en-stat-names.json",
    "terms": "en-terms.json",
    "segment_text": "en-segment-text.json",
}

# Sections that only replace machine or missing text by default: the official
# Global description already reads well, so a curated one is a last resort there.
TEXT_SECTIONS = frozenset({"skill_text", "key_text", "segment_text"})

CJK = re.compile(r"[\u4e00-\u9fff]")


class OverrideError(RuntimeError):
    pass


def load(directory: Path | None = None) -> dict[str, dict[str, str]]:
    """Read every override file. Missing files are allowed and mean "no overrides"."""
    directory = directory or DATA_DIR
    overrides: dict[str, dict[str, str]] = {}
    for section, filename in SECTIONS.items():
        path = directory / filename
        if not path.is_file():
            overrides[section] = {}
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise OverrideError(f"{filename} is not valid JSON") from exc
        if not isinstance(raw, dict):
            raise OverrideError(f"{filename} must be a JSON object")
        cleaned: dict[str, str] = {}
        for source, text in raw.items():
            if not isinstance(source, str) or not isinstance(text, str):
                raise OverrideError(f"{filename} has a non-string entry")
            source, text = source.strip(), text.strip()
            if not source or not text:
                raise OverrideError(f"{filename} has an empty entry")
            if CJK.search(text):
                raise OverrideError(f"{filename}: {text!r} still has Chinese")
            if text == source and CJK.search(source):
                raise OverrideError(f"{filename}: {source!r} is not translated")
            cleaned[source] = text
        overrides[section] = cleaned
    return overrides


def apply(pack: dict, overrides: dict[str, dict[str, str]] | None = None, *,
          force_text: bool = False) -> dict:
    """Write the overrides into a loaded pack and return a per-section report.

    Names are always applied. ``skill_text`` replaces only machine or missing
    text unless ``force_text`` is set, so an official Global description is kept
    by default. Any key that is overridden stops being flagged as machine.
    """
    overrides = overrides if overrides is not None else load()
    english = pack["main"]["en"]
    machine = pack["machine"]["main"]["en"]
    report: dict = {"applied": 0, "added": 0, "replaced_machine": 0, "replaced_official": 0,
                    "kept_official": 0, "unchanged": 0, "sections": {}}
    for section, mapping in overrides.items():
        counts = {"applied": 0, "added": 0, "replaced_machine": 0, "replaced_official": 0,
                  "kept_official": 0, "unchanged": 0}
        for source, text in mapping.items():
            key = language_pack.key_of(source)
            current = english.get(key, "")
            if current == text:
                counts["unchanged"] += 1
                continue
            if current and section in TEXT_SECTIONS and not force_text and key not in machine:
                counts["kept_official"] += 1
                continue
            if not current:
                counts["added"] += 1
            elif key in machine:
                counts["replaced_machine"] += 1
            else:
                counts["replaced_official"] += 1
            english[key] = text
            machine.discard(key)
            counts["applied"] += 1
        report["sections"][section] = counts
        for field in counts:
            report[field] += counts[field]
    return report


def summary(report: dict) -> str:
    """One-line-per-section human summary, used by the CLI and the pack builder."""
    lines = []
    for section, counts in report["sections"].items():
        if not counts["applied"] and not counts["unchanged"]:
            continue
        lines.append(f"{section}: {counts['applied']:,} applied "
                     f"(new {counts['added']:,}, machine {counts['replaced_machine']:,}, "
                     f"official {counts['replaced_official']:,}), "
                     f"{counts['kept_official']:,} official kept, "
                     f"{counts['unchanged']:,} already in place")
    return "\n".join(lines)
