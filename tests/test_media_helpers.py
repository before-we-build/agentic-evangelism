import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / 'skills' / 'suno-tiktok-video' / 'scripts'
if str(HELPERS) not in sys.path:
    sys.path.insert(0, str(HELPERS))

spec = importlib.util.spec_from_file_location('build_video', HELPERS / 'build_video.py')
build_video_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_video_module)
calculate_timeline = build_video_module.calculate_timeline


class TimelineTests(unittest.TestCase):
    def test_single_scene_uses_concat_mode(self):
        clips, offsets, t = calculate_timeline([5.0], 5.0, transition='fade', transition_duration=0.75)
        self.assertEqual(clips, [125])
        self.assertIsNone(offsets)
        self.assertIsNone(t)

    def test_transition_none_uses_concat_mode(self):
        clips, offsets, t = calculate_timeline([3.0, 3.0], 6.0, transition='none', transition_duration=0.75)
        self.assertEqual(clips, [75, 75])
        self.assertIsNone(offsets)
        self.assertIsNone(t)

    def test_default_transition_is_fade(self):
        clips, offsets, t = calculate_timeline([3.0, 4.0, 3.0], 10.0)
        self.assertIsNotNone(offsets)
        self.assertEqual(len(offsets), 2)
        total_frames = 250
        self.assertEqual(offsets[-1] + clips[-1], total_frames)

    def test_fade_transition_covers_exact_total_frames(self):
        clips, offsets, t = calculate_timeline([3.0, 4.0, 3.0], 10.0, transition='fade', transition_duration=0.75)
        self.assertIsNotNone(offsets)
        self.assertEqual(len(offsets), 2)
        total_frames = 250
        self.assertEqual(offsets[-1] + clips[-1], total_frames)
        # Ensure transitions do not collide
        self.assertGreaterEqual(offsets[1], offsets[0] + t)

    def test_tiny_scenes_fallback_safely(self):
        clips, offsets, t = calculate_timeline([0.04, 0.04], 0.08, transition='fade', transition_duration=0.75)
        self.assertEqual(clips, [1, 1])
        self.assertIsNone(offsets)
        self.assertIsNone(t)


class CliArgsTests(unittest.TestCase):
    def test_build_video_custom_binary_not_found(self):
        proc = subprocess.run([
            sys.executable, str(HELPERS / 'build_video.py'),
            '--audio', 'dummy.mp3', '--image', 'dummy.png', '--output', 'dummy.mp4',
            '--ffmpeg', '/non/existent/path/ffmpeg'
        ], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('not installed or not executable', proc.stderr)

    def test_extract_lyrics_custom_binary_not_found(self):
        proc = subprocess.run([
            sys.executable, str(HELPERS / 'extract_lyrics.py'),
            '--audio', 'dummy.mp3', '--output', 'dummy.json',
            '--ffprobe', '/non/existent/path/ffprobe'
        ], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('not installed or not executable', proc.stderr)

    def test_build_video_invalid_license_choice(self):
        proc = subprocess.run([
            sys.executable, str(HELPERS / 'build_video.py'),
            '--audio', 'dummy.mp3', '--image', 'dummy.png', '--output', 'dummy.mp4',
            '--license', 'invalid_choice'
        ], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('invalid choice', proc.stderr)

    def test_build_video_invalid_attribution_lang(self):
        proc = subprocess.run([
            sys.executable, str(HELPERS / 'build_video.py'),
            '--audio', 'dummy.mp3', '--image', 'dummy.png', '--output', 'dummy.mp4',
            '--attribution-lang', 'de'
        ], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('invalid choice', proc.stderr)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg / FFprobe')
class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.audio = self.work / 'test audio.wav'
        with wave.open(str(self.audio), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(b'\0\0' * 19200)
        for number, rgb in enumerate(((100, 30, 20), (20, 30, 100)), 1):
            (self.work / f'{number}.ppm').write_bytes(b'P6\n16 16\n255\n' + bytes(rgb) * 256)

    def board(self, lengths):
        path = self.work / 'storyboard.json'
        path.write_text(json.dumps({'scenes': [
            {'image': f'{i}.ppm', 'duration_seconds': length}
            for i, length in enumerate(lengths, 1)]}))
        return path

    def build(self, board):
        return subprocess.run([
            sys.executable, str(HELPERS / 'build_video.py'), '--audio', str(self.audio),
            '--storyboard', str(board), '--output', str(self.work / 'result.mp4')],
            text=True, capture_output=True, timeout=90)

    def test_complete_two_scene_video_and_overwrite_refusal(self):
        board = self.board([0.4, 0.4])
        result = self.build(board)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(report['decode_verified'])
        self.assertEqual(report['resolution'], '1080x1920')
        self.assertAlmostEqual(report['duration'], 0.8, delta=0.15)
        before = (self.work / 'result.mp4').read_bytes()
        again = self.build(board)
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual((self.work / 'result.mp4').read_bytes(), before)

    def test_complete_two_scene_video_with_fade_transition(self):
        board = self.board([0.4, 0.4])
        result = subprocess.run([
            sys.executable, str(HELPERS / 'build_video.py'), '--audio', str(self.audio),
            '--storyboard', str(board), '--transition', 'fade',
            '--transition-duration', '0.2', '--output', str(self.work / 'result_fade.mp4')],
            text=True, capture_output=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(report['decode_verified'])
        self.assertEqual(report['transition'], 'fade')
        self.assertAlmostEqual(report['duration'], 0.8, delta=0.15)

    def test_incomplete_timeline_does_not_create_video(self):
        result = self.build(self.board([0.2, 0.2]))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cover the full audio', result.stderr)
        self.assertFalse((self.work / 'result.mp4').exists())

    def test_lyrics_found_and_missing_are_distinguished(self):
        spec = importlib.util.spec_from_file_location('lyrics', HELPERS / 'extract_lyrics.py')
        lyrics = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lyrics)
        self.assertEqual(lyrics.extract(self.audio)['status'], 'missing')
        tagged = self.work / 'lyrics.mp3'
        text = '[Verse]\nТестовий рядок'
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-i', str(self.audio),
                        '-metadata', f'lyrics={text}', str(tagged)], check=True, timeout=30)
        extracted = lyrics.extract(tagged)
        self.assertEqual(extracted['status'], 'found')
        self.assertEqual(extracted['lyrics_candidates'][0]['raw'], text)
        self.assertEqual(extracted['lyrics_candidates'][0]['clean'], 'Тестовий рядок')


if __name__ == '__main__':
    unittest.main()
