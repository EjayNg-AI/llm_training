from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from tokenizer_bpe.pretokenizer import compile_pattern, resolve_pattern


class TestPretokenizer(unittest.TestCase):
    def test_gpt2_default_determinism(self):
        alias, pattern_str, flags, _ = resolve_pattern({"pattern": "gpt2_default", "flags": []})
        self.assertEqual(alias, "gpt2_default")
        compiled = compile_pattern(pattern_str, flags)
        text = "don't stop  now\n"
        pieces = [m.group(0) for m in compiled.finditer(text)]
        self.assertEqual(pieces, [("don"), ("'t"), (" stop"), (" "), ("now"), ("\n")])

    def test_gpt2_fast_compiles(self):
        alias, pattern_str, flags, _ = resolve_pattern({"pattern": "gpt2_fast", "flags": []})
        self.assertEqual(alias, "gpt2_fast")
        compiled = compile_pattern(pattern_str, flags)
        text = "Hello 123!"
        pieces = [m.group(0) for m in compiled.finditer(text)]
        self.assertTrue(len(pieces) > 0)


if __name__ == "__main__":
    unittest.main()

