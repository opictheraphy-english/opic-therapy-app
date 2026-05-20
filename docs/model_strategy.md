# Model strategy — Mini Mock vs Real Mock

This document separates **fast diagnostic** flows from **precision exam** flows so lightweight Mini Mock settings do not weaken future Real Mock evaluation.

## 1. Mini Mock V2

| Aspect | Choice |
|--------|--------|
| **Purpose** | Fast diagnostic / onboarding / trial (~5 minutes) |
| **STT model** | `GEMINI_STT_MODEL` (default: `gemini-2.5-flash-lite`) |
| **Report model** | `GEMINI_MINI_REPORT_MODEL`, or `GEMINI_REPORT_MODEL` for backward compatibility |
| **Report default** | `gemini-2.5-flash-lite` |
| **Rubric** | Lightweight, fast, student-friendly (`services/mini_mock_v2_rubric.py`) |
| **Expected output** | Quick level estimate, short feedback, practice mission |

Mini Mock V2 prioritizes **speed and stability** over exhaustive scoring. The light rubric and smaller Gemini payload are intentional.

Config: `MINI_REPORT_MODEL_NAME` / `build_mini_mock_v2_report_model_candidates()` in `services/evaluation/eval_config.py`.

## 2. Real Mock V2 (future)

| Aspect | Choice |
|--------|--------|
| **Purpose** | Full 15-question precision mock exam |
| **STT model** | May use the same STT stack as Mini Mock (`GEMINI_STT_MODEL`) |
| **Report model** | **`GEMINI_REAL_REPORT_MODEL`** (separate from Mini Mock) |
| **Report default** | `gemini-2.5-flash` |
| **Rubric** | Detailed, higher reliability (not the Mini Mock light rubric) |
| **Expected output** | Full report, score trend, question-type breakdown |
| **Latency** | Can take longer than Mini Mock; async/pending queue acceptable later |

Config placeholder: `REAL_REPORT_MODEL_NAME` in `services/evaluation/eval_config.py`. **Not wired to any view yet.**

Legacy mock exam (V1) continues to use `GEMINI_REPORT_MODEL` / `REPORT_MODEL_NAME` until Real Mock V2 ships.

## 3. Rule

**Do not reuse the Mini Mock lightweight rubric as the final Real Mock rubric.**

- Mini Mock: `build_mini_mock_v2_light_rubric_prompt()` (and optional detailed mini rubric for experiments only).
- Real Mock V2: will need its own rubric module and report pipeline when implemented.

## Environment variables (summary)

| Variable | Used by | Default |
|----------|---------|---------|
| `GEMINI_STT_MODEL` | STT (Mini + future Real) | `gemini-2.5-flash-lite` |
| `GEMINI_MINI_REPORT_MODEL` | Mini Mock V2 report | `gemini-2.5-flash-lite` |
| `GEMINI_REAL_REPORT_MODEL` | Future Real Mock V2 report | `gemini-2.5-flash` |
| `GEMINI_REPORT_MODEL` | Legacy mock + fallback for Mini/Real if specific var unset | `gemini-2.5-flash` |
| `GEMINI_MODEL` | Legacy alias for both STT/report if newer vars unset | — |
