import unittest
from src.core.analyzer import analyze_url, format_duration, label_for_height, parse_height
from src.core.downloader import DownloadTask, build_ydl_opts, format_speed


class TestCoreLogic(unittest.TestCase):
    def test_format_duration(self):
        self.assertEqual(format_duration(None), "--:--")
        self.assertEqual(format_duration(65), "01:05")
        self.assertEqual(format_duration(3661), "1:01:01")

    def test_height_parsing_and_labels(self):
        self.assertEqual(label_for_height(2160), "2160p (4K)")
        self.assertEqual(label_for_height(1440), "1440p (2K)")
        self.assertEqual(label_for_height(1080), "1080p")
        self.assertEqual(parse_height("2160p (4K)"), 2160)
        self.assertEqual(parse_height("720p"), 720)

    def test_invalid_url_rejected(self):
        with self.assertRaises(ValueError):
            analyze_url("no-es-un-url")

    def test_build_ydl_opts_video_and_audio(self):
        video_task = DownloadTask(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Test Video",
            mode="video",
            container="mp4",
            quality="1080p",
            output_dir="C:/Downloads",
        )
        v_opts = build_ydl_opts(video_task, lambda _d: None)
        self.assertIn("1080", v_opts["format"])
        self.assertTrue(v_opts["noplaylist"])

        audio_task = DownloadTask(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Test Audio",
            mode="audio",
            container="mp3",
            quality="320 kbps",
            output_dir="C:/Downloads",
        )
        a_opts = build_ydl_opts(audio_task, lambda _d: None)
        self.assertEqual(a_opts["format"], "bestaudio/best")
        self.assertEqual(a_opts["postprocessors"][0]["preferedformat"], "mp3")
        self.assertIn("320k", a_opts["postprocessor_args"]["videoconvertor"])

    def test_format_speed(self):
        self.assertEqual(format_speed(None), "-- MB/s")
        self.assertEqual(format_speed(2 * 1024 * 1024), "2.0 MB/s")
        self.assertEqual(format_speed(500 * 1024), "500 KB/s")


if __name__ == "__main__":
    unittest.main()
