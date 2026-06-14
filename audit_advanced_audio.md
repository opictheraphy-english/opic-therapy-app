# 검사 1 — ADVANCED 오디오 전수 일치 검사

**일시:** 2026-06-04  
**대상:** `ADVANCED_SET_POOL` 20세트 × 2슬롯(comparison, news_issue) = **40 MP3**  
**오디오 경로:** `assets/question_audio/{set_id}_comparison.mp3`, `{set_id}_news_issue.mp3`  
**풀 정의:** `services/mock_exam/mock_exam_test_set_generator.py`  
**원시 데이터:** `audit_advanced_audio_data.json`

---

## 방법

1. 각 MP3를 Gemini STT로 전사 (`question_text=""`, 힌트 없음).
2. 전사 결과를 풀의 `comparison.question` / `news_issue.question`과 정규화 유사도로 대조.
3. 유사도 **≥ 0.82** → `match`, 미만 → `mismatch`.
4. sports Q2/Q3 레거시 drift(화면 텍스트와 완전히 다른 질문 음성) 패턴 여부 확인.

---

## 요약

| 항목 | 결과 |
|------|------|
| 검사 파일 수 | 40 / 40 (누락 0) |
| STT 실패 | 0 |
| **일치 (match)** | **40** |
| **불일치 (mismatch)** | **0** |
| sports형 drift 의심 | **0건** |

**결론:** Advanced 풀 20세트 전체에서 화면 텍스트와 음성이 어긋난 세트는 없음. sports Q2/Q3처럼 레거시 음성이 다른 질문을 읽는 패턴은 발견되지 않음.

---

## 세트별 유사도 (전수)

| set_id | comparison | news_issue |
|--------|------------|------------|
| banks | 1.000 | 1.000 |
| education | 1.000 | 1.000 |
| environment | 1.000 | 1.000 |
| fashion | 1.000 | 1.000 |
| gatherings | 1.000 | 1.000 |
| health | 1.000 | 1.000 |
| holidays | 1.000 | 1.000 |
| home | **0.997** | 1.000 |
| industry | 1.000 | 1.000 |
| internet | 1.000 | 1.000 |
| jobs | 1.000 | 1.000 |
| neighborhood | 1.000 | 1.000 |
| phone | 1.000 | 1.000 |
| restaurants | 1.000 | 1.000 |
| shopping | 1.000 | 1.000 |
| social_media | 1.000 | 1.000 |
| technology | 1.000 | 1.000 |
| transportation | 1.000 | **0.988** |
| travel | 1.000 | 1.000 |
| weather | 1.000 | 1.000 |

---

## 불일치 세트

**없음** (threshold 0.82 기준 mismatch 0건).

---

## 유사도 1.0 미만 — 수동 확인 권장 (match 처리됨)

threshold는 통과했으나 STT와 화면 텍스트에 단어 차이가 있어, 필요 시 사람 귀/원문 대조를 권장.

| set_id | 슬롯 | 화면 텍스트 (발췌) | STT 전사 (발췌) | sim | 추정 원인 |
|--------|------|-------------------|-----------------|-----|-----------|
| home | comparison | …parents' way … **compare** to yours? | …parents' way … **compared** to yours? | 0.997 | 시제/어미 차이 — STT 표기 또는 TTS 억양, drift 아님 |
| transportation | news_issue | …problems do **riders** deal with… | …problems do **writers** deal with… | 0.988 | 동음/유사음 혼동 가능 (`riders`↔`writers`). **수동 청취 권장** — STT 오인식 vs 실제 녹음 오류 구분 필요 |

두 건 모두 질문 전체가 바뀐 sports형 레거시 drift 패턴과는 다름 (동일 문맥·동일 구조, 단어 1~2개 차이).

---

## sports drift 패턴 대비

| 패턴 | sports (과거) | advanced (본 검사) |
|------|---------------|---------------------|
| 증상 | 화면 질문과 전혀 다른 레거시 질문 음성 | 해당 없음 |
| 유사도 | threshold 미달 예상 | 최저 0.988, 전부 match |
| 영향 범위 | 특정 topic Q2/Q3 | 40/40 일치 |

---

## 부록 — 검사 환경

- STT: Gemini multimodal (프로젝트 기존 STT 파이프라인)
- 정규화: 소문자·구두점·공백 제거 후 SequenceMatcher ratio
- match threshold: **0.82**
