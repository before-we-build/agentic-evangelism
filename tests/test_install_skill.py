import importlib.util
from pathlib import Path
import tempfile
import unittest


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


if __name__ == '__main__':
    unittest.main()
