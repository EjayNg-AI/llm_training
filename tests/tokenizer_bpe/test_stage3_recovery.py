import logging
from pathlib import Path

from tokenizer_bpe.io_atomic import atomic_dump_pickle_with_checksum
from tokenizer_bpe.stage3_train import load_latest_snapshot, parse_wal_commits


def test_wal_ignores_uncommitted_begin(tmp_path):
    wal = tmp_path / "merges.wal"
    wal.write_text(
        "BEGIN\t1\t2\t3\t10\n"
        "COMMIT\t1\t256\n"
        "BEGIN\t2\t4\t5\t8\n",
        encoding="utf-8",
    )
    commits = parse_wal_commits(wal)
    assert commits == [(1, 2, 3, 256)]


def test_snapshot_loader_skips_corrupt_newer_snapshot(tmp_path):
    snapshot_dir = tmp_path
    logger = logging.getLogger("tests.stage3_recovery")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())

    valid_state = {
        "words": [[1, 2], [3, 4]],
        "freqs": [10, 5],
        "id_to_token_bytes": [bytes([i]) for i in range(256)],
        "merge_pairs": [(1, 2)],
        "last_merge": 1,
        "config_hash": "cfg",
        "pattern_hash": "pat",
    }
    valid_path = snapshot_dir / "state.m00000001.pkl"
    atomic_dump_pickle_with_checksum(valid_path, valid_state)

    bad_path = snapshot_dir / "state.m00000002.pkl"
    bad_path.write_bytes(b"not a pickle payload")
    bad_path.with_suffix(".pkl.sha256").write_text("wrong\n", encoding="utf-8")

    loaded = load_latest_snapshot(snapshot_dir, "cfg", "pat", logger)
    assert loaded is not None
    assert loaded["last_merge"] == 1
