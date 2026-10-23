import re
import unittest


YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class YouTubeIdValidationTests(unittest.TestCase):
    def test_valid_video_id(self):
        self.assertTrue(YOUTUBE_ID.fullmatch("abcdefghijk"))

    def test_rejects_invalid_or_path_like_id(self):
        for value in ("", "../secret", "short", "abcdefghijk/../x", "x" * 12):
            with self.subTest(value=value):
                self.assertIsNone(YOUTUBE_ID.fullmatch(value))


if __name__ == "__main__":
    unittest.main()
