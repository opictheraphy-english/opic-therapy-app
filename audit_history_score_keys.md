# 검사 2 — 학습기록 점수 막대 키 불일치

**일시:** 2026-06-04  
**대상:** `views/history.py` `_render_score_breakdown` vs 각 practice 파이프라인이 저장하는 `score_breakdown`  
**코드 수정:** 없음 (조사·제안만)

---

## 1. 축 정의 비교

### 학습기록 UI가 기대하는 키 (`views/history.py`)

```python
_SCORE_AXES = (
    ("fluency", "유창성"),
    ("delivery", "전달력"),
    ("grammar", "문법"),
    ("vocabulary", "어휘"),
    ("coherence", "일관성"),
    ("response_amount", "답변량"),
)
```

`_render_score_breakdown()`은 위 6키만 순회. 매칭 키가 없거나 값이 없으면 해당 축 생략 → **rows가 비면 섹션 자체를 렌더하지 않음** (빈 막대 UI 없이 “항목별 점수” 블록 미표시).

### 저장 측 헤더 점수 (`utils/history_sync.py`)

`_avg_score()`도 **동일 6키**만 평균 → producer 키와 불일치 시 `score` 헤더도 `null`에 가깝게 저장됨.

---

## 2. Producer별 실제 키

| practice_type | subtype | 저장 함수 | score_breakdown 키 (개수) | history 6축과 겹치는 키 |
|---------------|---------|-----------|-------------------------|-------------------------|
| `mock_exam` | `mock_v2` | `save_mock_v2_report` | response_amount, relevance, structure, grammar, vocabulary, naturalness (**6**) | grammar, vocabulary, response_amount (**3**) |
| `mock_exam` | `real_mock` | `save_real_mock_report` | 동일 6축 (`shared_score_breakdown` → content.score_breakdown) | grammar, vocabulary, response_amount (**3**) |
| `script_coaching` | `diagnose` | `save_script_diagnose` | response_amount, vocabulary, grammar, context, structure (**5**) | grammar, vocabulary, response_amount (**3**) |
| `script_coaching` | `upgrade` | `save_script_upgrade` | **없음** (`score=None`) | — |
| `topic_practice` | `topic_practice` | `save_topic_report` | **필드 없음** (`build_topic_v2_history_payload`) | — |
| mini mock V2 | (history 미연동) | — | 6축 mock 키 (`mini_mock_v2_analysis`) | 학습기록 저장 없음 |

**참고:** 각 practice **화면**은 자체 `_SCORE_LABELS` / `SHARED_SCORE_AXES`로 5~6축을 올바르게 표시함. 불일치는 **학습기록 상세**(`history.py`)에만 국한.

---

## 3. practice_type별 학습기록 점수 막대 동작

| practice_type | subtype | 막대 UI 결과 | 원인 |
|---------------|---------|--------------|------|
| `topic_practice` | `topic_practice` | **섹션 없음** | content에 `score_breakdown` 자체가 없음 |
| `script_coaching` | `upgrade` | **섹션 없음** | breakdown 미저장, score=null |
| `script_coaching` | `diagnose` | **3개만 표시** (문법·어휘·답변량) | context/structure는 history 축에 없음; fluency/delivery/coherence는 producer에 없음 |
| `mock_exam` | `mock_v2` | **3개만 표시** | relevance/structure/naturalness 미매핑; fluency/delivery/coherence 미생성 |
| `mock_exam` | `real_mock` | **3개만 표시** | mock_v2와 동일 |
| (가상) breakdown `{}` 또는 legacy 6축만 있는 구형 레코드 | — | **섹션 없음** | 6축 중 유효 값 0개 |

“완전 빈 화면”은 **topic / script upgrade / breakdown 부재** 케이스. mock·diagnose는 **부분 막대(3/6)** — 사용자 입장에선 “점수가 거의 안 나온다”로 느껴질 수 있음.

---

