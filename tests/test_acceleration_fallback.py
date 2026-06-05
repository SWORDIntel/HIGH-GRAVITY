"""Tests for stdlib proxy acceleration fallback behavior."""

import unittest

from src.acceleration_fallback import NotStisla, QIHSE, TurboQuantIndex, compress_payload, decompress_payload


class AccelerationFallbackTests(unittest.TestCase):
    def test_sorted_lookup_fallbacks_preserve_exact_search(self):
        values = [-9, -1, 3, 11]
        self.assertEqual(NotStisla().search_hashes(values, 3), 2)
        self.assertEqual(QIHSE().search_sorted_int64(values, 11), 3)
        self.assertEqual(QIHSE().search_sorted_int64(values, 4), -1)

    def test_turboquant_fallback_preserves_exact_hashes(self):
        index = TurboQuantIndex()
        value = b"a" * 48
        index.add(value)
        self.assertEqual(index.search(value), value)
        self.assertIsNone(index.search(b"b" * 48))
        self.assertEqual(len(index), 1)

    def test_payload_compression_round_trip(self):
        payload = b"high-gravity" * 100
        self.assertEqual(decompress_payload(compress_payload(payload)), payload)


if __name__ == "__main__":
    unittest.main()
