# 검사 3 — 죽은 CSS 셀렉터 전수 스캔

**일시:** 2026-06-04  
**대상:** `ui/styles.py` 전체  
**기준 DOM:** Streamlit **1.50** (`data-testid="stMain"`, `stBaseButton-*`, `.st-key-*`)  
**원시 데이터:** `audit_dead_selectors_data.json`  
**코드 수정:** 없음

---

## 요약 카운트

| 패턴 | 출현 | 1.50 상태 |
|------|------|-----------|
| `button[key=...]` | **0** (일반) / **4** (`pat_ex_toggle`, `pat_detail_close`) | ❌ 죽음 — `key`는 버튼 attr가 아니라 컨테이너 `.st-key-*` |
| `button[kind=...]` | **25줄** | ❌ 죽음 — `kind` attr 미사용 |
| `button[data-testid="baseButton-*"]` (st 접두 없음) | **26줄** | ❌ 죽음 — `stBaseButton-*`가 정식 |
| `section.main:has(...)` (동일 줄에 stMain 없음) | **215줄** | ⚠️ 죽음/레거시 — 1.50은 `[data-testid="stMain"]` |
| `[data-testid="stMain"]` | **504줄** | ✅ 정상 |
| `stBaseButton-*` | **45줄** | ✅ 정상 |
| `.st-key-*` | **20줄** | ✅ 정상 (홈 QA 네비 등) |

---

## 죽은 셀렉터 상세 표

### A. `button[key*="..."]` — 패턴 화면 예시 토글

| 셀렉터 (발췌) | 줄 | 칠하려던 대상 | 왜 안 먹는지 | 1.50 호환 수정안 |
|---------------|-----|---------------|--------------|------------------|
| `…stButton]:has(button[key*="pat_ex_toggle"])` | 2877, 2885 | 패턴 카드 예문 펼치기 버튼 (`pat_ex_toggle_{row_key}`) | `st.button(key=…)` → DOM은 `div.stElementContainer.st-key-pat_ex_toggle_*`, button에 `key` attr 없음 | `[data-testid="stMain"]:has(.pat-screen-marker) div[data-testid="stElementContainer"][class*="st-key-pat_ex_toggle"] div[data-testid="stButton"] > button` |
| `…stButton]:has(button[key*="pat_detail_close"])` | 2878, 2886 | 패턴 상세 닫기 (`pat_detail_close_{row_key}`) | 동일 | `…[class*="st-key-pat_detail_close"]…` |
| `…stHorizontalBlock]:has(button[key*="pat_detail_close"])` | 2881 | 닫기 버튼 행 간격 | 동일 | `…stHorizontalBlock:has([class*="st-key-pat_detail_close"])…` |

**Python key 출처:** `components/pattern_card_compact.py` L295, L304.

**현재 증상:** 예문 토글·닫기 버튼에 지정한 margin/padding/border 스타일 미적용 → 기본 Streamlit 버튼 외형.

---

### B. `button[kind="primary"|"secondary"]` — 25줄

Streamlit 1.50 버튼은 `data-testid="stBaseButton-primary"` / `stBaseButton-secondary`만 사용. `kind` HTML attribute 없음.

| 화면/마커 | 줄 (예) | 칠하려던 대상 | 1.50 수정안 |
|-----------|---------|---------------|-------------|
| 온보딩 `.onb-marker` | 483–526 | Google 로그인·secondary CTA 전폭·여백 | `button[data-testid="stBaseButton-secondary"]` (이미 인접 줄에 st 버전 **병렬 존재** — `kind` 줄만 삭제 가능) |
| 온보딩 선택지 `.onb-choice-list` | 839, 846 | primary/secondary 선택 버튼 | `stBaseButton-primary/secondary` only |
| 홈 `.home-screen` continue actions | 1521–1553 | 이어하기 primary/secondary | `stBaseButton-*` (kind 줄 제거) |
| 주제별 `.tq-screen-marker` | 1838 | primary CTA | `stBaseButton-primary` |
| 모의고사 `.mx-marker` listen compact | 3513–3516 | 재생/compact 버튼 | `[data-testid="stMain"]:has(.mx-marker) … stBaseButton-*` (**section.main → stMain 교체**) |
| 모의고사 `.mx-marker` legacy `.stButton` | 3919, 3925 | primary hover | `stBaseButton-primary` |
| 글로벌 primary | 4791, 4800 | 앱 전역 primary | `stBaseButton-primary` |
| accent scope (teal/blue/purple/pink/amber/coral) | 4812–4872 | 주제별 accent primary | `stBaseButton-primary` |

