# 미션 3 요구사항 대조표

| 요구사항 | 구현 및 검증 |
|---|---|
| 2차원 배열, 3/5/13/25 지원 | list, validate_matrix, generate_patterns |
| 3×3 A/B/패턴 순차 입력과 저장 확인 | read_matrix, manual_mode, manual-run.txt |
| 행/열 및 숫자 검증, 재입력 | test_reprompt, test_invalid_matrices |
| JSON 크기 키 기반 필터 선택 | analyze, test_schema_and_keys |
| 케이스 오류 격리, 원인 기록 | test_bad_case_continues, test_bad_filter_continues |
| 라벨 정규화 | normalize_label, test_normalization |
| 반복문 MAC, 외부 라이브러리 금지 | mac, test_mac_and_verdict |
| epsilon과 동점 판정 | decide, epsilon 경계 테스트 |
| 크기별 평균 시간 및 N² | performance, sample-run.txt |
| 최소 10회, I/O 제외 | benchmark, --repeats 최소값 검증 |
| 총/통과/실패 및 실패 목록 | json_mode, test_sample |
| README 10줄 이상 결과/복잡도 분석 | 결과 리포트 20개 항목 |
| 패턴 생성기 (선택) | generate_patterns, generate_data.py |
| 공식 데이터 검증 | 미제공 상태. 자체 샘플과 공식 데이터 구분 명시 |