## 4. 키 매핑 상세 (어긋남 표)

### History ← Mock V2 / Real Mock / Mini Mock (6축 producer)

| Producer 키 | History 축 | 학습기록 막대 |
|-------------|------------|---------------|
| response_amount | response_amount | ✅ 표시 |
| grammar | grammar | ✅ 표시 |
| vocabulary | vocabulary | ✅ 표시 |
| relevance | *(없음)* | ❌ 무시 |
| structure | *(없음)* | ❌ 무시 |
| naturalness | *(없음)* | ❌ 무시 |
| *(없음)* | fluency | ❌ 빈 축 |
| *(없음)* | delivery | ❌ 빈 축 |
| *(없음)* | coherence | ❌ 빈 축 |

### History ← Script Coaching Diagnose (5축 producer)

| Producer 키 | History 축 | 학습기록 막대 |
|-------------|------------|---------------|
| response_amount | response_amount | ✅ |
| vocabulary | vocabulary | ✅ |
| grammar | grammar | ✅ |
| context | *(없음)* | ❌ 무시 |
| structure | *(없음)* | ❌ 무시 |
| *(없음)* | fluency / delivery / coherence | ❌ 빈 축 |

---

## 5. 수정 방안 제안 (적용 안 함)

### A. 단기 — history 전용 매핑 dict (권장)

`views/history.py` (또는 `utils/history_score_map.py`)에 producer → display 축 매핑:

```python
_MOCK_TO_HISTORY = {
    "response_amount": "response_amount",
    "relevance": "coherence",      # 또는 별도 라벨 "질문 적합도"
    "structure": "coherence",       # 중복 시 가중 평균 또는 structure 전용 라벨 추가
    "grammar": "grammar",
    "vocabulary": "vocabulary",
    "naturalness": "fluency",     # 또는 "delivery"
}

_SCRIPT_DIAG_TO_HISTORY = {
    "response_amount": "response_amount",
    "vocabulary": "vocabulary",
    "grammar": "grammar",
    "context": "coherence",
    "structure": "delivery",
}
```

`_render_score_breakdown()` 진입 시 `practice_type`/`subtype`으로 매핑 적용 후 `_SCORE_AXES` 또는 **동적 라벨 테이블**로 렌더.

### B. 중기 — 표시 축을 `SHARED_SCORE_AXES`에 통일

`services/mini_mock_v2_level_rules.py`의 `SHARED_SCORE_AXES`(6키)를 **단일 소스**로:

- mock / mini mock / real_mock producer 키 유지
- `history.py`의 `_SCORE_AXES`를 `SHARED_SCORE_AXES` + 한글 라벨 dict로 교체
- script coaching은 5축 전용 `_SCRIPT_SCORE_LABELS` 유지 (이미 `script_coaching.py`에 존재)

### C. `_avg_score()` 동기화

`history_sync._SCORE_AXES`를 producer-aware 평균으로 변경하거나, 저장 시 **정규화된 breakdown**을 content에 함께 넣기 (`score_breakdown_display`).

### D. topic_practice

점수 막대가 필요하면 `build_topic_v2_history_payload`에 mini report 축 추가 또는 “점수 없음” 안내 문구를 history UI에 명시.

---

## 6. 관련 파일

| 파일 | 역할 |
|------|------|
| `views/history.py` | `_SCORE_AXES`, `_render_score_breakdown`, `_axis_value` |
| `utils/history_sync.py` | `_avg_score`, `save_*` |
| `services/mock_v2_analysis.py` | mock 6축 `_SCORE_KEYS` |
| `services/mini_mock_v2_analysis.py` | mini mock 6축 (동일) |
| `services/script_coaching_diagnose_analysis.py` | diagnose 5축 |
| `views/script_coaching.py` | `_SCORE_LABELS` (화면은 정상) |
| `views/mock_v2.py` | `_SCORE_LABELS` (화면은 정상) |
