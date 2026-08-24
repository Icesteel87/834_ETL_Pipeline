from dataclasses import dataclass
from pathlib import Path



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
    return text


def tokenize_segments(segment: list[str], delimiters: Delimiters) -> list[list[str]]:
    elements = [segment.split(delimiters.element_sep) for segment in segment]
    return elements


if __name__ == '__main__':
    filepath = 'Sample_Files/test 834.txt'
    raw_text = Path(filepath).read_text()
    delimiters = detect_delimiters(raw_text)
    segments = split_segments(raw_text, delimiters)
    elements = tokenize_segments(segments, delimiters)
    for element in elements:
        print(element)
