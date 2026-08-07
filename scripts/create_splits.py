#!/usr/bin/env python3
"""Create deterministic, formula-grouped UAV-NL2STL data splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {"id", "sentence", "stl"}
SPLIT_SALT = b"uav-nl2stl-v1\0"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class STLParseError(ValueError):
    """Raised when an STL expression does not match the dataset grammar."""


class STLParser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def parse(self) -> tuple[Any, ...]:
        node = self._parse_or()
        self._skip_space()
        if self.pos != len(self.text):
            raise self._error("unexpected trailing input")
        return self._normalize(node)

    def _parse_or(self) -> tuple[Any, ...]:
        children = [self._parse_and()]
        while self._take("|"):
            children.append(self._parse_and())
        return children[0] if len(children) == 1 else ("or", *children)

    def _parse_and(self) -> tuple[Any, ...]:
        children = [self._parse_until()]
        while self._take("&"):
            children.append(self._parse_until())
        return children[0] if len(children) == 1 else ("and", *children)

    def _parse_until(self) -> tuple[Any, ...]:
        node = self._parse_unary()
        while self._peek_temporal("U"):
            self.pos += 1
            lower, upper = self._parse_interval()
            node = ("until", lower, upper, node, self._parse_unary())
        return node

    def _parse_unary(self) -> tuple[Any, ...]:
        self._skip_space()
        if self._take("~"):
            return ("not", self._parse_unary())
        for operator in ("F", "G"):
            if self._peek_temporal(operator):
                self.pos += 1
                lower, upper = self._parse_interval()
                return (operator.lower(), lower, upper, self._parse_unary())
        if self._take("("):
            node = self._parse_or()
            if not self._take(")"):
                raise self._error("missing closing parenthesis")
            return node
        return self._parse_atom()

    def _parse_atom(self) -> tuple[Any, ...]:
        self._skip_space()
        start = self.pos
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char in "&|()~":
                break
            if char == "U" and self._peek_temporal("U"):
                break
            self.pos += 1
        atom = re.sub(r"\s+", " ", self.text[start:self.pos].strip())
        if not atom:
            raise self._error("expected atomic proposition")
        return ("atom", atom)

    def _parse_interval(self) -> tuple[int | str, int | str]:
        if not self._take("["):
            raise self._error("expected interval")
        lower = self._parse_bound()
        self._skip_space()
        if self.pos >= len(self.text) or self.text[self.pos] not in ":,":
            raise self._error("expected ':' or ',' between interval bounds")
        self.pos += 1
        upper = self._parse_bound()
        if not self._take("]"):
            raise self._error("missing closing interval bracket")
        if isinstance(lower, int) and isinstance(upper, int) and lower > upper:
            raise self._error("interval lower bound exceeds upper bound")
        return lower, upper

    def _parse_bound(self) -> int | str:
        self._skip_space()
        match = re.match(r"(?:\d+|inf(?:inite)?)", self.text[self.pos :], re.I)
        if not match:
            raise self._error("invalid interval bound")
        token = match.group(0)
        self.pos += len(token)
        return "infinite" if token.lower().startswith("inf") else int(token)

    def _peek_temporal(self, operator: str) -> bool:
        self._skip_space()
        if self.pos >= len(self.text) or self.text[self.pos] != operator:
            return False
        lookahead = self.pos + 1
        while lookahead < len(self.text) and self.text[lookahead].isspace():
            lookahead += 1
        return lookahead < len(self.text) and self.text[lookahead] == "["

    def _take(self, token: str) -> bool:
        self._skip_space()
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def _skip_space(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def _error(self, message: str) -> STLParseError:
        return STLParseError(f"{message} at column {self.pos + 1}: {self.text!r}")

    def _normalize(self, node: tuple[Any, ...]) -> tuple[Any, ...]:
        kind = node[0]
        if kind in {"and", "or"}:
            children: list[tuple[Any, ...]] = []
            for child in node[1:]:
                normalized = self._normalize(child)
                if normalized[0] == kind:
                    children.extend(normalized[1:])
                else:
                    children.append(normalized)
            children.sort(key=serialize_ast)
            return (kind, *children)
        if kind == "not":
            return (kind, self._normalize(node[1]))
        if kind in {"f", "g"}:
            return (kind, node[1], node[2], self._normalize(node[3]))
        if kind == "until":
            return (
                kind,
                node[1],
                node[2],
                self._normalize(node[3]),
                self._normalize(node[4]),
            )
        return node


def serialize_ast(node: tuple[Any, ...]) -> str:
    return json.dumps(node, ensure_ascii=False, separators=(",", ":"))


def canonicalize_stl(formula: str) -> str:
    return serialize_ast(STLParser(formula).parse())


def split_for(canonical_stl: str) -> str:
    digest = hashlib.sha256(SPLIT_SALT + canonical_stl.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10
    if bucket < 8:
        return "train"
    return "validation" if bucket == 8 else "test"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_records(path: Path) -> list[dict[str, Any]]:
    if path.read_bytes().startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"UTF-8 BOM is not allowed: {path}")
    records: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"blank line at {path}:{line_number}")
            record = json.loads(line)
            if not isinstance(record, dict) or set(record) != REQUIRED_FIELDS:
                raise ValueError(f"invalid fields at {path}:{line_number}")
            if not isinstance(record["id"], int) or record["id"] in seen_ids:
                raise ValueError(f"invalid or duplicate id at {path}:{line_number}")
            if not all(isinstance(record[key], str) and record[key].strip() for key in ("sentence", "stl")):
                raise ValueError(f"empty sentence or STL at {path}:{line_number}")
            canonicalize_stl(record["stl"])
            seen_ids.add(record["id"])
            records.append(record)
    return sorted(records, key=lambda item: item["id"])


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, default=REPOSITORY_ROOT / "data")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPOSITORY_ROOT / "metadata" / "split_manifest.json",
    )
    args = parser.parse_args()

    args.source = args.source.resolve()
    args.output_dir = args.output_dir.resolve()
    args.manifest = args.manifest.resolve()

    records = read_records(args.source)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[canonicalize_stl(record["stl"])].append(record)

    splits: dict[str, list[dict[str, Any]]] = {name: [] for name in ("train", "validation", "test")}
    group_manifest: list[dict[str, Any]] = []
    for canonical_stl, group in sorted(grouped.items()):
        split = split_for(canonical_stl)
        splits[split].extend(group)
        group_manifest.append(
            {
                "canonical_stl_sha256": hashlib.sha256(canonical_stl.encode("utf-8")).hexdigest(),
                "count": len(group),
                "split": split,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    full_path = args.output_dir / "full.jsonl"
    shutil.copyfile(args.source, full_path)
    for name, split_records in splits.items():
        split_records.sort(key=lambda item: item["id"])
        write_jsonl(args.output_dir / f"{name}.jsonl", split_records)

    files = [full_path, *(args.output_dir / f"{name}.jsonl" for name in splits)]
    manifest = {
        "format_version": 1,
        "source_sha256": sha256_file(args.source),
        "split_algorithm": "sha256 first 64 bits modulo 10",
        "split_salt": SPLIT_SALT.rstrip(b"\0").decode("ascii"),
        "canonicalization": "parsed STL AST; flattened and sorted associative & and | nodes",
        "records": len(records),
        "unique_canonical_stl": len(grouped),
        "splits": {
            name: {
                "records": len(split_records),
                "canonical_stl_groups": sum(1 for group in group_manifest if group["split"] == name),
            }
            for name, split_records in splits.items()
        },
        "files": {
            path.relative_to(REPOSITORY_ROOT).as_posix(): sha256_file(path)
            for path in files
        },
        "groups": group_manifest,
    }
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    checksum_paths = [*files, args.manifest]
    checksum_lines = [
        f"{sha256_file(path)}  {path.relative_to(REPOSITORY_ROOT).as_posix()}"
        for path in checksum_paths
    ]
    (REPOSITORY_ROOT / "checksums.sha256").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8", newline="\n"
    )

    for name in splits:
        stats = manifest["splits"][name]
        print(f"{name}: {stats['records']} records, {stats['canonical_stl_groups']} formula groups")


if __name__ == "__main__":
    main()
