"""Mini NPU Simulator — Python 3.8+, standard library only."""
import argparse
import json
import math
import re
import time
from pathlib import Path

EPSILON = 1e-9


def normalize_label(value):
    if isinstance(value, str):
        label = {"+": "Cross", "cross": "Cross", "x": "X"}.get(value.strip().lower())
        if label:
            return label
    raise ValueError("지원하지 않는 라벨: {!r}".format(value))


def validate_matrix(value, size):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("행 수 오류: {}행 필요".format(size))
    result = []
    for row in value:
        if not isinstance(row, list) or len(row) != size:
            raise ValueError("열 수 오류: 각 행에 {}개 필요".format(size))
        converted = []
        for number in row:
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                raise ValueError("배열에는 숫자만 사용할 수 있습니다")
            try:
                number = float(number)
            except OverflowError:
                raise ValueError("표현 범위를 초과한 숫자") from None
            if not math.isfinite(number):
                raise ValueError("NaN/무한대는 사용할 수 없습니다")
            converted.append(number)
        result.append(converted)
    return result


def mac(pattern, kernel):
    """Validated square matrices: one multiplication and accumulation per cell."""
    total = 0.0
    for i in range(len(pattern)):
        for j in range(len(pattern)):
            total += pattern[i][j] * kernel[i][j]
    if not math.isfinite(total):
        raise ValueError("MAC 결과가 유한하지 않습니다: 숫자 범위를 줄이세요")
    return total


def decide(score_a, score_b, labels=("Cross", "X")):
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return labels[0] if score_a > score_b else labels[1]


