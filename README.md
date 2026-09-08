# 834 ETL Pipeline

An ingestion pipeline for ANSI X12 **834 Benefit Enrollment and Maintenance**
files: raw EDI in, structured member records out, database entry as the
eventual target.

> **Status: early development.** The parser runs end to end on the two
> hand-built sample files, but it aborts on the seven vendor samples and
> silently drops data for members with more than one coverage. It is not ready
> to load a database. See [Known limitations](#known-limitations).

---

## Requirements

- Python 3.12+ (the code uses PEP 695 `type` statements)
- pandas

```bash
python -m venv .venv
.venv/Scripts/activate
pip install pandas
```

On macOS/Linux the activate line is `source .venv/bin/activate`.

There is no `requirements.txt` or packaging config yet.

## Quick start

The entry point is the `__main__` block in `segmenter.py`, which reads a
hardcoded `filepath` and prints the mapped result as JSON:

```bash
python segmenter.py
```

To parse a different file, edit `filepath` in [`segmenter.py`](segmenter.py)
(line 94). There is no CLI yet.

## How it works

The pipeline is five stages across two modules.

| # | Stage | Function | Module | What it does |
|---|-------|----------|--------|--------------|
| 1 | Detect delimiters | `detect_delimiters` | `segmenter.py` | Reads the element, sub-element and segment separators out of fixed byte offsets in the ISA segment |
| 2 | Split segments | `split_segments` | `segmenter.py` | Strips newlines, splits on the segment separator, drops empties |
| 3 | Tokenize | `tokenize_segments` | `segmenter.py` | Splits each segment on the element separator into a list of elements |
| 4 | Group member loops | `extract_members` | `segmenter.py` | Loads segments into a DataFrame and assigns a `member_seq_no` via a cumulative sum over `INS` segments, then groups by it. Group `0` is everything before the first `INS` (the file header); groups `1..n` are the 2000 member loops |
| 5 | Map to fields | `extract_elements` -> `map_member` | `segmenter.py` -> `mapper.py` | Dispatches each segment to a registered parser and merges every result into one flat dict per group |

### Segment parser registry

`mapper.py` uses a decorator registry rather than a chain of conditionals. Each
segment ID gets a function that turns a raw element list into a dict:

```python
@register_parser("N3")
def map_n3(segs: list[str]) -> dict:
    return {
        'Address_1': segs[1],
        'Address_2': segs[2],
    }
```

`map_member` looks each segment ID up in `parsers` and **raises `ValueError` if
no parser is registered**, so an unhandled segment aborts the whole file.

Currently registered: `AMT`, `BGN`, `DMG`, `DTP`, `GE`, `GS`, `HD`, `IEA`,
`INS`, `ISA`, `LX`, `N1`, `N3`, `N4`, `NM1`, `PER`, `QTY`, `REF`, `SE`, `ST`.
(`BGN`, `GE`, `GS`, `IEA`, `ISA`, `QTY` and `ST` are registered as stubs that
return `None`.)

### Code tables

X12 qualifier codes are translated to readable labels through module-level
dicts in `mapper.py`, all of which fall back to the raw code on a miss:

| Table | Covers |
|---|---|
| `RELATIONSHIP` | INS02 — self, spouse, child, ward |
| `MAINTENANCE` | INS03 — addition, change, termination |
| `GENDER` | DMG03 — male, female, unknown |
| `DTP_QUAL` | DTP01 date qualifiers (356, 357, 348, 349, 303, 336, 337) |
| `REF_QUALIFIER` | REF01 reference identification qualifiers (17 codes) |
| `PER_QUALIFIER` | PER03/PER05 contact number qualifiers (9 codes) |
| `HD03_QUALIFER` | HD03 insurance line codes (22 codes) |
| `HD05_QUALIFER` | HD05 coverage level codes (18 codes) |
| `AMT_QUALIFER` | AMT01 amount qualifiers (7 codes) |

### Output

One flat dict per group, keyed by group number:

```json
{
  "subscriber": "Y",
  "relationship_code": "self",
  "maintenance_type": "030",
  "member_id": "555000102",
  "group_policy_number": "100200",
  "employment_date": "20180312",
  "effective_date": "20180401",
  "last_name": "NGUYEN",
  "first_name": "MAI",
  "middle": "T",
  "ssn": "555000102",
  "Home Phone Number": "2085550102",
  "Address_1": "88 N EAGLE RD",
  "City": "MERIDIAN",
  "State": "ID",
  "Zip": "83642",
  "Birth Date": "09301979",
  "Gender": "F",
  "Marital_status": "M",
  "Coverage Type": "Dental",
  "Coverage Description": "IDDEN500",
  "Coverage Level Code": "Employee and Spouse",
  "coverage_begin": "20260101"
}
```

`MemberRecord` in `mapper.py` sketches the intended typed target schema
(current vs. prior name, INS detail codes, loop 2100A/2100B fields, dates as
`date` objects). It is not wired into the pipeline yet.

## Sample files

| File | Source | Parses today |
|---|---|---|
| `bci_834_cycle_n_baseline.edi` | Hand-built, Blue Cross of Idaho companion-guide shape | yes |
| `test 834.txt` | Hand-built | yes |
| `MCE834Sample_1/2/3.txt` | [eMedNY 5010 834 samples](https://www.emedny.org/hipaa/5010/transactions/834_sample_files/) | no |
| `834CGSample_ADD/CANCEL/TERM/UPDATE.txt` | CGS companion-guide samples | no |

## Known limitations

These are current, reproducible defects — not future features.

- **Unregistered segments abort the file.** All seven vendor samples fail with
  `ValueError: No parser for ...` on `LS`, `LE`, `LUI` or `COB`. Only the two
  hand-built files parse.
- **Repeated segments overwrite each other.** `map_member` merges every segment
  in a member loop into one dict with `.update()`, so the last write wins. A
  member with medical *and* dental coverage keeps only the dental `HD`; the
  header's three `N1` segments (employer, carrier, broker) collapse to one.
  This is silent — no error, just missing rows.
- **`map_n1` is off by one.** It reads `segs[3]` as `ETIN`, but that position
  holds the ID *qualifier* (`FI`); the identifier itself is `segs[4]`.
- **Output is not spec-valid JSON.** DataFrame padding of ragged segments
  leaves `NaN` floats in the result, so `json.dumps(..., allow_nan=False)`
  raises and strict consumers (Postgres `::json`, `JSON.parse`) reject it.
- **Dates are `MMDDYYYY` strings.** `map_dmg` reformats `CCYYMMDD` into
  `MMDDYYYY`, which is neither the source format nor a sortable one. Its
  `len(segs) > 3` guard also tests the wrong index for the birth date.
- **Code tables are bypassed in places.** `MAINTENANCE` and `GENDER` are
  defined but never applied — `map_ins` returns the raw INS03 code and
  `map_dmg` the raw DMG03.
- **Sub-element separator is detected but unused.** Composite elements are
  never split, so `HD` and `NM1` composites stay as single strings.
- **`extract_elements` writes `member_<n>.csv` to the repo root** as a side
  effect of every run. These are not gitignored and dirty the working tree.
- **Delimiter detection uses hardcoded byte offsets** (`raw_text[3]`, `[104]`,
  `[105]`). Correct for a byte-exact 106-character ISA, but a BOM or leading
  whitespace breaks it.
- **Dead code paths.** `parse_member_loops` and `map_information` in
  `segmenter.py` are the superseded pre-pandas implementation; `map_ISA` in
  `mapper.py` is unreferenced and 0-indexed as though the segment ID had been
  stripped.
- **No tests.** There is no test suite of any kind.

## Roadmap

1. Register the missing segments (`LS`, `LE`, `LUI`, `COB`) or make unknown
   segments a warning instead of a hard failure, so vendor files parse.
2. Restructure `map_member` so repeatable loops (`HD`, `REF`, `PER`, `N1`,
   `DTP`) collect into lists instead of flattening.
3. Normalize dates to ISO `YYYY-MM-DD` and coerce `NaN` to `None`.
4. Populate `MemberRecord` and make it the pipeline's return type.
5. Add a pytest suite asserting all nine sample files parse.
6. Add a CLI (input path, output path/format) in place of the hardcoded
   `filepath`.
7. Build the load stage — schema plus writer — to reach "database entry".

## License

GPL-3.0. See [LICENSE](LICENSE).
