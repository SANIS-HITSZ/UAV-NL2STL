#!/usr/bin/env python3
"""Validate UAV-NL2STL records, grouped splits, and release checksums."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from create_splits import canonicalize_stl, read_records, sha256_file, split_for


ORDERING_PATTERN = re.compile(r"\b(?:before|after|prior)\b", re.I)


def contains_until(canonical_stl: str) -> bool:
    return '"until"' in canonical_stl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict-semantics", action="store_true")
    args = parser.parse_args()

    data_dir = args.root / "data"
    manifest_path = args.root / "metadata" / "split_manifest.json"
    full_records = read_records(data_dir / "full.jsonl")
    split_records = {
        name: read_records(data_dir / f"{name}.jsonl")
        for name in ("train", "validation", "test")
    }

    full_by_id = {record["id"]: record for record in full_records}
    split_by_id: dict[int, str] = {}
    groups: dict[str, set[str]] = defaultdict(set)
    for split, records in split_records.items():
        for record in records:
            if record["id"] in split_by_id:
                raise ValueError(f"id {record['id']} appears in multiple splits")
            if full_by_id.get(record["id"]) != record:
                raise ValueError(f"split record {record['id']} differs from full.jsonl")
            canonical = canonicalize_stl(record["stl"])
            if split_for(canonical) != split:
                raise ValueError(f"id {record['id']} is assigned to the wrong split")
            split_by_id[record["id"]] = split
            groups[canonical].add(split)

    if set(split_by_id) != set(full_by_id):
        raise ValueError("split ids do not exactly cover full.jsonl")
    leaked = [canonical for canonical, locations in groups.items() if len(locations) != 1]
    if leaked:
        raise ValueError(f"{len(leaked)} canonical STL groups cross split boundaries")

    ids = sorted(full_by_id)
    if ids != list(range(1, len(ids) + 1)):
        raise ValueError("full.jsonl ids must be contiguous from 1 to N")

    sentence_labels: dict[str, set[str]] = defaultdict(set)
    pairs: Counter[tuple[str, str]] = Counter()
    ordering_without_until = 0
    for record in full_records:
        sentence_labels[record["sentence"]].add(record["stl"])
        pairs[(record["sentence"], record["stl"])] += 1
        canonical = canonicalize_stl(record["stl"])
        if ORDERING_PATTERN.search(record["sentence"]) and not contains_until(canonical):
            ordering_without_until += 1

    conflicts = [sentence for sentence, labels in sentence_labels.items() if len(labels) > 1]
    if conflicts:
        raise ValueError(f"{len(conflicts)} sentences have conflicting STL labels")

    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["records"] != len(full_records):
        raise ValueError("manifest record count is stale")
    if manifest["unique_canonical_stl"] != len(groups):
        raise ValueError("manifest canonical STL count is stale")
    for split, records in split_records.items():
        if manifest["splits"][split]["records"] != len(records):
            raise ValueError(f"manifest {split} record count is stale")
    for relative_path, expected in manifest["files"].items():
        actual = sha256_file(args.root / relative_path)
        if actual != expected:
            raise ValueError(f"checksum mismatch: {relative_path}")

    checksum_path = args.root / "checksums.sha256"
    for line_number, line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"invalid checksum line {line_number}")
        expected, relative_path = parts
        actual = sha256_file(args.root / relative_path)
        if actual != expected:
            raise ValueError(f"release checksum mismatch: {relative_path}")

    duplicate_pairs = sum(count - 1 for count in pairs.values() if count > 1)
    print(f"records: {len(full_records)}")
    print(f"unique canonical STL: {len(groups)}")
    print(f"duplicate (sentence, STL) records: {duplicate_pairs}")
    for name, records in split_records.items():
        print(f"{name}: {len(records)}")
    print(f"warning: ordering language without U encoding: {ordering_without_until}")
    if args.strict_semantics and ordering_without_until:
        raise ValueError("ordering-language warnings fail strict semantic validation")
    print("structural validation passed")


if __name__ == "__main__":
    main()
