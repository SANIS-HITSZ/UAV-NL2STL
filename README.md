# UAV-NL2STL

UAV-NL2STL is a navigation-oriented dataset of English natural-language instructions paired with bounded Signal Temporal Logic (STL) specifications.

## Dataset contents

The source collection contains 23,000 JSON Lines records. Every record has three fields:

```json
{"id":1,"sentence":"...","stl":"..."}
```

- `id`: unique integer identifier.
- `sentence`: an English UAV navigation instruction.
- `stl`: the corresponding STL specification in the documented ASCII syntax.

The original source file contains 16,784 distinct STL strings and 15,408 distinct canonical STL syntax trees after associative `&` and `|` normalization. All 23,000 lines are valid JSON, all identifiers are unique and contiguous, and no fields are missing or empty.

## Files and splits

| File | Purpose |
| --- | --- |
| `data/full.jsonl` | Byte-for-byte copy of the source collection |
| `data/train.jsonl` | Deterministic training split |
| `data/validation.jsonl` | Deterministic validation split |
| `data/test.jsonl` | Deterministic test split |
| `metadata/split_manifest.json` | Split algorithm, counts, group assignments, and checksums |

Splits are assigned by a salted SHA-256 hash of a canonical parsed STL syntax tree. Associative conjunction and disjunction nodes are flattened and sorted before hashing. Consequently, records with the same canonical STL cannot cross split boundaries.

| Split | Records | Canonical STL groups |
| --- | ---: | ---: |
| Train | 18,537 | 12,363 |
| Validation | 2,171 | 1,478 |
| Test | 2,292 | 1,567 |

Run the release checks with Python 3.10 or newer; no third-party packages are required:

```bash
python scripts/validate_dataset.py
```

The STL syntax is described in [`docs/STL_GRAMMAR.md`](docs/STL_GRAMMAR.md).

## Known limitations

- The language and formulas are synthetic and highly template-structured.
- Some natural-language instructions use ordering expressions such as `before`, while their labels encode only a conjunction of bounded eventualities. Such labels do not enforce ordering under standard STL semantics and require further semantic audit.
- The source includes 367 additional records whose `(sentence, stl)` pair duplicates another record. They are retained to preserve the released source collection.
- Atomic-proposition capitalization is not fully normalized; for example, some records use `Black chair`.
- The dataset does not currently include scene, template, or task-family metadata.
- This research dataset is not validated for direct use in real-world flight or other safety-critical control systems.

## Source and license

UAV-NL2STL was constructed by the authors for navigation-oriented NL-to-STL research. The dataset and repository contents are released under the [Creative Commons Attribution 4.0 International License](LICENSE). Reusers must provide attribution, link to the license, and indicate whether changes were made.

Citation metadata is provided in [`CITATION.cff`](CITATION.cff).

## Associated paper

Yuqi Ping, Huahao Ding, Tianhao Liang, Longyu Zhou, Guangyu Lei, Xinglin Chen, Junwei Wu, Jieyu Zhou, and Tingting Zhang, "LLM-Enabled Low-Altitude UAV Natural Language Navigation via Signal Temporal Logic Specification Translation and Repair."