**참고:** 많은 규칙이 **같은 블록에** `kind` + `baseButton-*` + `stBaseButton-*`를 나열. **stBaseButton 줄만 살아 있음** → `kind`/`baseButton` 줄은 dead weight.

---

### C. `button[data-testid="baseButton-*"]` (st 접두 없음) — 26줄

| 화면 | 줄 (예) | 의도 | 수정안 |
|------|---------|------|--------|
| 온보딩 | 484–527, 840–847 | secondary/primary 구분 | → `stBaseButton-secondary` / `stBaseButton-primary` |
| 홈 continue | 1522–1554 | CTA 색 | → `stBaseButton-*` |
| tq-screen | 1839 | primary | → `stBaseButton-primary` |
| mx listen compact | 3514–3517 | compact 버튼 | → stMain + stBaseButton |
| 글로벌·accent | 4792–4873 | primary 색상 | → stBaseButton-primary |
| mx-record-stage | 4949 | `:not([kind=…]):not([data-testid="baseButton-primary"])` | → `:not([data-testid="stBaseButton-primary"])` |

---

### D. `section.main:has(...)` — 215줄 (stMain 미동행)

1.50 메인 래퍼는 `[data-testid="stMain"]`. `section.main` 단독 규칙은 **매칭 실패**.

| 화면/마커 | 대표 줄 | 칠하려던 대상 | stMain-only 규칙 존재? | 수정안 |
|-----------|---------|---------------|------------------------|--------|
| 전역 레이아웃 | 96, 122–141 | block-container, padding | 부분 중복 | `main, [data-testid="stMain"], .block-container` |
| 온보딩 `.onb-marker` | 285–471 | 카드·브랜드·CTA·링크 | 버튼 일부만 stMain 병렬 | `section.main` → `[data-testid="stMain"]` 일괄 치환 |
| 모의고사 `.mx-marker` | 3513+, 3919+ | listen/record UI | **없음** (mx는 section.main only) | `[data-testid="stMain"]:has(.mx-marker) …` |
| `.mx-record-stage` | 126, 4949+ | 녹음 스테이지 레이아웃 | 일부 stMain | stMain으로 통일 |

**패턴 화면 `.pat-screen-marker`:** 대부분 **이미 stMain만 사용** (L2353+) → ✅ 양호. 죽은 부분은 **pat_ex_toggle의 button[key]** 뿐.

**홈 `.home-screen`:** QA 카드·`.st-key-qa_nav_*` — stMain + st-key 사용 ✅.

---

### E. `button[key=...]` (일반) — 0줄

이전 마이그레이션으로 `button[key=…]` 일반 패턴은 제거됨. 잔존은 **pat_ex_toggle / pat_detail_close** 4줄뿐.

---

## 패턴 화면 (`pat_ex_toggle`) 요약

```
components/pattern_card_compact.py
  key=f"pat_ex_toggle_{row_key}"
  key=f"pat_detail_close_{row_key}"

ui/styles.py L2877–2886
  button[key*="pat_ex_toggle"]  ← DOM 불일치
```

**기대 UX:** 펼친 카드 하단 예문 토글·닫기 버튼 — 8px margin, 10px radius, 회색 border.  
**실제:** 셀렉터 미매칭 → Streamlit 기본 secondary 스타일.

**수정 예시 (한 줄):**

```css
[data-testid="stMain"]:has(.pat-screen-marker)
  div[data-testid="stElementContainer"][class*="st-key-pat_ex_toggle"]
  div[data-testid="stButton"] > button { … }
```

---

## 우선순위 제안 (적용 안 함)

1. **P0** — `pat_ex_toggle` / `pat_detail_close` → `.st-key-*` (사용자 눈에 띄는 패턴 UX)
2. **P1** — `.mx-marker` 블록 `section.main` → `stMain` (모의고사 listen/record)
3. **P2** — `button[kind]` / `baseButton-*` dead 줄 정리 (stBaseButton 병렬 줄만 남기기)
4. **P3** — 온보딩 `section.main-only` 215줄 일괄 stMain 치환

---

## 스캔 방법

- `ui/styles.py` 정규 패턴 grep + 줄 번호 수집
- `section.main` vs `[data-testid="stMain"]` 동일 줄 공존 여부 스크립트 집계
- `components/pattern_card_compact.py` key와 CSS `:has(button[key=…])` 교차 확인
