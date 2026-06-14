# 검사 4 — 미사용/깨진 import·죽은 코드 스캔

**일시:** 2026-06-04  
**범위:** `views/`, `services/`, `components/`  
**방법:** 정적 참조 grep, import 경로 존재 확인, `refs==1`(정의만 존재) 휴리스틱  
**원시 데이터:** `audit_dead_code_data.json`  
**코드 수정·삭제:** 없음

---

## 요약

| 항목 | 결과 |
|------|------|
| 깨진 import (경로 불일치) | **0건** |
| 구문 오류 | **0건** |
| 미사용 의심 private 함수 | **17건** (아래 상세) |
| **확실한 dead code** | **6건** |
| **확인 필요 (false positive 가능)** | **11건** |

---

## 확실 — 호출처 없음 (삭제 후보, 미적용)

| 파일 | 심볼 | 근거 |
|------|------|------|
| `views/topic_practice_v2.py` | `_get_topic_v2_audio_by_answer_id` | 정의만 존재. 실제 재생은 `_get_topic_v2_audio_blob` 사용 (L1604, L2477) |
| `views/topic_practice_v2.py` | `_practice_screen_title` | 정의만, 호출 0 |
| `views/topic_practice_v2.py` | `_render_topic_v2_attempt_caption` | 정의만, 호출 0 |
| `views/topic_practice_v2.py` | `_topic_v2_mic_key` | 정의만, 호출 0 |
| `services/feedback/feedback_builder.py` | `_expression_upgrades_from_hits` | 정의만. 표현 업그레이드는 `merge_expression_upgrades_for_display` / `extract_expression_upgrades` 경로 |
| `services/feedback/topic_mini_report_analysis.py` | `_path_one_call_audio_batch` | 정의만, 호출 0 |
| `services/evaluation/gemini_multimodal_pipeline.py` | `_list_available_models` | 정의만, 호출 0 |

---

## 확인 필요 — mock_exam.py 대형 dead 블록 의심

아래 함수들은 `views/mock_exam.py` 내 **정의만 있고 파일 내·외 호출 grep 0**. 리팩터링 잔재로 보이나, 동적 호출·미커밋 분기 가능성 있어 **수동 확인 후** 제거 권장.

| 심볼 | 줄 | 추정 원래 역할 |
|------|-----|----------------|
| `_is_topic_practice` | 752 | topic vs mock 분기 (`history._is_topic_practice_record`와 별개) |
| `_render_coaching_flow` | 2218 | 코칭 플로우 UI |
| `_needs_mode_selection` | 2456 | 모드 선택 게이트 |
| `_topic_sync_audio_to_mx` | 2922 | topic 오디오 session sync |
| `_render_detailed_coaching_for_result` | 2979 | 결과별 상세 코칭 |
| `_render_topic_api_delay_recovery_card` | 3119 | API 지연 복구 카드 |
| `_mini_mock_sync_audio_to_mx` | 4744 | mini mock 오디오 sync |
| `_render_mock_question_listen_stage` | 6118 | listen 스테이지 렌더 |
| `_render_real_mock_error_fallback` | 659 | real mock 오류 fallback |

**주의:** `mock_exam.py`는 8700+ 줄 — 과거 플로우가 새 mini_mock_v2 / topic_practice_v2로 이전되며 호출 체인이 끊긴 것으로 추정.

---

## 확인 필요 — false positive

| 파일 | 심볼 | 실제 상태 |
|------|------|-----------|
| `components/navigation.py` | `_href_key` | **사용 중** — `components/topbar.py`, `navigation.py` 내부에서 import·호출. 스캔 refs=1 오탐 |

---

## 깨진 import

**없음.** `views/`·`services/`·`components/` Python 파일 대상 상대/절대 import 경로 존재 여부 확인 — unresolved 0.

---

## 도달 불가 분기

정적 분석만으로 “확실한” unreachable branch는 별도 IR 분석 없이는 미보고. mock_exam dead 함수와 연결된 `if False` / legacy page 분기는 **확인 필요**로 남김.

---

## 권장 후속 (적용 안 함)

1. **확실 7건** — IDE “Find References” 후 unused import/함수 제거 PR (topic_practice_v2 4 + feedback 2 + gemini 1).
2. **mock_exam 9건** — git history로 마지막 호출 커밋 확인 → dead module 분리 또는 삭제.
3. CI — `vulture` / `ruff F401` 으로 회귀 방지 (선택).

---

## 스캔 한계

- Streamlit `st.session_state` 키 기반 간접 호출 미탐지
- 문자열 `getattr` / 동적 import 미탐지
- 테스트 전용 import 경로 일부 제외 가능

**애매한 항목은 “확인 필요”로만 표기했으며, 확실한 dead code만 삭제 후보로 분류함.**
