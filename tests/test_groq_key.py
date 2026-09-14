import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "groq_key.py"
spec = importlib.util.spec_from_file_location("groq_key", SCRIPT)
groq_key = importlib.util.module_from_spec(spec)
spec.loader.exec_module(groq_key)


class GroqKeyTests(unittest.TestCase):
    def test_key_persists_privately_and_can_be_rotated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "groq-api-key"
            groq_key.save_key(path, "first-key")
            self.assertEqual(groq_key.load_key(path), "first-key")
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            groq_key.save_key(path, "second-key")
            self.assertEqual(groq_key.load_key(path), "second-key")

    def test_rejects_public_file_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "groq-api-key"
            path.write_text("fake-key", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                groq_key.load_key(path)
            path.chmod(0o600)
            link = Path(directory) / "link"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                groq_key.load_key(link)

    def test_rejects_empty_or_whitespace_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "groq-api-key"
            for bad_key in ("", "  ", "two words"):
                with self.assertRaises(ValueError):
                    groq_key.save_key(path, bad_key)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
