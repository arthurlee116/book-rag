import unittest


class TestRepackStrategy(unittest.TestCase):
    def test_repack_chunks_reverse_reverses(self) -> None:
        from backend.app.repacking import repack_chunks_reverse

        self.assertEqual(repack_chunks_reverse([1, 2, 3]), [3, 2, 1])

    def test_repack_chunks_strategy_forward_keeps_order(self) -> None:
        from backend.app.repacking import repack_chunks

        chunks = ["a", "b", "c"]
        self.assertIs(repack_chunks(chunks, strategy="forward"), chunks)

    def test_repack_chunks_strategy_reverse_reverses(self) -> None:
        from backend.app.repacking import repack_chunks

        self.assertEqual(repack_chunks(["a", "b", "c"], strategy="reverse"), ["c", "b", "a"])

    def test_repack_chunks_strategy_unknown_defaults_to_reverse(self) -> None:
        from backend.app.repacking import repack_chunks

        self.assertEqual(repack_chunks(["a", "b", "c"], strategy="???"), ["c", "b", "a"])

    def test_apply_repack_strategy_applies_configured_strategy(self) -> None:
        from backend.app.repacking import apply_repack_strategy

        chunks = ["a", "b", "c"]
        self.assertEqual(
            apply_repack_strategy(chunks, repack_strategy="reverse"),
            ["c", "b", "a"],
        )
        self.assertIs(
            apply_repack_strategy(chunks, repack_strategy="forward"),
            chunks,
        )
