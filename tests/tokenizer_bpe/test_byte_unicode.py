from tokenizer_bpe.byte_unicode import bytes_to_unicode, token_bytes_to_string, token_string_to_bytes


def test_mapping_is_invertible():
    byte_to_unicode, unicode_to_byte = bytes_to_unicode()
    assert len(byte_to_unicode) == 256
    assert len(unicode_to_byte) == 256
    for b in range(256):
        assert unicode_to_byte[byte_to_unicode[b]] == b


def test_round_trip_all_bytes():
    byte_to_unicode, unicode_to_byte = bytes_to_unicode()
    payload = bytes(range(256))
    token_string = token_bytes_to_string(payload, byte_to_unicode)
    restored = token_string_to_bytes(token_string, unicode_to_byte)
    assert restored == payload


def test_ascii_bytes_keep_expected_identity():
    byte_to_unicode, unicode_to_byte = bytes_to_unicode()
    assert byte_to_unicode[65] == "A"
    assert unicode_to_byte["A"] == 65
