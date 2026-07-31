import re
import unittest
from pathlib import Path

import app


ROOT = Path(__file__).resolve().parents[1]


class ProjectMetadataTests(unittest.TestCase):
    def test_default_hotkeys_are_distinct(self):
        self.assertEqual(app.DEFAULT_CONFIG["hotkey"], "right_alt")
        self.assertNotEqual(
            app.DEFAULT_CONFIG["hotkey"],
            app.DEFAULT_CONFIG["translation_hotkey"],
        )

    def test_hotkey_normalization(self):
        cases = {
            "right_alt": "right_alt",
            "Ctrl+Space": "ctrl+space",
            "shift+ctrl+F12": "ctrl+shift+f12",
            "Alt+`": "alt+oem_3",
            "Mouse4": "mouse_x1",
            "xbutton2": "mouse_x2",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(app.normalize_hotkey(value), expected)

        self.assertEqual(app.normalize_hotkey("unknown+space"), "right_alt")

    def test_reserved_hotkeys(self):
        for value in ("alt+tab", "alt+f4", "ctrl+alt+delete", "win+l"):
            with self.subTest(value=value):
                self.assertTrue(app.hotkey_is_reserved(value))
        self.assertFalse(app.hotkey_is_reserved("ctrl+space"))

    def test_hotkey_labels_are_localized(self):
        app.set_interface_language("ru")
        self.assertEqual(app.hotkey_label("ctrl+space"), "Ctrl+Пробел")
        app.set_interface_language("en")
        try:
            self.assertEqual(app.hotkey_label("ctrl+space"), "Ctrl+Space")
            self.assertEqual(
                app.hotkey_label("mouse_x1"),
                "Mouse Side Button 1",
            )
        finally:
            app.set_interface_language("ru")

    def test_supported_whisper_models_are_complete(self):
        self.assertEqual(
            set(app.WHISPER_MODELS),
            {"tiny", "base", "small", "medium", "large-v3"},
        )

        for model_id, model in app.WHISPER_MODELS.items():
            with self.subTest(model=model_id):
                self.assertTrue(
                    {"config.json", "model.bin", "tokenizer.json"}
                    <= set(model["files"])
                )
                for filename, (size, sha256) in model["files"].items():
                    with self.subTest(model=model_id, file=filename):
                        self.assertGreater(size, 0)
                        self.assertRegex(sha256, r"^[0-9a-f]{64}$")

    def test_installer_and_application_versions_match(self):
        installer = (ROOT / "installer.iss").read_text(encoding="utf-8-sig")
        match = re.search(r'#define MyAppVersion "([^"]+)"', installer)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), app.APP_VERSION)

    def test_english_model_names_do_not_contain_cyrillic(self):
        app.set_interface_language("en")
        try:
            for model_id in app.WHISPER_MODELS:
                with self.subTest(model=model_id):
                    label = app.model_label(model_id)
                    self.assertIsNone(re.search(r"[А-Яа-яЁё]", label))
        finally:
            app.set_interface_language("ru")


if __name__ == "__main__":
    unittest.main()
