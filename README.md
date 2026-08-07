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

## Citation

[LLM-Enabled Low-Altitude UAV Natural Language Navigation via Signal Temporal Logic Specification Translation and Repair](https://ieeexplore.ieee.org/document/11627954)

```bibtex
@article{ping2026llm,
  title={LLM-Enabled Low-Altitude UAV Natural Language Navigation via Signal Temporal Logic Specification Translation and Repair},
  author={Ping, Yuqi and Ding, Huahao and Liang, Tianhao and Zhou, Longyu and Lei, Guangyu and Chen, Xinglin and Wu, Junwei and Zhou, Jieyu and Zhang, Tingting},
  journal={IEEE Transactions on Cognitive Communications and Networking},
  year={2026},
  publisher={IEEE},
  url={https://ieeexplore.ieee.org/document/11627954}
}
```
