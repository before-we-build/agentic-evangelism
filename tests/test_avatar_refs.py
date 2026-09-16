import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/suno-tiktok-video/scripts/avatar_refs.py"
SPEC = importlib.util.spec_from_file_location("avatar_refs", SCRIPT)
avatar_refs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(avatar_refs)


class AvatarReferenceTests(unittest.TestCase):
    def test_optional_avatar_applies_only_to_linked_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "avatars").mkdir()
            avatar = root / "avatars/person.png"
            avatar.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"image data")
            board = root / "storyboard.json"
            board.write_text(json.dumps({
                "characters": [
                    {"id": "person", "avatar_image": "avatars/person.png"},
                    {"id": "other"},
                ],
                "assets": [
                    {"id": "a1", "character_ids": ["person"]},
                    {"id": "a2", "character_ids": ["other"]},
                    {"id": "a3", "character_ids": []},
                ],
            }))
            result = avatar_refs.reference_manifest(board)
            self.assertEqual(result["assets"], [
                {"id": "a1", "reference_images": [str(avatar)]},
                {"id": "a2", "reference_images": []},
                {"id": "a3", "reference_images": []},
            ])

    def test_missing_avatar_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            board = Path(directory) / "storyboard.json"
            board.write_text(json.dumps({
                "characters": [{"id": "person", "avatar_image": "missing.png"}],
                "assets": [{"id": "a1", "character_ids": ["person"]}],
            }))
            with self.assertRaisesRegex(ValueError, "missing or not"):
                avatar_refs.reference_manifest(board)

    def test_unknown_character_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            board = Path(directory) / "storyboard.json"
            board.write_text(json.dumps({
                "assets": [{"id": "a1", "character_ids": ["unknown"]}],
            }))
            with self.assertRaisesRegex(ValueError, "unknown character"):
                avatar_refs.reference_manifest(board)


if __name__ == "__main__":
    unittest.main()
