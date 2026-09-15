import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'scripts' / 'install_skill.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'SKILL.md').write_text('skill')
        (self.source / 'scripts').mkdir()
        (self.source / 'scripts' / 'helper.py').write_text('print(1)')

    def test_copies_complete_skill_without_overwriting_edits(self):
        target = installer.install(self.root / 'user skills', self.source)
        self.assertEqual((target / 'scripts' / 'helper.py').read_text(), 'print(1)')
        (target / 'SKILL.md').write_text('personal edits')
        with self.assertRaises(FileExistsError):
            installer.install(self.root / 'user skills', self.source)
        self.assertEqual((target / 'SKILL.md').read_text(), 'personal edits')

    def test_refuses_broken_symlink_destination(self):
        dest = self.root / 'skills'
        dest.mkdir()
        link = dest / installer.SKILL_NAME
        link.symlink_to(self.root / 'missing')
        with self.assertRaises(FileExistsError):
            installer.install(dest, self.source)
        self.assertTrue(link.is_symlink())

    def test_missing_source_does_not_create_destination(self):
        dest = self.root / 'not-created'
        with self.assertRaises(FileNotFoundError):
            installer.install(dest, self.root / 'missing')
        self.assertFalse(dest.exists())

    def test_update_preserves_full_original_and_local_only_files(self):
        dest = self.root / 'skills'
        target = installer.install(dest, self.source)
        (target / 'SKILL.md').write_text('personal edits')
        (target / 'notes.txt').write_text('keep locally')
        (target / 'personal.png').write_bytes(b'personal image')
        (target / 'local-link').symlink_to(self.root / 'missing')
        (self.source / 'SKILL.md').write_text('updated instructions')
        result = installer.install(dest, self.source, update=True)
        self.assertEqual(result, target)
        self.assertEqual((target / 'SKILL.md').read_text(), 'updated instructions')
        self.assertEqual((target / 'notes.txt').read_text(), 'keep locally')
        self.assertEqual((target / 'personal.png').read_bytes(), b'personal image')
        self.assertTrue((target / 'local-link').is_symlink())
        backups = list(dest.glob(f'.{installer.SKILL_NAME}.backup-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'SKILL.md').read_text(), 'personal edits')
        self.assertEqual((backups[0] / 'notes.txt').read_text(), 'keep locally')
        self.assertEqual((backups[0] / 'personal.png').read_bytes(), b'personal image')
        self.assertTrue((backups[0] / 'local-link').is_symlink())
        self.assertEqual(list(dest.glob('*.staging-*')), [])

    def test_update_rolls_back_when_final_rename_fails(self):
        dest = self.root / 'skills'
        target = installer.install(dest, self.source)
        (target / 'SKILL.md').write_text('original')
        real_rename = Path.rename

        def fail_stage_rename(path, destination):
            if '.staging-' in path.name:
                raise OSError('simulated failure')
            return real_rename(path, destination)

        with patch.object(Path, 'rename', fail_stage_rename):
            with self.assertRaisesRegex(OSError, 'simulated failure'):
                installer.install(dest, self.source, update=True)
        self.assertEqual((target / 'SKILL.md').read_text(), 'original')
        self.assertEqual(list(dest.iterdir()), [target])

    def test_staging_failure_does_not_touch_original(self):
        dest = self.root / 'skills'
        target = installer.install(dest, self.source)
        (target / 'SKILL.md').write_text('original')
        with patch.object(installer.shutil, 'copy2', side_effect=OSError('copy failed')):
            with self.assertRaisesRegex(OSError, 'copy failed'):
                installer.install(dest, self.source, update=True)
        self.assertEqual((target / 'SKILL.md').read_text(), 'original')
        self.assertEqual(list(dest.iterdir()), [target])

    def test_selected_skill_and_repeated_updates_have_distinct_backups(self):
        dest = self.root / 'skills'
        target = installer.install(dest, self.source, skill_name='dual-image-pipeline')
        self.assertEqual(target.name, 'dual-image-pipeline')
        installer.install(dest, self.source, skill_name='dual-image-pipeline', update=True)
        installer.install(dest, self.source, skill_name='dual-image-pipeline', update=True)
        self.assertEqual(len(list(dest.glob('.dual-image-pipeline.backup-*'))), 2)
        self.assertFalse((dest / installer.SKILL_NAME).exists())

    def test_source_credentials_media_and_caches_are_not_installed(self):
        for relative in ['.env', 'credentials.json', 'audio.mp3', 'picture.png',
                         '__pycache__/helper.pyc', '__pycache__/helper.py',
                         'cache/private.md', '.git/config', 'private/note.md']:
            path = self.source / relative
            path.parent.mkdir(exist_ok=True)
            path.write_text('must not be copied')
        target = installer.install(self.root / 'skills', self.source)
        files = sorted(str(path.relative_to(target)) for path in target.rglob('*') if path.is_file())
        self.assertEqual(files, ['SKILL.md', 'scripts/helper.py'])

    def test_source_symlinks_are_refused_without_touching_destination(self):
        dest = self.root / 'skills'
        link = self.root / 'source-link'
        link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Source symlinks'):
            installer.install(dest, link)
        self.assertFalse(dest.exists())
        (self.source / 'scripts' / 'link.py').symlink_to(self.root / 'private.py')
        with self.assertRaisesRegex(ValueError, 'Source symlinks'):
            installer.install(dest, self.source)
        self.assertFalse(dest.exists())

    def test_update_refuses_existing_symlink_and_directory_conflicts(self):
        dest = self.root / 'skills'
        target = installer.install(dest, self.source)
        outside = self.root / 'outside.py'
        outside.write_text('private original')
        helper = target / 'scripts' / 'helper.py'
        helper.unlink()
        helper.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            installer.install(dest, self.source, update=True)
        self.assertEqual(outside.read_text(), 'private original')
        self.assertTrue(helper.is_symlink())
        self.assertEqual(list(dest.glob(f'.{installer.SKILL_NAME}.backup-*')), [])

    def test_update_refuses_symlink_target(self):
        dest = self.root / 'skills'
        dest.mkdir()
        (dest / installer.SKILL_NAME).symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'real directory'):
            installer.install(dest, self.source, update=True)
        self.assertEqual((self.source / 'SKILL.md').read_text(), 'skill')

    def test_refuses_overlapping_source_and_destination(self):
        with self.assertRaisesRegex(ValueError, 'overlap'):
            installer.install(self.source / 'installed', self.source)
        self.assertFalse((self.source / 'installed').exists())

    def test_refuses_unknown_skill_names(self):
        with self.assertRaisesRegex(ValueError, 'Unknown skill'):
            installer.install(self.root / 'skills', self.source, skill_name='../private')


if __name__ == '__main__':
    unittest.main()
