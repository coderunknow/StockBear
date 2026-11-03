"""Optional NumPy training-feature differential tests (no PyTorch needed)."""
import sys
from pathlib import Path
import unittest

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import nnue_features as f


class BatchFeatures(unittest.TestCase):
    def test_all_king_squares_and_perspectives(self):
        rng = np.random.default_rng(20261102)
        boards = []
        for square in range(64):
            board = np.zeros(64, dtype=np.uint8)
            board[square] = 6
            board[(square + 31) % 64] = 12
            free = np.flatnonzero(board == 0)
            chosen = rng.choice(free, size=16, replace=False)
            board[chosen] = rng.choice([1, 2, 3, 4, 5, 7, 8, 9, 10, 11], 16)
            boards.append(board)
        boards = np.stack(boards)
        for buckets in (1, 4, 16, 64):
            for side in (0, 1):
                sides = np.full(64, side, dtype=np.uint8)
                flat, offsets = f.batch_indices(boards, sides, buckets)
                self.assertEqual(len(offsets), 129)
                self.assertEqual(offsets[-1], len(flat))
                for row, board in enumerate(boards):
                    expected = f.ordered_features(board, side, buckets)
                    for perspective in (0, 1):
                        i = 2 * row + perspective
                        np.testing.assert_array_equal(
                            np.sort(flat[offsets[i]:offsets[i + 1]]), expected[perspective])

    def test_invalid_and_empty(self):
        boards = np.zeros((1, 64), dtype=np.uint8)
        with self.assertRaises(ValueError):
            f.batch_indices(boards, np.array([0]), 16)
        with self.assertRaises(ValueError):
            f.batch_indices(boards, np.array([0]), 3)
        flat, offsets = f.batch_indices(boards[:0], np.array([], dtype=np.uint8), 64)
        self.assertEqual(len(flat), 0)
        np.testing.assert_array_equal(offsets, [0])


if __name__ == "__main__":
    unittest.main()
