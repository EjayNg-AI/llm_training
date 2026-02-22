"""Special-token helpers for runtime usage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialTokenIds:
    bos: int | None
    eos: int | None
    pad: int | None
    unk: int | None


def resolve_special_token_ids(vocab: dict[str, int], mapping: dict[str, str]) -> SpecialTokenIds:
    def _id(key: str) -> int | None:
        token = mapping.get(key)
        if token is None:
            return None
        return vocab.get(token)

    return SpecialTokenIds(
        bos=_id("bos_token"),
        eos=_id("eos_token"),
        pad=_id("pad_token"),
        unk=_id("unk_token"),
    )
