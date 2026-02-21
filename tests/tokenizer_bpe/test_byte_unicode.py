from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from tokenizer_bpe.byte_unicode import bytes_to_unicode, token_bytes_to_string, token_string_to_bytes


class TestByteUnicode(unittest.TestCase):
    def test_mapping_is_invertible(self):
        byte_to_unicode, unicode_to_byte = bytes_to_unicode()
        self.assertEqual(len(byte_to_unicode), 256)
        self.assertEqual(len(unicode_to_byte), 256)
        for b in range(256):
            self.assertEqual(unicode_to_byte[byte_to_unicode[b]], b)

    def test_round_trip_bytes(self):
        byte_to_unicode, unicode_to_byte = bytes_to_unicode()
        payload = bytes(range(256))
        token_string = token_bytes_to_string(payload, byte_to_unicode)
        restored = token_string_to_bytes(token_string, unicode_to_byte)
        self.assertEqual(restored, payload)


if __name__ == "__main__":
    unittest.main()

