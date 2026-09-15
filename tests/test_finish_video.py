"""Safety checks for the one-command Android karaoke finishing step."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/suno-tiktok-video/scripts/finish_video.py"


class FinishVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys

        sys.path.insert(0, str(SCRIPT.parent))
        spec = importlib.util.spec_from_file_location("finish_video", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_new_names_preserve_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "work"
            workspace.mkdir()
            (root / "TikTok_song_Karaoke_01.mp4").touch()
            base, final = self.module.choose_outputs(root, workspace, "song")
            self.assertEqual(base.name, "base_song_02.mp4")
            self.assertEqual(final.name, "TikTok_song_Karaoke_02.mp4")

    def test_rejects_audio_outside_downloads_before_running_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / "Download"
            downloads.mkdir()
            workspace = root / "work"
            workspace.mkdir()
            outside_audio = root / "private.mp3"
            outside_audio.write_bytes(b"audio")
            with patch.object(self.module, "check_file_stability") as stability:
                with self.assertRaisesRegex(ValueError, "Audio must be"):
                    self.module.finish(outside_audio, workspace / "storyboard.json",
                                       workspace / "timing.json", workspace, "song", downloads)
            stability.assert_not_called()

    def test_rejects_slug_path_traversal(self):
        with self.assertRaisesRegex(ValueError, "Slug must"):
            self.module.finish(Path("audio.mp3"), Path("story.json"), Path("timing.json"),
                               Path("/tmp/work"), "../other")

    def test_accepts_runtime_temporary_directory_but_checks_audio(self):
        # A Termux/PRoot runtime can choose a canonical temp root other than /tmp.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            downloads = root / 'Download'
            downloads.mkdir()
            workspace = root / 'runtime-temp' / 'work'
            workspace.mkdir(parents=True)
            with patch.object(self.module.tempfile, 'gettempdir', return_value=str(workspace.parent)):
                with patch.object(self.module, 'check_file_stability') as stability:
                    with self.assertRaisesRegex(ValueError, 'Audio must be'):
                        self.module.finish(root / 'private.mp3', workspace / 'storyboard.json',
                                           workspace / 'timing.json', workspace, 'song', downloads)
                stability.assert_not_called()

    def test_rejects_workspace_that_escapes_allowed_root_through_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            downloads = root / 'Download'
            downloads.mkdir()
            workspace = root / 'private'
            workspace.mkdir()
            (downloads / 'linked-work').symlink_to(workspace, target_is_directory=True)
            # Patch only /tmp resolution to make this independent of whichever
            # temporary root hosts the test itself.
            real_resolve = Path.resolve

            def resolve_without_test_temp(path, *args, **kwargs):
                if path == Path('/tmp'):
                    return root / 'other-system-temp'
                return real_resolve(path, *args, **kwargs)

            with patch.object(Path, 'resolve', resolve_without_test_temp):
                with patch.object(self.module.tempfile, 'gettempdir', return_value=str(root / 'other-temp')):
                    with patch.object(self.module, 'check_file_stability') as stability:
                        with self.assertRaisesRegex(ValueError, 'Workspace must be'):
                            self.module.finish(downloads / 'song.mp3', workspace / 'storyboard.json',
                                               workspace / 'timing.json', downloads / 'linked-work',
                                               'song', downloads)
                    stability.assert_not_called()


if __name__ == "__main__":
    unittest.main()
