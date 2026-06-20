import unittest

from app.services.chunking import chunk_text, find_chunk_end


class ChunkTextTests(unittest.TestCase):
    def test_prefers_sentence_boundary_within_lookahead(self):
        text = f"{'a' * 20}. {'b' * 30}"

        chunks = chunk_text(
            text,
            chunk_size=18,
            overlap=0,
            lookahead=10,
        )

        self.assertEqual(chunks[0], f"{'a' * 20}.")

    def test_falls_back_to_whitespace_within_lookahead(self):
        text = f"{'a' * 20} {'b' * 30}"

        chunks = chunk_text(
            text,
            chunk_size=18,
            overlap=0,
            lookahead=5,
        )

        self.assertEqual(chunks[0], "a" * 20)

    def test_uses_exact_target_for_unbroken_text(self):
        text = "abcdefghijklmnopqrstuvwxyz"

        chunks = chunk_text(
            text,
            chunk_size=10,
            overlap=0,
            lookahead=5,
        )

        self.assertEqual(chunks[0], "abcdefghij")

    def test_preserves_requested_overlap(self):
        text = "abcdefghijklmnopqrstuvwxyz"

        chunks = chunk_text(
            text,
            chunk_size=10,
            overlap=3,
            lookahead=0,
        )

        self.assertEqual(chunks[0][-3:], chunks[1][:3])

    def test_chunk_never_exceeds_target_plus_lookahead(self):
        text = ("word " * 100).strip()
        chunk_size = 40
        lookahead = 10

        chunks = chunk_text(
            text,
            chunk_size=chunk_size,
            overlap=5,
            lookahead=lookahead,
        )

        self.assertTrue(
            all(len(chunk) <= chunk_size + lookahead for chunk in chunks)
        )

    def test_rejects_invalid_settings(self):
        invalid_settings = (
            {"chunk_size": 0},
            {"chunk_size": 10, "overlap": -1},
            {"chunk_size": 10, "overlap": 10},
            {"lookahead": -1},
        )

        for settings in invalid_settings:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    chunk_text("example text", **settings)


class FindChunkEndTests(unittest.TestCase):
    def test_returns_text_length_at_end(self):
        self.assertEqual(find_chunk_end("short", 5, 5), 5)


if __name__ == "__main__":
    unittest.main()