def generate_patterns(size):
    if not isinstance(size, int) or isinstance(size, bool) or size < 3 or size % 2 == 0:
        raise ValueError("크기는 3 이상의 홀수여야 합니다")
    cross = [[float(i == size // 2 or j == size // 2) for j in range(size)]
             for i in range(size)]
    diagonal = [[float(i == j or i + j == size - 1) for j in range(size)]
                for i in range(size)]
    return cross, diagonal


def benchmark(pattern, kernel, repeats=100):
    if repeats < 10:
        raise ValueError("측정 반복 횟수는 10 이상이어야 합니다")
    mac(pattern, kernel)  # warm-up, excluded from timing
    started = time.perf_counter_ns()
    for _ in range(repeats):
        mac(pattern, kernel)
    return (time.perf_counter_ns() - started) / repeats / 1_000_000


def performance(sizes=(3, 5, 13, 25), repeats=100, examples=None):
    print("\n[성능 분석] 단일 필터 MAC, 평균/{}회 (I/O 제외)".format(repeats))
    print("크기       평균 시간(ms)    연산 횟수(N²)")
    for size in sizes:
        pattern, kernel = (examples or {}).get(size, generate_patterns(size))
        try:
            elapsed = benchmark(pattern, kernel, repeats)
            print("{}x{}       {:.6f}          {}".format(size, size, elapsed, size * size))
        except ValueError as exc:
            print("{}x{} 측정 실패: {}".format(size, size, exc))


def read_matrix(name, size=3):
    print("\n{} ({}줄, 각 줄에 숫자 {}개)".format(name, size, size))
    matrix = []
    while len(matrix) < size:
        try:
            line = input("{}행: ".format(len(matrix) + 1))
            if not line.strip():
                print("행 수 오류: {}행 중 {}행을 입력했습니다. {}행을 입력하세요.".format(
                    size, len(matrix), len(matrix) + 1))
                continue
            row = [float(item) for item in line.split()]
            if len(row) != size or not all(math.isfinite(x) for x in row):
                raise ValueError()
        except ValueError:
            print("입력 형식 오류: 각 줄에 {}개의 유한한 숫자를 공백으로 구분해 입력하세요.".format(size))
            continue
        matrix.append(row)
    return matrix


def manual_mode(repeats=100):
    a = read_matrix("필터 A")
    b = read_matrix("필터 B")
    print("필터 A, B 저장 완료")
    while True:
        pattern = read_matrix("패턴")
        try:
            score_a, score_b = mac(pattern, a), mac(pattern, b)
        except ValueError as exc:
            print("{}: 패턴을 다시 입력하세요.".format(exc))
            continue
        break
    print("\nA 점수: {:.17g}\nB 점수: {:.17g}".format(score_a, score_b))
    verdict = decide(score_a, score_b, ("A", "B"))
    print("판정: {}".format("UNDECIDED (판정 불가)" if verdict == "UNDECIDED" else verdict))
    performance((3,), repeats, {3: (pattern, a)})


def load_filters(raw, size):
    if not isinstance(raw, dict):
        raise ValueError("필터 그룹은 객체여야 합니다")
    filters = {}
    for label, matrix in raw.items():
        normalized = normalize_label(label)
        if normalized in filters:
            raise ValueError("정규화 후 필터 라벨 중복: " + normalized)
        filters[normalized] = validate_matrix(matrix, size)
    if set(filters) != {"Cross", "X"}:
        raise ValueError("Cross와 X 필터가 모두 필요합니다")
    return filters


def analyze(data):
    if not isinstance(data, dict):
        raise ValueError("JSON 최상위는 객체여야 합니다")
    raw_filters, patterns = data.get("filters"), data.get("patterns")
    if not isinstance(raw_filters, dict) or not isinstance(patterns, dict):
        raise ValueError("filters와 patterns는 객체여야 합니다")
    print("\n[필터 로드]")
    filters, errors = {}, {}
    for key, raw in raw_filters.items():
        try:
            match = re.fullmatch(r"size_([1-9][0-9]*)", key)
            if not match:
                raise ValueError("필터 키 형식 오류")
            size = int(match.group(1))
            filters[key] = load_filters(raw, size)
            print("{} 로드 완료 (Cross, X)".format(key))
        except ValueError as exc:
            errors[key] = str(exc)
            print("{} 로드 실패: {}".format(key, exc))
    print("\n[패턴 분석]")
    results = []
    for key, case in patterns.items():
        result = {"id": key, "passed": False}
        print("--- {} ---".format(key))
        try:
            match = re.fullmatch(r"size_([1-9][0-9]*)_([0-9]+)", key)
            if not match:
                raise ValueError("패턴 키 형식 오류: size_{N}_{idx} 필요")
            size = int(match.group(1))
            filter_key = "size_{}".format(size)
            if filter_key not in filters:
                raise ValueError(errors.get(filter_key, "해당 크기의 필터가 없습니다"))
            if not isinstance(case, dict) or "input" not in case or "expected" not in case:
                raise ValueError("input과 expected가 필요합니다")
            pattern = validate_matrix(case["input"], size)
            expected = normalize_label(case["expected"])
            a = mac(pattern, filters[filter_key]["Cross"])
            b = mac(pattern, filters[filter_key]["X"])
            verdict = decide(a, b)
            result.update(passed=verdict == expected, verdict=verdict, expected=expected)
            print("Cross 점수: {:.17g} | X 점수: {:.17g}".format(a, b))
            print("판정: {} | expected: {} | {}".format(verdict, expected, "PASS" if result["passed"] else "FAIL"))
            if not result["passed"]:
                result["reason"] = ("동점: |Cross-X| < 1e-9" if verdict == "UNDECIDED"
                                    else "예상 라벨과 판정 불일치")
        except (ValueError, OverflowError) as exc:
            result["reason"] = "데이터/연산 오류: " + str(exc)
            print("FAIL: " + result["reason"])
        results.append(result)
    return results


def json_mode(path, repeats=100):
    with Path(path).open(encoding="utf-8-sig") as stream:
        data = json.load(stream)
    results = analyze(data)
    performance(repeats=repeats)
    passed = sum(result["passed"] for result in results)
    print("\n[결과 요약]\n총 테스트: {}개 | 통과: {}개 | 실패: {}개".format(len(results), passed, len(results) - passed))
    for result in results:
        if not result["passed"]:
            print("- {}: {}".format(result["id"], result["reason"]))
    if not results:
        print("주의: 분석할 패턴이 없습니다. 데이터 구성을 확인하세요.")
    return results


def main():
    parser = argparse.ArgumentParser(description="Mini NPU Simulator")
    parser.add_argument("--mode", choices=("1", "2"))
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("data.json"))
    parser.add_argument("--repeats", type=int, default=100)
    args = parser.parse_args()
    if args.repeats < 10:
        parser.error("--repeats는 10 이상이어야 합니다")
    print("=== Mini NPU Simulator ===")
    try:
        mode = args.mode
        while mode not in ("1", "2"):
            print("1. 사용자 입력 (3x3)\n2. data.json 분석")
            mode = input("선택: ").strip()
            if mode not in ("1", "2"):
                print("1 또는 2를 입력하세요.")
        if mode == "1":
            manual_mode(args.repeats)
        else:
            json_mode(args.data, args.repeats)
    except (EOFError, KeyboardInterrupt):
        print("\n입력이 종료되어 프로그램을 마칩니다.")
    except (OSError, ValueError, RecursionError) as exc:
        print("실행 오류: {}".format(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
