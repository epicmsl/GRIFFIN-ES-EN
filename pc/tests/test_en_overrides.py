import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import en_overrides
import language_pack


def make_pack(en=None, machine=()):
    return {"format": language_pack.FORMAT, "keys": "sha1-16", "profiles": [],
            "main": {"en": dict(en or {}), "es": {}}, "builtin": {"en": {}, "es": {}},
            "machine": {"main": {"en": set(machine), "es": set()}, "builtin": {"en": set(), "es": set()}}}


class OverrideDataTests(unittest.TestCase):
    def test_files_exist_and_are_well_formed(self):
        overrides = en_overrides.load()
        for section in ("skill_names", "weapon_names", "key_names", "stat_names", "terms", "segment_text"):
            self.assertTrue(overrides[section], f"{section} overrides are missing")
        for section, mapping in overrides.items():
            for source, text in mapping.items():
                self.assertTrue(source.strip() and text.strip(), f"{section}: empty entry")
                if source != text:
                    self.assertIsNone(en_overrides.CJK.search(text), f"{section}: CJK left in {text!r}")
                else:
                    self.assertIsNone(en_overrides.CJK.search(source),
                                      f"{section}: {source!r} keeps the Chinese")

    def test_latin_identity_is_allowed(self):
        overrides = en_overrides.load()
        self.assertEqual(overrides["terms"]["OTs-14"], "OTs-14")

    def test_sheet_naming_is_used(self):
        overrides = en_overrides.load()
        self.assertEqual(overrides["skill_names"]["星群追应"], "Constellation Pursuit")
        self.assertEqual(overrides["skill_names"]["战场微芒"], "Faint Glow of the Battlefield")
        self.assertEqual(overrides["key_names"]["固键·隐形守护"], "Fixed Key - Invisible Guardian")
        self.assertEqual(overrides["key_names"]["跃键·备受宠爱的猫咪"], "Expansion Key - The Beloved Cat")
        self.assertEqual(overrides["stat_names"]["暴击伤害"], "Crit DMG")

    def test_one_english_name_per_key(self):
        overrides = en_overrides.load()["key_names"]
        by_english = {}
        for chinese, english in overrides.items():
            self.assertNotIn(english, by_english,
                             f"{english!r} is used for both {by_english.get(english)!r} and {chinese!r}")
            by_english[english] = chinese

    def test_broken_file_is_reported(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "en-skill-names.json").write_text("{not json", encoding="utf-8")
            with self.assertRaises(en_overrides.OverrideError):
                en_overrides.load(Path(directory))


class ApplyTests(unittest.TestCase):
    def test_names_replace_official_text(self):
        key = language_pack.key_of("星群追应")
        pack = make_pack({key: "Stellar Pursuit"})
        report = en_overrides.apply(pack, {"skill_names": {"星群追应": "Constellation Pursuit"}})
        self.assertEqual(pack["main"]["en"][key], "Constellation Pursuit")
        self.assertEqual(report["replaced_official"], 1)

    def test_machine_text_is_replaced_and_flagged_as_curated(self):
        key = language_pack.key_of("轨炮裁决")
        pack = make_pack({key: "Yeah."}, {key})
        en_overrides.apply(pack, {"skill_text": {"轨炮裁决": "Railgun Judgement"}})
        self.assertEqual(pack["main"]["en"][key], "Railgun Judgement")
        self.assertNotIn(key, pack["machine"]["main"]["en"])

    def test_official_description_is_kept_unless_forced(self):
        key = language_pack.key_of("轨道炮")
        pack = make_pack({key: "Official text."})
        overrides = {"skill_text": {"轨道炮": "Sheet text."}}
        en_overrides.apply(pack, overrides)
        self.assertEqual(pack["main"]["en"][key], "Official text.")
        en_overrides.apply(pack, overrides, force_text=True)
        self.assertEqual(pack["main"]["en"][key], "Sheet text.")

    def test_missing_line_is_added(self):
        key = language_pack.key_of("新的技能")
        pack = make_pack()
        report = en_overrides.apply(pack, {"skill_names": {"新的技能": "New Skill"}})
        self.assertEqual(pack["main"]["en"][key], "New Skill")
        self.assertEqual(report["added"], 1)

    def test_apply_is_idempotent(self):
        key = language_pack.key_of("生命")
        pack = make_pack({key: "Life."}, {key})
        overrides = {"stat_names": {"生命": "HP"}}
        first = en_overrides.apply(pack, overrides)
        second = en_overrides.apply(pack, overrides)
        self.assertEqual(first["applied"], 1)
        self.assertEqual(second["applied"], 0)
        self.assertEqual(second["unchanged"], 1)

    def test_spanish_is_never_touched(self):
        pack = make_pack()
        es_key = language_pack.key_of("生命")
        pack["main"]["es"][es_key] = "Vida"
        en_overrides.apply(pack, {"stat_names": {"生命": "HP"}})
        self.assertEqual(pack["main"]["es"][es_key], "Vida")


if __name__ == "__main__":
    unittest.main()
