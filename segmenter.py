from dataclasses import dataclass
from pathlib import Path
import json



@dataclass(frozen=True)
class Delimiters:
    element_sep: str  #e.g. "*"
    segment_sep: str  #e.g. "~"


def detect_delimiters(raw_text: str) -> Delimiters:
    delimiters = Delimiters(raw_text[3], raw_text[105])
    return delimiters


def split_segments(raw_text: str, delimiters: Delimiters) -> list[str]:
    raw_string = raw_text.replace("\n", "").replace("\r", "")
    text = raw_string.split(delimiters.segment_sep)
    #print(text)
    return text


def tokenize_segments(segment: list[str], delimiters: Delimiters) -> list[list[str]]:
    elements = [segment.split(delimiters.element_sep) for segment in segment]
    #
    return elements


def parse_member_loops(segments: list[list[str]]) -> dict:
    header = {}
    members = []
    current = None

    for seg in segments:
        seg_id = seg[0]
        print(seg)

        if seg_id == "INS":
            if current:
                members.append(current)  # flush previous
            current = {"ins": seg,
                       "refs": [],
                       "dtps": [],
                       "hd": None,
                       "nm1": None,
                       "dmg": None,
                       "n3": None,
                       "n4": None,
                       "per": None,
                       "amt": None}

        elif current is None:
            # still in header territory
            header.setdefault(seg_id, []).append(seg)

        elif seg_id == "REF":
            current["refs"].append(seg)

        elif seg_id == "DTP":
            current["dtps"].append(seg)

        elif seg_id in ("NM1", "HD", "DMG", "N3", "N4", "PER", "AMT"):
            current[seg_id.lower()] = seg

    if current:
        members.append(current)  # flush last member

    return {"header": header, "members": members}


if __name__ == '__main__':
    filepath = 'Sample_Files/test 834.txt'
    raw_text = Path(filepath).read_text()
    delimiters = detect_delimiters(raw_text)
    segments = split_segments(raw_text, delimiters)
    elements = tokenize_segments(segments, delimiters)
    members = parse_member_loops(elements)
    json_string = json.dumps(members, indent=4)
    print(json_string)



