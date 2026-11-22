"""Generate clearly identified demonstration data; does not replace course data."""
import json
from pathlib import Path

from main import generate_patterns


def build_data():
    data = {"description": "과제 원본이 아닌 자체 생성 샘플. 정상 6개, 의도적 실패 3개.",
            "filters": {}, "patterns": {}}
    for size in (5, 13, 25):
        cross, diagonal = generate_patterns(size)
        data["filters"]["size_{}".format(size)] = {"cross": cross, "x": diagonal}
        data["patterns"]["size_{}_1".format(size)] = {"input": cross, "expected": "+"}
        data["patterns"]["size_{}_2".format(size)] = {"input": diagonal, "expected": "x"}
    near_tie = [[0.0] * 13 for _ in range(13)]
    near_tie[6][6] = 0.9
    near_tie[6][0] = 1e-10
    data["patterns"]["size_13_3"] = {"input": near_tie, "expected": "x"}
    data["patterns"]["size_5_3"] = {"input": [[0.0] * 5 for _ in range(4)], "expected": "+"}
    data["patterns"]["size_25_3"] = {"input": generate_patterns(25)[0], "expected": "unknown"}
    return data


if __name__ == "__main__":
    path = Path(__file__).with_name("data.json")
    if path.exists():
        raise SystemExit("data.json이 이미 존재합니다. 원본 보존을 위해 생성을 중단합니다.")
    path.write_text(json.dumps(build_data(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
