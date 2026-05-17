"""Global Streamlit CSS — premium medical AI design system."""

GLOBAL_CSS = """
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable.css");

    :root {
      --font-sans: "Pretendard Variable", "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color-scheme: light only;
      --mint: #0d9488;
      --mint-soft: #ccfbf1;
      --mint-muted: rgba(13, 148, 136, 0.12);
      --navy: #0f172a;
      --navy-soft: #1e293b;
      --bg-warm: #fafaf9;
      --bg-page: linear-gradient(180deg, #fafaf9 0%, #f4f4f5 48%, #f1f5f9 100%);
      --surface: rgba(255, 255, 255, 0.72);
      --border-subtle: rgba(17, 24, 39, 0.08);
      --text: #111827;
      --text-secondary: #4b5563;
      --text-muted: #6b7280;
      --text-soft: #9ca3af;
      --danger-soft: #fecaca;
      --danger-text: #b91c1c;
      --radius-lg: 20px;
      --radius-md: 14px;
      --radius-sm: 10px;
      --shadow-float: 0 8px 32px rgba(15, 23, 42, 0.08), 0 2px 8px rgba(15, 23, 42, 0.04);
      --shadow-card: 0 1px 0 rgba(15, 23, 42, 0.04), 0 12px 40px rgba(15, 23, 42, 0.06);
      --space-1: 8px;
      --space-2: 16px;
      --space-3: 24px;
      --space-4: 40px;
      --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
    }

    html, body,
    .stApp,
    [data-testid="stAppViewContainer"],
    .block-container,
    .stMarkdown,
    h1, h2, h3, h4, h5, h6,
    p, span, div, input, textarea, select, label {
      font-family: var(--font-sans) !important;
    }

    html, body, .stMarkdown {
      color: var(--text);
    }

    html, body, .stMarkdown, .block-container {
      line-height: 1.55;
    }

    small, .ds-muted, .tp-topic-sub, .cc-meta, .mx-record-hint {
      line-height: 1.45;
    }

    h1, h2, h3, h4, h5, h6,
    .mx-mode-title, .tp-topic-title, .cc-title, .tb-title {
      line-height: 1.25;
    }

    /* Lock html/body background to the page gradient so anchor navigations
     * (?nav=...) don't flash white between the old page unload and the new
     * Streamlit shell paint. */
    html, body {
      background: #f8faf9 !important;
      background-color: #f8faf9 !important;
      color: #111827 !important;
      color-scheme: light only !important;
    }

    [data-testid="stAppViewContainer"] {
      background: #f8faf9 !important;
      color: #111827 !important;
      color-scheme: light only !important;
    }

    .stApp {
      background: var(--bg-page) !important;
      color: #111827 !important;
      color-scheme: light only !important;
    }

    main, section.main, .block-container {
      background: transparent !important;
      color: #111827 !important;
    }

    /* Single-app routing: no reserved Streamlit sidebar (bottom nav is primary). */
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }

    /* Quiet Streamlit's "Running…" status widget. Reruns happen often on tab
     * switches; the bouncing dot in the corner makes everything feel like a
     * page reload. We softly hide it without removing the toolbar entirely. */
    [data-testid="stStatusWidget"],
    [data-testid="stToolbarActions"] [data-testid="stStatusWidget"] {
      opacity: 0 !important;
      pointer-events: none !important;
      transition: opacity 0.2s ease;
    }

    /* Decoration block that sometimes pulses on rerun — keep it from drawing
     * attention to the rerender. */
    [data-testid="stDecoration"] {
      opacity: 0 !important;
    }

    section.main > div {
      padding-top: 0.6rem !important;
      padding-bottom: 96px !important;
    }

    /* Subtle fade-in on each rerun so the rerender feels like a transition
     * instead of a hard repaint. Kept short (140ms) and opacity-only so it
     * never delays interactivity. */
    section.main > div > div.block-container {
      animation: pageSettle 0.14s var(--ease-out);
    }
    @keyframes pageSettle {
      from { opacity: 0.85; }
      to { opacity: 1; }
    }
    @media (prefers-reduced-motion: reduce) {
      section.main > div > div.block-container { animation: none !important; }
    }

    /* --- Mobile top bar (back · title · home) -------------------------- */
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 12px;
      margin: 0 0 12px 0;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.78);
      backdrop-filter: saturate(160%) blur(14px);
      -webkit-backdrop-filter: saturate(160%) blur(14px);
      border: 1px solid rgba(15, 23, 42, 0.06);
      box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02);
    }
    .topbar .tb-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 12px;
      color: #0f172a;
      text-decoration: none !important;
      background: transparent;
      border: 1px solid transparent;
      transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }
    .topbar .tb-btn:hover {
      background: rgba(15, 23, 42, 0.05);
      border-color: rgba(15, 23, 42, 0.08);
      color: #0d9488;
    }
    .topbar .tb-btn:active { transform: scale(0.96); }
    .topbar .tb-spacer { visibility: hidden; }
    .topbar .tb-titleblock {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 0 4px;
    }
    .topbar .tb-eyebrow {
      font-size: 0.65rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #94a3b8;
      line-height: 1.2;
    }
    .topbar .tb-title {
      font-size: 1rem;
      font-weight: 700;
      color: #0f172a;
      letter-spacing: -0.01em;
      line-height: 1.25;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 60vw;
    }

    /* Typography system */
    .ds-display {
      font-size: clamp(2rem, 4.5vw, 2.75rem);
      font-weight: 800;
      letter-spacing: -0.03em;
      color: var(--navy);
      line-height: 1.15;
      margin: 0 0 var(--space-1) 0;
    }
    .ds-hero-tag {
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--mint);
      margin-bottom: var(--space-2);
    }
    .ds-subtitle {
      font-size: 1.05rem;
      color: var(--text-secondary);
      font-weight: 450;
      line-height: 1.55;
      margin: 0;
    }
    .ds-section-title {
      font-size: 0.8125rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin: var(--space-4) 0 var(--space-2) 0;
    }
    .ds-h2 {
      font-size: 1.35rem;
      font-weight: 700;
      color: var(--navy);
      letter-spacing: -0.02em;
      margin: 0 0 var(--space-2) 0;
    }
    .ds-muted { color: var(--text-muted); font-size: 0.9rem; line-height: 1.5; }
    .ds-footer-copy {
      text-align: center;
      font-size: 0.7rem !important;
      color: var(--text-soft) !important;
      letter-spacing: 0.02em;
      margin-top: 0.5rem !important;
    }

    [data-testid="stCaption"] {
      text-align: center !important;
    }
    [data-testid="stCaption"] * {
      font-size: 0.7rem !important;
      color: var(--text-soft) !important;
    }

    /* Glass cards */
    .glass-card {
      background: var(--surface);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      padding: var(--space-3);
      border-radius: var(--radius-lg);
      border: 1px solid var(--border-subtle);
      box-shadow: var(--shadow-card);
      margin-bottom: var(--space-2);
      transition: transform 0.22s var(--ease-out), box-shadow 0.22s var(--ease-out), border-color 0.2s ease;
    }
    .glass-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 48px rgba(15, 23, 42, 0.1);
      border-color: rgba(13, 148, 136, 0.15);
    }

    .glass-card-quiet {
      background: rgba(255, 255, 255, 0.55);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: var(--space-2) var(--space-3);
      margin-bottom: var(--space-2);
    }

    /* --- Onboarding (first entry, scoped) — premium mobile coach intro ----- */
    section.main:has(.onb-marker) {
      color-scheme: light only;
      background:
        radial-gradient(ellipse 95% 60% at 50% -8%, rgba(20, 184, 166, 0.14) 0%, transparent 58%),
        radial-gradient(ellipse 70% 45% at 100% 20%, rgba(204, 251, 241, 0.35) 0%, transparent 50%),
        linear-gradient(180deg, #f8faf9 0%, #f6fbfa 42%, #f1f5f9 100%) !important;
      color: #111827 !important;
    }
    section.main:has(.onb-marker) div.block-container {
      max-width: 520px !important;
      margin: 0 auto !important;
      padding-top: 1rem !important;
      padding-bottom: 5rem !important;
      padding-left: 1rem !important;
      padding-right: 1rem !important;
    }
    section.main:has(.onb-marker) .onb-shell {
      width: 100%;
      max-width: 520px;
      margin: 0 auto;
    }
    section.main:has(.onb-marker) .onb-progress {
      text-align: center;
      margin: 0 0 1rem 0;
      padding: 0 0.15rem;
    }
    section.main:has(.onb-marker) .onb-progress-label {
      display: block;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #6b7280 !important;
      margin-bottom: 10px;
    }
    section.main:has(.onb-marker) .onb-progress-track {
      display: block;
      width: 100%;
      max-width: 220px;
      height: 6px;
      margin: 0 auto 12px auto;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.08);
      overflow: hidden;
      border: 1px solid rgba(13, 148, 136, 0.08);
    }
    section.main:has(.onb-marker) .onb-progress-fill {
      display: block;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #0f9f8f 0%, #14b8a6 55%, #2dd4bf 100%);
      box-shadow: 0 0 12px rgba(20, 184, 166, 0.35);
      transition: width 0.35s cubic-bezier(0.22, 1, 0.36, 1);
    }
    section.main:has(.onb-marker) .onb-progress-dots {
      display: flex;
      justify-content: center;
      gap: 8px;
      align-items: center;
    }
    section.main:has(.onb-marker) .onb-dot {
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.14);
      transition: transform 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
    }
    section.main:has(.onb-marker) .onb-dot--on {
      background: linear-gradient(135deg, #0f9f8f 0%, #14b8a6 100%);
      transform: scale(1.2);
      box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.2);
    }
    section.main:has(.onb-marker) .onb-hero-premium {
      border-radius: 24px;
      padding: 1.65rem 1.35rem 1.5rem 1.35rem;
      margin-bottom: 1.25rem;
      background:
        radial-gradient(ellipse 100% 80% at 100% 0%, rgba(45, 212, 191, 0.18) 0%, transparent 52%),
        radial-gradient(ellipse 80% 60% at 0% 100%, rgba(13, 148, 136, 0.08) 0%, transparent 50%),
        linear-gradient(165deg, #ffffff 0%, #f8fafc 55%, #f1f5f9 100%);
      border: 1px solid rgba(13, 148, 136, 0.14);
      box-shadow: 0 12px 40px rgba(15, 23, 42, 0.07), 0 1px 0 rgba(255, 255, 255, 0.8) inset;
    }
    section.main:has(.onb-marker) .onb-badge {
      display: inline-block;
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #0f766e;
      background: rgba(204, 251, 241, 0.65);
      border: 1px solid rgba(13, 148, 136, 0.22);
      padding: 6px 12px;
      border-radius: 999px;
      margin-bottom: 14px;
    }
    section.main:has(.onb-marker) .onb-title-xl {
      font-size: clamp(1.5rem, 5vw, 1.95rem);
      font-weight: 800;
      letter-spacing: -0.035em;
      color: #111827 !important;
      line-height: 1.2;
      margin: 0 0 12px 0;
    }
    section.main:has(.onb-marker) .onb-sub-hero {
      font-size: 0.98rem;
      line-height: 1.55;
      color: #4b5563 !important;
      margin: 0 0 1rem 0;
      font-weight: 500;
    }
    section.main:has(.onb-marker) .onb-mini-mock {
      border-radius: 18px;
      padding: 14px 14px 12px 14px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(15, 23, 42, 0.06);
      box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
      margin-top: 4px;
    }
    section.main:has(.onb-marker) .onb-mini-head {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 10px;
    }
    section.main:has(.onb-marker) .onb-mini-tag {
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.06em;
    }
    section.main:has(.onb-marker) .onb-mini-pill {
      font-size: 0.65rem;
      font-weight: 700;
      color: #0f766e;
      background: rgba(204, 251, 241, 0.9);
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid rgba(13, 148, 136, 0.2);
    }
    section.main:has(.onb-marker) .onb-mini-q {
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--navy);
      margin: 0 0 12px 0;
      line-height: 1.45;
    }
    section.main:has(.onb-marker) .onb-mini-flow {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
      margin-bottom: 12px;
    }
    section.main:has(.onb-marker) .onb-mini-chip {
      font-size: 0.72rem;
      font-weight: 600;
      color: var(--text-secondary);
      background: rgba(241, 245, 249, 0.95);
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(15, 23, 42, 0.06);
    }
    section.main:has(.onb-marker) .onb-mini-chip--rec {
      background: rgba(254, 243, 199, 0.45);
      border-color: rgba(245, 158, 11, 0.25);
    }
    section.main:has(.onb-marker) .onb-mini-chip--ai {
      background: rgba(204, 251, 241, 0.55);
      border-color: rgba(13, 148, 136, 0.22);
      color: #0f766e;
    }
    section.main:has(.onb-marker) .onb-mini-arrow {
      font-size: 0.75rem;
      color: var(--text-soft);
      font-weight: 600;
    }
    section.main:has(.onb-marker) .onb-mini-foot {
      font-size: 0.72rem;
      color: var(--text-muted);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px;
    }
    section.main:has(.onb-marker) .onb-mini-dot { opacity: 0.5; }
    section.main:has(.onb-marker) .onb-head-card {
      border-radius: 24px;
      padding: 1.25rem 1.15rem 1rem 1.15rem;
      margin-bottom: 0.85rem;
      background: #ffffff;
      border: 1px solid rgba(15, 23, 42, 0.06);
      box-shadow: 0 10px 32px rgba(15, 23, 42, 0.06);
    }
    section.main:has(.onb-marker) .onb-head-card--plan {
      margin-bottom: 0.75rem;
    }
    section.main:has(.onb-marker) .onb-eyebrow {
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0 0 10px 0;
    }
    section.main:has(.onb-marker) .onb-h2 {
      font-size: clamp(1.15rem, 4.5vw, 1.35rem);
      font-weight: 800;
      color: #111827 !important;
      letter-spacing: -0.025em;
      margin: 0 0 8px 0;
      line-height: 1.28;
    }
    section.main:has(.onb-marker) .onb-muted {
      font-size: 0.92rem;
      line-height: 1.55;
      color: #6b7280 !important;
      margin: 0;
      font-weight: 500;
    }
    section.main:has(.onb-marker) .onb-choice-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 0.65rem;
    }
    section.main:has(.onb-marker) .onb-pick-card {
      position: relative;
      display: grid;
      grid-template-columns: auto 1fr;
      grid-template-rows: auto auto;
      gap: 2px 10px;
      padding: 14px 14px 12px 14px;
      border-radius: 16px;
      background: #ffffff;
      border: 1.5px solid rgba(15, 23, 42, 0.08);
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
      transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    }
    section.main:has(.onb-marker) .onb-pick-card--selected {
      background: linear-gradient(165deg, #e6fffa 0%, #ffffff 48%);
      border-color: rgba(20, 184, 166, 0.55);
      box-shadow: 0 8px 24px rgba(20, 184, 166, 0.14);
    }
    section.main:has(.onb-marker) .onb-pick-check {
      grid-row: 1 / span 2;
      align-self: center;
      width: 22px;
      height: 22px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.72rem;
      font-weight: 800;
      color: #ffffff;
      background: linear-gradient(135deg, #0f9f8f 0%, #14b8a6 100%);
      box-shadow: 0 2px 8px rgba(20, 184, 166, 0.35);
    }
    section.main:has(.onb-marker) .onb-pick-check--empty {
      background: #f3f4f6;
      color: transparent;
      box-shadow: none;
      border: 1.5px solid rgba(15, 23, 42, 0.1);
    }
    section.main:has(.onb-marker) .onb-pick-badge {
      grid-column: 2;
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      color: #0f766e;
      margin-bottom: 0;
    }
    section.main:has(.onb-marker) .onb-pick-title {
      grid-column: 2;
      margin: 0;
      font-size: 0.98rem;
      font-weight: 700;
      color: #111827 !important;
      line-height: 1.35;
    }
    section.main:has(.onb-marker) .onb-pick-body {
      grid-column: 2;
      margin: 0;
      font-size: 0.86rem;
      line-height: 1.5;
      color: #6b7280 !important;
      font-weight: 500;
    }
    section.main:has(.onb-marker) .onb-choice-list div[data-testid="stButton"] {
      margin: -4px 0 8px 0 !important;
    }
    section.main:has(.onb-marker) .onb-choice-list div[data-testid="stButton"] > button {
      min-height: 2.35rem !important;
      border-radius: 12px !important;
      font-size: 0.82rem !important;
      padding: 0.4rem 0.75rem !important;
      white-space: nowrap !important;
    }
    section.main:has(.onb-marker) .onb-plan-card {
      margin: 0 0 0.85rem 0;
      padding: 18px 16px;
      border-radius: 20px;
      background: linear-gradient(165deg, #e6fffa 0%, #f0fdfa 40%, #ffffff 100%);
      border: 1px solid rgba(20, 184, 166, 0.22);
      box-shadow: 0 8px 28px rgba(20, 184, 166, 0.1);
    }
    section.main:has(.onb-marker) .onb-plan-eyebrow {
      font-size: 0.78rem;
      font-weight: 700;
      color: #0f766e;
      margin: 0 0 10px 0;
      letter-spacing: 0.02em;
    }
    section.main:has(.onb-marker) .onb-plan-list {
      margin: 0;
      padding-left: 1.35rem;
      color: var(--text-secondary);
      font-size: 0.95rem;
      line-height: 1.6;
      font-weight: 500;
      list-style-type: decimal;
    }
    section.main:has(.onb-marker) .onb-plan-list li { margin-bottom: 8px; }
    section.main:has(.onb-marker) .onb-actions {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 0.35rem;
    }
    section.main:has(.onb-marker) .onb-actions--hero {
      margin-top: 0.15rem;
    }
    section.main:has(.onb-marker) .onb-actions--stack {
      gap: 10px;
    }
    section.main:has(.onb-marker) .onb-actions div[data-testid="stButton"] > button {
      border-radius: 15px !important;
      min-height: 3rem !important;
      font-weight: 700 !important;
      font-size: 0.95rem !important;
      letter-spacing: -0.01em;
    }
    section.main:has(.onb-marker) .onb-actions div[data-testid="stButton"] > button[kind="primary"],
    section.main:has(.onb-marker) .onb-actions div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: linear-gradient(135deg, #0f9f8f 0%, #14b8a6 100%) !important;
      color: #ffffff !important;
      border: none !important;
      box-shadow: 0 6px 20px rgba(20, 184, 166, 0.32) !important;
    }
    section.main:has(.onb-marker) .onb-actions div[data-testid="stButton"] > button[kind="secondary"],
    section.main:has(.onb-marker) .onb-actions div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {
      background: #ffffff !important;
      color: #111827 !important;
      border: 1.5px solid rgba(15, 23, 42, 0.1) !important;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
    }
    section.main:has(.onb-marker) .onb-actions--split div[data-testid="column"] {
      padding: 0 4px !important;
    }
    section.main:has(.onb-marker) .onb-choice-list div[data-testid="stButton"] > button[kind="primary"],
    section.main:has(.onb-marker) .onb-choice-list div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: rgba(20, 184, 166, 0.12) !important;
      color: #0f766e !important;
      border: 1.5px solid rgba(20, 184, 166, 0.45) !important;
      box-shadow: none !important;
    }
    section.main:has(.onb-marker) .onb-choice-list div[data-testid="stButton"] > button[kind="secondary"],
    section.main:has(.onb-marker) .onb-choice-list div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {
      background: #f9fafb !important;
      color: #6b7280 !important;
      border: 1px solid rgba(15, 23, 42, 0.08) !important;
    }
    section.main:has(.onb-marker) [data-testid="stCaptionContainer"],
    section.main:has(.onb-marker) [data-testid="stCaptionContainer"] p {
      color: #9ca3af !important;
      text-align: center;
      font-size: 0.78rem !important;
    }

    /* --- Session splash (before Home, scoped) ----------------------------- */
    section.main:has(.splash-marker) {
      background:
        radial-gradient(ellipse 85% 50% at 50% 0%, rgba(13, 148, 136, 0.14) 0%, transparent 52%),
        linear-gradient(180deg, #fafaf9 0%, #f4f4f5 50%, #f1f5f9 100%) !important;
    }
    section.main:has(.splash-marker) div.block-container {
      max-width: 480px !important;
      margin: 0 auto !important;
      padding-top: min(12vh, 5.5rem) !important;
      padding-bottom: 4rem !important;
      padding-left: 1.1rem !important;
      padding-right: 1.1rem !important;
    }
    section.main:has(.splash-marker) .splash-root {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: min(72vh, 520px);
    }
    section.main:has(.splash-marker) .splash-card {
      width: 100%;
      border-radius: 24px;
      padding: 2rem 1.5rem 1.75rem 1.5rem;
      text-align: center;
      background:
        radial-gradient(ellipse 100% 70% at 100% 0%, rgba(45, 212, 191, 0.2) 0%, transparent 48%),
        linear-gradient(165deg, #ffffff 0%, #f8fafc 55%, #f1f5f9 100%);
      border: 1px solid rgba(13, 148, 136, 0.16);
      box-shadow: 0 14px 44px rgba(15, 23, 42, 0.08), 0 1px 0 rgba(255, 255, 255, 0.85) inset;
    }
    section.main:has(.splash-marker) .splash-brand {
      font-size: clamp(1.65rem, 6vw, 2.1rem);
      font-weight: 800;
      letter-spacing: -0.04em;
      margin: 0 0 6px 0;
      background: linear-gradient(135deg, #0f766e 0%, #14b8a6 45%, #2dd4bf 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
    section.main:has(.splash-marker) .splash-sub {
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin: 0 0 1.25rem 0;
    }
    section.main:has(.splash-marker) .splash-line {
      font-size: 1.08rem;
      line-height: 1.55;
      font-weight: 600;
      color: var(--navy);
      margin: 0 0 1.5rem 0;
    }
    section.main:has(.splash-marker) .splash-loading {
      font-size: 0.88rem;
      color: var(--text-secondary);
      margin: 0 0 14px 0;
      font-weight: 500;
    }
    section.main:has(.splash-marker) .splash-dots {
      display: flex;
      justify-content: center;
      gap: 10px;
      margin-top: 4px;
    }
    section.main:has(.splash-marker) .splash-dots span {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: linear-gradient(135deg, #0d9488 0%, #5eead4 100%);
      opacity: 0.35;
      animation: splash-dot 1.05s ease-in-out infinite;
    }
    section.main:has(.splash-marker) .splash-dots span:nth-child(2) { animation-delay: 0.18s; }
    section.main:has(.splash-marker) .splash-dots span:nth-child(3) { animation-delay: 0.36s; }
    @keyframes splash-dot {
      0%, 80%, 100% { transform: scale(0.92); opacity: 0.35; }
      40% { transform: scale(1.15); opacity: 1; }
    }

    /* Hero */
    .home-hero {
      border-radius: var(--radius-lg);
      padding: var(--space-4) var(--space-3);
      margin-bottom: var(--space-3);
      background:
        radial-gradient(ellipse 120% 80% at 100% 0%, rgba(13, 148, 136, 0.14) 0%, transparent 55%),
        radial-gradient(ellipse 90% 70% at 0% 100%, rgba(15, 23, 42, 0.06) 0%, transparent 50%),
        linear-gradient(180deg, #ffffff 0%, #fafaf9 100%);
      border: 1px solid var(--border-subtle);
      box-shadow: var(--shadow-card);
      /* Single global page settle animation handles fade-in; hero no longer
       * animates per-rerun so HOME doesn't visibly re-appear each time. */
    }

    .home-metrics {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: var(--space-2);
      margin-top: var(--space-2);
    }
    @media (max-width: 768px) {
      .home-metrics { grid-template-columns: 1fr; }
    }
    .metric-tile {
      background: rgba(255, 255, 255, 0.65);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: var(--space-2);
      text-align: left;
    }
    .metric-label { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }
    .metric-value { font-size: 1.35rem; font-weight: 700; color: var(--navy); letter-spacing: -0.02em; }
    .metric-hint { font-size: 0.8rem; color: var(--text-soft); margin-top: 4px; }

    .feature-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: var(--space-2);
    }
    @media (max-width: 900px) {
      .feature-grid { grid-template-columns: 1fr; }
    }
    .feature-tile {
      padding: var(--space-3);
      border-radius: var(--radius-lg);
      border: 1px solid var(--border-subtle);
      background: rgba(255,255,255,0.65);
      transition: transform 0.2s var(--ease-out), border-color 0.2s;
    }
    .feature-tile:hover {
      transform: translateY(-3px);
      border-color: rgba(13, 148, 136, 0.2);
    }
    .feature-tile .ft-title { font-weight: 700; font-size: 1rem; color: var(--navy); margin-bottom: 8px; }
    .feature-tile .ft-body { font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5; }

    /* ------------------------------------------------------------------
     * Home "이어하기" (resume mock exam) card
     * ------------------------------------------------------------------ */
    .resume-card {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 18px 20px;
      border-radius: 18px;
      background:
        linear-gradient(135deg, rgba(13, 148, 136, 0.10) 0%, rgba(255, 255, 255, 0.6) 100%);
      border: 1px solid rgba(13, 148, 136, 0.22);
      box-shadow: 0 6px 22px rgba(13, 148, 136, 0.08);
      margin: 0 0 var(--space-3) 0;
    }
    .resume-card .rc-eyebrow {
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
    }
    .resume-card .rc-title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--navy);
      letter-spacing: -0.01em;
    }
    .resume-card .rc-meta {
      font-size: 0.85rem;
      color: var(--text-secondary);
    }
    .resume-card .rc-actions {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }
    .resume-card .rc-action {
      flex: 1;
      display: inline-block;
      text-align: center;
      padding: 12px 14px;
      border-radius: 12px;
      text-decoration: none !important;
      font-weight: 700;
      font-size: 0.95rem;
      transition: transform 0.12s ease, box-shadow 0.18s ease, background 0.18s ease;
    }
    .resume-card .rc-action.rc-primary {
      background: var(--mint);
      color: #ffffff !important;
      box-shadow: 0 2px 10px rgba(13, 148, 136, 0.25);
    }
    .resume-card .rc-action.rc-primary:hover {
      background: #0b8076;
      box-shadow: 0 6px 18px rgba(13, 148, 136, 0.32);
    }
    .resume-card .rc-action.rc-secondary {
      background: rgba(15, 23, 42, 0.04);
      color: var(--navy) !important;
      border: 1px solid var(--border-subtle);
    }
    .resume-card .rc-action.rc-secondary:hover {
      background: rgba(15, 23, 42, 0.07);
    }
    .resume-card .rc-action:active { transform: scale(0.98); }

    /* ==================================================================
     * Home screen — premium mobile dashboard (Step 2)
     * ==================================================================
     * Visual-only redesign. Routing, query params, and session_state are
     * untouched. Section order on the home view:
     *   .greeting → .continue-card → .qa-grid → .stats-row
     * Section labels use .home-section-h (soft, no uppercase tracking).
     */

    /* --- Section label -------------------------------------------------- */
    .home-section-h {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--navy);
      letter-spacing: -0.005em;
      margin: 22px 4px 10px 4px;
    }
    .home-section-h .h-soft {
      margin-left: 6px;
      font-weight: 500;
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    /* --- 1) Greeting ---------------------------------------------------- */
    .greeting {
      margin: 6px 0 18px 0;
      padding: 4px 4px 0 4px;
    }
    .greeting .gr-hello {
      display: flex;
      align-items: baseline;
      gap: 10px;
      font-size: clamp(1.6rem, 5vw, 2.05rem);
      font-weight: 800;
      letter-spacing: -0.025em;
      color: var(--navy);
      line-height: 1.15;
      margin: 0;
    }
    .greeting .gr-wave {
      display: inline-block;
      transform-origin: 70% 70%;
      animation: gr-wave 2.6s ease-in-out 0.6s 2;
    }
    @keyframes gr-wave {
      0%, 60%, 100% { transform: rotate(0deg); }
      10%, 30%      { transform: rotate(14deg); }
      20%, 40%      { transform: rotate(-10deg); }
      50%           { transform: rotate(8deg); }
    }
    @media (prefers-reduced-motion: reduce) {
      .greeting .gr-wave { animation: none !important; }
    }
    .greeting .gr-sub {
      margin: 6px 0 0 0;
      font-size: 1rem;
      color: var(--text-secondary);
      font-weight: 450;
      line-height: 1.55;
    }
    .greeting .gr-meta {
      margin-top: 12px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.72rem;
      font-weight: 600;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid var(--border-subtle);
      border-radius: 999px;
      padding: 4px 10px 4px 8px;
      letter-spacing: 0.005em;
    }
    .greeting .gr-meta-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--mint);
      box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
    }

    /* --- 2) Continue Study Card (primary CTA) --------------------------- */
    .continue-card {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 22px 22px 20px 22px;
      border-radius: 22px;
      margin: 4px 0 22px 0;
      overflow: hidden;
    }
    .continue-card::after {
      /* Soft mint glow in the top-right — purely decorative. */
      content: "";
      position: absolute;
      top: -36px;
      right: -28px;
      width: 160px;
      height: 160px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(13, 148, 136, 0.18) 0%, transparent 65%);
      pointer-events: none;
    }
    .continue-card--resume {
      background:
        linear-gradient(135deg, rgba(13, 148, 136, 0.14) 0%, rgba(255, 255, 255, 0.65) 100%),
        linear-gradient(180deg, #ffffff 0%, #fafaf9 100%);
      border: 1px solid rgba(13, 148, 136, 0.22);
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.03),
        0 12px 32px rgba(13, 148, 136, 0.10);
    }
    .continue-card--start {
      background:
        linear-gradient(135deg, rgba(13, 148, 136, 0.08) 0%, rgba(255, 255, 255, 0.6) 100%),
        linear-gradient(180deg, #ffffff 0%, #fafaf9 100%);
      border: 1px solid rgba(15, 23, 42, 0.06);
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.02),
        0 10px 28px rgba(15, 23, 42, 0.06);
    }
    .continue-card .cc-row-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      position: relative;
      z-index: 1;
    }
    .continue-card .cc-eyebrow {
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
    }
    .continue-card .cc-time {
      font-size: 0.78rem;
      color: var(--text-muted);
      font-weight: 600;
    }
    .continue-card .cc-title {
      font-size: 1.2rem;
      font-weight: 800;
      color: var(--navy);
      letter-spacing: -0.015em;
      line-height: 1.35;
      position: relative;
      z-index: 1;
    }
    .continue-card .cc-title .cc-of {
      font-weight: 600;
      color: var(--text-muted);
      letter-spacing: -0.005em;
    }
    .continue-card .cc-meta {
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.5;
      position: relative;
      z-index: 1;
    }
    .continue-card .cc-meta b {
      color: var(--navy);
      font-weight: 700;
    }
    .continue-card .cc-progress {
      height: 6px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.06);
      overflow: hidden;
      margin: 4px 0 2px 0;
      position: relative;
      z-index: 1;
    }
    .continue-card .cc-progress-fill {
      display: block;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--mint) 0%, #14b8a6 100%);
      transition: width 0.4s var(--ease-out);
    }
    .continue-card .cc-actions {
      display: flex;
      gap: 8px;
      margin-top: 6px;
      position: relative;
      z-index: 1;
    }
    .continue-card .cc-action {
      flex: 1;
      display: inline-block;
      text-align: center;
      padding: 13px 14px;
      border-radius: 14px;
      text-decoration: none !important;
      font-weight: 700;
      font-size: 0.95rem;
      letter-spacing: -0.005em;
      transition:
        transform 0.12s ease,
        background 0.18s ease,
        box-shadow 0.18s ease;
    }
    .continue-card .cc-action.cc-primary {
      color: #ffffff !important;
      background: var(--mint);
      box-shadow: 0 6px 18px rgba(13, 148, 136, 0.30);
    }
    .continue-card .cc-action.cc-primary:hover {
      background: #0b8076;
      box-shadow: 0 8px 22px rgba(13, 148, 136, 0.36);
    }
    .continue-card .cc-action.cc-secondary {
      color: var(--navy) !important;
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid var(--border-subtle);
    }
    .continue-card .cc-action.cc-secondary:hover {
      background: rgba(15, 23, 42, 0.04);
    }
    .continue-card .cc-action:active { transform: scale(0.98); }
    .continue-card .cc-action:focus-visible {
      outline: 2px solid rgba(13, 148, 136, 0.35);
      outline-offset: 2px;
    }

    /* --- 3) Quick Action Cards ----------------------------------------- */
    .qa-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin: 2px 0 4px 0;
    }
    @media (min-width: 720px) {
      .qa-grid { grid-template-columns: repeat(4, 1fr); }
    }
    .qa-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 16px 16px 14px 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid var(--border-subtle);
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.02),
        0 6px 16px rgba(15, 23, 42, 0.04);
      text-decoration: none !important;
      color: inherit !important;
      transition:
        transform 0.18s var(--ease-out),
        box-shadow 0.18s ease,
        border-color 0.2s ease,
        background 0.2s ease;
      min-height: 104px;
    }
    .qa-card:hover {
      transform: translateY(-2px);
      border-color: rgba(13, 148, 136, 0.22);
      background: rgba(255, 255, 255, 0.92);
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.04),
        0 12px 24px rgba(15, 23, 42, 0.06);
    }
    .qa-card:active { transform: scale(0.98); }
    .qa-card:focus-visible {
      outline: 2px solid rgba(13, 148, 136, 0.35);
      outline-offset: 2px;
    }
    .qa-card .qa-ico {
      width: 36px;
      height: 36px;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(13, 148, 136, 0.10);
      color: var(--mint);
      margin-bottom: 2px;
    }
    .qa-card .qa-ico svg {
      width: 20px;
      height: 20px;
      stroke-width: 2;
    }
    .qa-card .qa-title {
      font-size: 0.97rem;
      font-weight: 700;
      color: var(--navy);
      letter-spacing: -0.01em;
      line-height: 1.25;
    }
    .qa-card .qa-sub {
      font-size: 0.78rem;
      color: var(--text-muted);
      line-height: 1.4;
    }

    /* --- 4) Simple Learning Stats -------------------------------------- */
    .stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin: 2px 0 4px 0;
    }
    @media (max-width: 380px) {
      .stats-row { grid-template-columns: 1fr 1fr; }
      .stats-row .stat-chip:nth-child(3) { grid-column: span 2; }
    }
    .stat-chip {
      padding: 14px 14px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid var(--border-subtle);
      box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02);
      text-align: left;
    }
    .stat-chip .st-label {
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
    }
    .stat-chip .st-value {
      margin-top: 4px;
      font-size: 1.4rem;
      font-weight: 800;
      color: var(--navy);
      letter-spacing: -0.025em;
      line-height: 1.15;
    }
    .stat-chip .st-value--time {
      /* Time strings ("2시간 전") are multi-word — keep them readable. */
      font-size: 1.05rem;
      line-height: 1.3;
    }
    .stat-chip .st-hint {
      font-size: 0.72rem;
      color: var(--text-soft);
      margin-top: 2px;
    }

    /* ==================================================================
     * Mock-exam recovery card — soft amber panel surfaced when Gemini
     * analysis has failed and the user can safely retry the same question.
     * ================================================================== */
    .recovery-card {
      position: relative;
      padding: 20px 22px 18px 22px;
      border-radius: 20px;
      background:
        linear-gradient(135deg, rgba(245, 158, 11, 0.10) 0%, rgba(255, 255, 255, 0.6) 100%),
        linear-gradient(180deg, #fffbeb 0%, #fefce8 100%);
      border: 1px solid rgba(245, 158, 11, 0.28);
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.03),
        0 10px 28px rgba(245, 158, 11, 0.10);
      margin: 6px 0 16px 0;
      overflow: hidden;
    }
    .recovery-card::after {
      content: "";
      position: absolute;
      top: -34px;
      right: -30px;
      width: 150px;
      height: 150px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(245, 158, 11, 0.18) 0%, transparent 65%);
      pointer-events: none;
    }
    .recovery-card .rv-eyebrow {
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #b45309;
      position: relative;
      z-index: 1;
    }
    .recovery-card .rv-title {
      margin-top: 8px;
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--navy);
      letter-spacing: -0.015em;
      line-height: 1.35;
      position: relative;
      z-index: 1;
    }
    .recovery-card .rv-body {
      margin-top: 8px;
      font-size: 0.92rem;
      color: var(--text-secondary);
      line-height: 1.55;
      position: relative;
      z-index: 1;
    }
    .recovery-card .rv-meta {
      margin-top: 12px;
      font-size: 0.76rem;
      color: var(--text-muted);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px 6px;
      position: relative;
      z-index: 1;
    }
    .recovery-card .rv-meta .rv-sep {
      color: var(--text-soft);
    }

    /* ------------------------------------------------------------------
     * Smart feedback cards — grammar fix + alternative expressions
     * ------------------------------------------------------------------ */
    .grammar-fix,
    .coach-gf-card {
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 12px 14px;
      margin: 6px 0;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
    }
    .grammar-fix .gf-line {
      display: flex;
      gap: 8px;
      align-items: baseline;
      font-size: 0.95rem;
      line-height: 1.45;
    }
    .grammar-fix .gf-mark {
      flex: 0 0 auto;
      font-size: 0.95rem;
    }
    .grammar-fix .gf-text {
      color: var(--text);
      font-weight: 500;
    }
    .grammar-fix .gf-bad-line .gf-text {
      color: #a16207;
      text-decoration: line-through;
      text-decoration-color: rgba(161, 98, 7, 0.35);
    }
    .grammar-fix .gf-good {
      color: var(--mint);
    }
    .grammar-fix .gf-good-line .gf-text.gf-good {
      color: var(--mint);
      font-weight: 700;
    }
    .grammar-fix .gf-note {
      margin-top: 4px;
      font-size: 0.78rem;
      color: var(--text-muted);
      line-height: 1.5;
    }

    .alt-card,
    .coach-alt-card {
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 12px 14px;
      margin: 6px 0;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
    }
    .alt-card .alt-header {
      font-size: 0.95rem;
      color: var(--navy);
      margin-bottom: 6px;
    }
    .alt-card .alt-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 6px 0 4px 0;
    }
    .alt-card .alt-chip {
      display: inline-block;
      font-size: 0.82rem;
      font-weight: 600;
      letter-spacing: -0.005em;
      color: var(--mint);
      background: var(--mint-muted);
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid rgba(13, 148, 136, 0.18);
    }
    .alt-card .alt-note {
      margin-top: 4px;
      font-size: 0.78rem;
      color: var(--text-muted);
      line-height: 1.5;
    }

    .recent-list {
      border-radius: var(--radius-md);
      border: 1px solid var(--border-subtle);
      background: rgba(255,255,255,0.5);
      overflow: hidden;
    }
    .recent-row {
      padding: 14px var(--space-2);
      border-bottom: 1px solid var(--border-subtle);
      font-size: 0.9rem;
      color: var(--text-secondary);
    }
    .recent-row:last-child { border-bottom: none; }
    .recent-empty { padding: var(--space-3); color: var(--text-muted); font-size: 0.9rem; text-align: center; }

    /* Lectures layout */
    .lecture-layout { margin-top: var(--space-2); }
    .lecture-scroll {
      max-height: min(520px, 70vh);
      overflow-y: auto;
      padding-right: var(--space-2);
      scrollbar-width: thin;
    }
    .lecture-curriculum-head {
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: var(--space-2);
    }
    .lecture-row {
      display: flex;
      gap: 12px;
      align-items: flex-start;
      padding: 12px 14px;
      border-radius: var(--radius-sm);
      border: 1px solid transparent;
      margin-bottom: 6px;
      transition: background 0.18s ease, border-color 0.18s ease;
    }
    .lecture-row:hover {
      background: rgba(13, 148, 136, 0.06);
      border-color: rgba(13, 148, 136, 0.12);
    }
    .lecture-idx {
      flex-shrink: 0;
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--mint);
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--mint-muted);
      border-radius: 8px;
    }
    .lecture-title { font-size: 0.88rem; color: var(--navy); font-weight: 500; line-height: 1.45; }
    .lecture-aside {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: var(--space-3);
      padding: var(--space-2);
      border-radius: var(--radius-sm);
      background: rgba(15, 23, 42, 0.03);
      border: 1px solid var(--border-subtle);
    }

    /* ==================================================================
     * Floating bottom navigation — premium pill dock
     * ==================================================================
     * Visual-only refresh (Step 1).
     * Same DOM and same anchor hrefs — only the look-and-feel changes.
     * Designed to feel calmer and more app-like (Duolingo / Quizlet /
     * Headspace inspired) without any structural changes.
     */
    /* Fixed bottom tab bar — CSS flex row only (no Streamlit columns) */
    .opic-bottom-nav {
      position: fixed;
      left: 50%;
      transform: translateX(-50%);
      bottom: max(14px, env(safe-area-inset-bottom, 14px));
      width: min(100%, 560px);
      max-width: calc(100vw - 16px);
      z-index: 10000;
      display: flex;
      flex-direction: row;
      flex-wrap: nowrap;
      align-items: stretch;
      justify-content: space-between;
      gap: 2px;
      padding: 8px 10px;
      box-sizing: border-box;
      background: linear-gradient(180deg,
        rgba(255, 255, 255, 0.95) 0%,
        rgba(255, 255, 255, 0.86) 100%);
      backdrop-filter: saturate(180%) blur(24px);
      -webkit-backdrop-filter: saturate(180%) blur(24px);
      border: 1px solid rgba(255, 255, 255, 0.75);
      border-radius: 28px;
      box-shadow:
        0 1px 2px rgba(15, 23, 42, 0.06),
        0 8px 28px rgba(15, 23, 42, 0.10),
        0 1px 0 rgba(255, 255, 255, 0.95) inset,
        0 -1px 0 rgba(15, 23, 42, 0.02) inset;
    }
    a.opic-bottom-nav__item {
      flex: 1 1 0;
      min-width: 0;
      max-width: none;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 3px;
      padding: 8px 2px 7px 2px;
      min-height: 56px;
      border: none;
      border-radius: 18px;
      background: transparent;
      cursor: pointer;
      font-family: inherit;
      color: var(--text-soft);
      font-size: 0.58rem;
      font-weight: 600;
      letter-spacing: 0.01em;
      text-align: center;
      text-decoration: none !important;
      box-sizing: border-box;
      transition:
        color 0.18s ease,
        background-color 0.22s ease,
        transform 0.12s ease;
    }
    a.opic-bottom-nav__item:hover {
      color: var(--text);
      background: rgba(15, 23, 42, 0.035);
    }
    .opic-bottom-nav__item--active {
      color: #0f766e;
      background: #e6fffa;
      box-shadow: 0 1px 0 rgba(13, 148, 136, 0.10) inset;
    }
    .opic-bottom-nav__ico {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 22px;
      height: 22px;
      flex-shrink: 0;
      color: inherit;
    }
    .opic-bottom-nav__ico svg {
      width: 20px;
      height: 20px;
      stroke-width: 1.9;
    }
    .opic-bottom-nav__item--active .opic-bottom-nav__ico svg {
      stroke-width: 2.2;
    }
    .opic-bottom-nav__label {
      display: block;
      line-height: 1.15;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    a.opic-bottom-nav__item:focus-visible {
      outline: 2px solid rgba(13, 148, 136, 0.35);
      outline-offset: 2px;
    }
    a.opic-bottom-nav__item:active {
      transform: scale(0.96);
    }
    @media (max-width: 360px) {
      .opic-bottom-nav { padding: 6px 4px; border-radius: 24px; }
      a.opic-bottom-nav__item { font-size: 0.52rem; padding: 8px 1px 6px 1px; }
      .opic-bottom-nav__ico svg { width: 18px; height: 18px; }
    }
    @media (prefers-reduced-motion: reduce) {
      a.opic-bottom-nav__item,
      .opic-bottom-nav__ico { transition: none !important; }
      a.opic-bottom-nav__item:active { transform: none !important; }
    }
    /* Nav is position:fixed — do not reserve vertical space in the page flow */
    section.main [data-testid="stMarkdown"]:has(.opic-bottom-nav),
    section.main .stMarkdown:has(.opic-bottom-nav) {
      height: 0 !important;
      min-height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      overflow: visible !important;
    }

    .topbar--inline .tb-titleblock { text-align: center; }

    @keyframes dsFadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes dockFadeUp {
      from { opacity: 0; transform: translateY(14px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 640px) {
      [data-testid="stTabs"] [role="tablist"] { overflow-x: auto; flex-wrap: nowrap; }
    }

    /* Streamlit widgets — calmer defaults */
    .stButton > button {
      border-radius: var(--radius-md) !important;
      font-weight: 600 !important;
      border: 1px solid var(--border-subtle) !important;
      background: rgba(255,255,255,0.9) !important;
      color: var(--navy) !important;
      transition: transform 0.15s ease, box-shadow 0.2s ease !important;
    }
    .stButton > button:hover {
      border-color: rgba(13, 148, 136, 0.35) !important;
      box-shadow: 0 4px 16px rgba(13, 148, 136, 0.12) !important;
    }

    [data-testid="stTabs"] button[data-baseweb="tab"] {
      font-weight: 600 !important;
      letter-spacing: -0.01em;
    }

    .survey-label { font-size: 1.05rem; font-weight: 600; color: var(--navy); margin-top: var(--space-3); }

    .wave {
      display: flex;
      gap: 4px;
      align-items: flex-end;
      height: 42px;
      margin: var(--space-2) 0;
    }
    .wave span {
      display: block;
      width: 5px;
      border-radius: 999px;
      background: var(--mint);
      animation: wave 1.1s infinite ease-in-out;
    }
    .wave span:nth-child(2){animation-delay:.1s}.wave span:nth-child(3){animation-delay:.2s}
    .wave span:nth-child(4){animation-delay:.3s}.wave span:nth-child(5){animation-delay:.4s}
    .wave span:nth-child(6){animation-delay:.5s}.wave span:nth-child(7){animation-delay:.6s}
    @keyframes wave {0%,100%{height:8px;opacity:.55}50%{height:38px;opacity:1}}

    .focus-shell { background: rgba(15, 23, 42, 0.55); border-radius: var(--radius-lg); padding: var(--space-2); }

    /* ==================================================================
     * Pattern screen (UI redesign step 3) — premium mobile learning UX.
     *
     * Scoped under ``.pat-screen`` so Streamlit overrides (st.tabs,
     * st.expander, st.button) never leak to the rest of the app. The
     * pattern-specific classes (.pat-card, .pat-en, …) are namespaced
     * by prefix and unique to this view.
     * ================================================================== */

    .pat-screen {
      max-width: 720px;
      margin: 0 auto;
      padding: 0 4px;
      overflow-x: hidden;
      box-sizing: border-box;
    }
    .pat-screen [data-testid="column"],
    .pat-screen [data-testid="stHorizontalBlock"] {
      max-width: 100%;
    }

    /* --- Hero (greeting + subtitle) ----------------------------------- */
    .pat-hero {
      background: linear-gradient(140deg, rgba(204, 251, 241, 0.55) 0%, rgba(255, 255, 255, 0.9) 60%);
      border: 1px solid rgba(13, 148, 136, 0.14);
      border-radius: var(--radius-lg);
      padding: 18px 20px;
      margin: 4px 0 16px;
      box-shadow: var(--shadow-card);
    }
    .pat-hero .pat-eyebrow {
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0;
    }
    .pat-hero .pat-title {
      font-size: 1.6rem;
      font-weight: 800;
      color: var(--navy);
      letter-spacing: -0.025em;
      line-height: 1.15;
      margin: 6px 0 6px 0;
    }
    .pat-hero .pat-sub {
      font-size: 0.85rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 0;
    }

    /* --- Pattern tab pills (session-state buttons, not st.tabs) -------- */
    .pat-screen .pat-tab-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 0 0 14px 0;
      padding: 4px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid var(--border-subtle);
      border-radius: 999px;
      box-shadow: var(--shadow-card);
    }
    .pat-screen .pat-tab-row [data-testid="column"] {
      flex: 0 0 auto;
      min-width: 0;
    }
    .pat-screen .pat-tab-row .stButton > button {
      border-radius: 999px !important;
      font-weight: 600 !important;
      font-size: 0.88rem !important;
      min-height: 36px !important;
      padding: 8px 14px !important;
      white-space: nowrap;
    }
    .pat-screen .pat-tab-row .stButton > button[kind="secondary"] {
      color: var(--text-secondary) !important;
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
    }
    .pat-screen .pat-tab-row .stButton > button[kind="primary"] {
      color: #ffffff !important;
      background: linear-gradient(135deg, #14b8a6 0%, var(--mint) 100%) !important;
      border: none !important;
      box-shadow: 0 6px 16px rgba(13, 148, 136, 0.25);
    }

    /* --- Streamlit tab bar (legacy st.tabs fallback) ------------------- */
    .pat-screen [data-testid="stTabs"] [role="tablist"] {
      gap: 6px;
      padding: 4px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid var(--border-subtle);
      border-radius: 999px;
      box-shadow: var(--shadow-card);
      overflow-x: auto;
      flex-wrap: nowrap;
      scrollbar-width: none;
    }
    .pat-screen [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {
      display: none;
    }
    .pat-screen [data-testid="stTabs"] button[data-baseweb="tab"] {
      flex: 0 0 auto;
      padding: 8px 16px !important;
      border-radius: 999px !important;
      font-weight: 600 !important;
      font-size: 0.88rem !important;
      color: var(--text-secondary) !important;
      background: transparent !important;
      border: none !important;
      transition: background 0.18s var(--ease-out), color 0.18s var(--ease-out);
      min-height: auto !important;
    }
    .pat-screen [data-testid="stTabs"] button[data-baseweb="tab"]:hover {
      color: var(--mint) !important;
      background: rgba(13, 148, 136, 0.06) !important;
    }
    .pat-screen [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
      color: #ffffff !important;
      background: linear-gradient(135deg, #14b8a6 0%, var(--mint) 100%) !important;
      box-shadow: 0 6px 16px rgba(13, 148, 136, 0.25);
    }
    /* Kill the default Streamlit bottom underline / highlight bar. */
    .pat-screen [data-testid="stTabs"] [data-baseweb="tab-highlight"],
    .pat-screen [data-testid="stTabs"] [data-baseweb="tab-border"] {
      display: none !important;
    }
    .pat-screen [data-testid="stTabs"] [data-baseweb="tab-list"] {
      border-bottom: none !important;
    }
    .pat-screen [data-testid="stTabs"] [role="tabpanel"] {
      padding-top: 18px;
    }

    /* --- Section accordion (st.expander) ------------------------------ */
    /* Each category section is rendered with st.expander. We restyle the
     * details/summary so the section feels like a soft category card
     * instead of Streamlit's default chevron-with-border. */
    .pat-screen div[data-testid="stExpander"] {
      margin: 0 0 10px 0;
    }
    .pat-screen div[data-testid="stExpander"] details {
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md) !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
      transition: box-shadow 0.2s var(--ease-out), border-color 0.2s var(--ease-out);
    }
    .pat-screen div[data-testid="stExpander"] details[open] {
      border-color: rgba(13, 148, 136, 0.22);
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }
    .pat-screen div[data-testid="stExpander"] summary {
      padding: 12px 14px !important;
      font-weight: 600 !important;
      font-size: 0.95rem !important;
      color: var(--navy) !important;
      letter-spacing: -0.005em;
      border-radius: var(--radius-md) !important;
    }
    .pat-screen div[data-testid="stExpander"] summary:hover {
      background: rgba(13, 148, 136, 0.04) !important;
    }
    .pat-screen div[data-testid="stExpander"] details[open] summary {
      border-bottom: 1px solid var(--border-subtle);
      border-bottom-left-radius: 0 !important;
      border-bottom-right-radius: 0 !important;
    }
    .pat-screen div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
      padding: 12px 14px 4px 14px !important;
    }

    /* --- Pattern detail stack (UI redesign step 5) -------------------- */
    .pat-detail-hero {
      position: relative;
      background: linear-gradient(155deg, rgba(13, 148, 136, 0.12) 0%, rgba(255, 255, 255, 0.96) 55%, rgba(204, 251, 241, 0.35) 100%);
      border: 1px solid rgba(13, 148, 136, 0.2);
      border-radius: var(--radius-lg);
      padding: 20px 18px 18px 20px;
      margin: 0 0 14px 0;
      box-shadow: 0 10px 32px rgba(15, 23, 42, 0.07);
      overflow: hidden;
    }
    .pat-detail-hero::after {
      content: "";
      position: absolute;
      right: -24px; top: -24px;
      width: 120px; height: 120px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(45, 212, 191, 0.18) 0%, transparent 70%);
      pointer-events: none;
    }
    .pat-detail-eyebrow {
      font-size: 0.68rem;
      font-weight: 800;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0 0 6px 0;
    }
    .pat-detail-pattern {
      font-size: 1.22rem;
      font-weight: 800;
      color: var(--navy);
      line-height: 1.35;
      letter-spacing: -0.02em;
      margin: 0 0 8px 0;
    }
    .pat-detail-meaning {
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text);
      line-height: 1.5;
      margin: 0 0 10px 0;
    }
    .pat-detail-usage {
      font-size: 0.8rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 0;
    }
    .pat-detail-usage .pat-usage-meta {
      color: var(--mint);
      font-weight: 600;
    }

    .pat-learn-card {
      background: #ffffff;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 14px 16px 14px 16px;
      margin: 0 0 10px 0;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    .pat-learn-eyebrow {
      font-size: 0.62rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(13, 148, 136, 0.75);
      margin: 0 0 4px 0;
    }
    .pat-learn-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--navy);
      margin: 0 0 8px 0;
      letter-spacing: -0.02em;
    }
    .pat-learn-body { margin: 0; }
    .pat-learn-en {
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--navy);
      line-height: 1.55;
      margin: 0;
    }
    .pat-learn-en--long {
      font-weight: 500;
      font-size: 0.88rem;
      line-height: 1.6;
    }
    .pat-learn-ko {
      font-size: 0.78rem;
      color: var(--text-secondary);
      line-height: 1.5;
      margin: 8px 0 0 0;
    }
    .pat-learn-tip {
      font-size: 0.82rem;
      color: var(--text-secondary);
      line-height: 1.6;
      margin: 0;
    }
    .pat-learn-ih-hint {
      font-size: 0.8rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 10px 0 0 0;
    }

    .pat-learn-card--short {
      border-left: 3px solid rgba(13, 148, 136, 0.45);
    }
    .pat-learn-card--opic {
      background: linear-gradient(180deg, rgba(248, 250, 252, 0.9) 0%, #ffffff 100%);
      border-color: rgba(15, 23, 42, 0.06);
    }
    .pat-learn-card--ih {
      background: linear-gradient(125deg, rgba(204, 251, 241, 0.55) 0%, rgba(255, 255, 255, 0.98) 100%);
      border: 1px solid rgba(13, 148, 136, 0.28);
      box-shadow: 0 4px 16px rgba(13, 148, 136, 0.1);
    }
    .pat-learn-card--tip {
      background: rgba(255, 251, 235, 0.65);
      border-color: rgba(251, 191, 36, 0.25);
    }

    .pat-practice-shell {
      margin: 4px 0 6px 0;
      padding: 14px 16px 4px 16px;
      background: rgba(15, 23, 42, 0.03);
      border: 1px dashed rgba(13, 148, 136, 0.35);
      border-radius: var(--radius-md);
    }
    .pat-practice-eyebrow {
      font-size: 0.62rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0 0 4px 0;
    }
    .pat-practice-title {
      font-size: 1rem;
      font-weight: 700;
      color: var(--navy);
      margin: 0 0 0 0;
    }
    .pat-screen div[data-testid="stTextArea"] textarea {
      border-radius: var(--radius-sm) !important;
      border-color: rgba(13, 148, 136, 0.22) !important;
      font-size: 0.88rem !important;
    }

    .pat-ex-wrap--tail {
      margin-top: 8px;
    }

    /* --- Pattern card (legacy compact; step 5 uses pat-detail-hero) --- */
    .pat-screen .pat-card {
      position: relative;
      background: #ffffff;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 14px 14px 14px 18px;
      margin: 0 0 10px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
      transition: box-shadow 0.18s var(--ease-out), transform 0.18s var(--ease-out);
    }
    .pat-screen .pat-card::before {
      content: "";
      position: absolute;
      left: 0; top: 14px; bottom: 14px;
      width: 3px;
      border-radius: 3px;
      background: linear-gradient(180deg, var(--mint) 0%, rgba(13, 148, 136, 0.4) 100%);
      opacity: 0.85;
    }
    .pat-screen .pat-card:hover {
      box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
      transform: translateY(-1px);
    }
    .pat-screen .pat-en {
      font-size: 0.98rem;
      font-weight: 600;
      color: var(--navy);
      line-height: 1.4;
      letter-spacing: -0.005em;
    }
    .pat-screen .pat-ko {
      font-size: 0.82rem;
      color: var(--text-secondary);
      line-height: 1.5;
      margin-top: 4px;
    }

    /* --- Examples block ---------------------------------------------- */
    .pat-screen .pat-ex-wrap {
      margin: 10px 0 0 0;
      padding: 10px 12px;
      background: rgba(248, 250, 252, 0.85);
      border: 1px solid rgba(15, 23, 42, 0.04);
      border-radius: var(--radius-sm);
    }
    .pat-screen .pat-ex-label {
      display: inline-block;
      font-size: 0.66rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--mint);
      margin-bottom: 4px;
    }
    .pat-screen .pat-ex-wrap ul {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .pat-screen .pat-ex-wrap li {
      position: relative;
      padding: 4px 0 4px 14px;
      font-size: 0.84rem;
      line-height: 1.55;
      color: var(--text);
    }
    .pat-screen .pat-ex-wrap li::before {
      content: "";
      position: absolute;
      left: 0; top: 13px;
      width: 5px; height: 5px;
      border-radius: 999px;
      background: var(--mint);
      opacity: 0.55;
    }
    .pat-screen .pat-ex-wrap--extra {
      margin-top: 6px;
      background: rgba(204, 251, 241, 0.32);
      border-color: rgba(13, 148, 136, 0.14);
    }

    /* --- "예문 더보기 / 접기" toggle button -------------------------- */
    .pat-screen .stButton > button {
      margin-top: 8px !important;
      min-height: 1.9rem !important;
      padding: 4px 14px !important;
      border-radius: 999px !important;
      font-size: 0.78rem !important;
      font-weight: 600 !important;
      color: var(--mint) !important;
      background: rgba(204, 251, 241, 0.55) !important;
      border: 1px solid rgba(13, 148, 136, 0.25) !important;
      box-shadow: none !important;
    }
    .pat-screen .stButton > button:hover {
      background: rgba(204, 251, 241, 0.9) !important;
      border-color: var(--mint) !important;
    }

    /* --- Mobile tweaks ----------------------------------------------- */
    @media (max-width: 480px) {
      .pat-screen .pat-hero { padding: 16px 16px; }
      .pat-screen .pat-hero .pat-title { font-size: 1.4rem; }
      .pat-screen .pat-card { padding: 12px 12px 12px 16px; }
      .pat-screen .pat-detail-hero { padding: 16px 14px; }
      .pat-screen .pat-detail-pattern { font-size: 1.08rem; }
      .pat-screen .pat-learn-card { padding: 12px 14px; }
      .pat-screen [data-testid="stTabs"] button[data-baseweb="tab"] {
        padding: 7px 13px !important;
        font-size: 0.82rem !important;
      }
    }

    /* --- Topic practice: selection screen (filters + compact cards) ----- */
    .tp-select-intro {
      margin-bottom: 4px;
    }
    .tp-select-summary {
      margin: 10px 0 0 0;
      font-size: 0.84rem;
      font-weight: 600;
      color: var(--text-muted);
      letter-spacing: -0.01em;
    }
    .tp-select-visible {
      margin: 0 0 10px 0;
      font-size: 0.8rem;
      color: var(--text-secondary);
    }
    .tp-select-visible b {
      color: var(--mint);
      font-weight: 700;
    }
    .tp-filter-label {
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin: 12px 0 6px 0;
    }
    .tp-topic-card {
      background: #ffffff;
      border: 1px solid rgba(17, 24, 39, 0.08);
      border-radius: var(--radius-md);
      padding: 12px 14px 10px 14px;
      margin: 0 0 6px 0;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    .tp-topic-title {
      font-size: 1.02rem;
      font-weight: 700;
      color: var(--navy);
      letter-spacing: -0.02em;
      margin: 0 0 4px 0;
      line-height: 1.3;
    }
    .tp-topic-sub {
      margin: 0 0 6px 0;
      font-size: 0.82rem;
      line-height: 1.45;
      color: var(--text-secondary);
    }
    .tp-topic-meta {
      margin: 0;
      font-size: 0.74rem;
      font-weight: 600;
      color: var(--mint);
      letter-spacing: -0.01em;
    }
    section.main:has(.mx-landing-marker) div[data-testid="column"] {
      min-width: 0;
    }
    @media (max-width: 640px) {
      section.main:has(.mx-landing-marker) div[data-testid="column"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
      }
    }

    /* ==================================================================
     * Mock exam screen (UI redesign step 4) — premium speaking studio.
     *
     * Strategy: ``.mx-*`` custom HTML uses unique class names so it
     * never collides with anything else; the Streamlit-widget overrides
     * (st.button, st.progress, st.expander) are scoped via
     * ``section.main:has(.mx-marker)`` so they only activate while the
     * mock-exam view has placed its marker in the DOM. This keeps the
     * design intentional even though the audio recorder and TTS player
     * render inside iframes we cannot style directly.
     * ================================================================== */

    /* --- Top progress strip ------------------------------------------ */
    .mx-progress {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 4px 0 14px 0;
    }
    .mx-progress-meta {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .mx-progress-eyebrow {
      font-size: 0.66rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
    }
    .mx-progress-count {
      font-size: 1.1rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: var(--navy);
    }
    .mx-progress-count .mx-progress-of {
      color: var(--text-soft);
      font-weight: 700;
    }
    .mx-progress-chip {
      align-self: center;
      padding: 4px 12px;
      border-radius: 999px;
      background: var(--mint-muted);
      color: var(--mint);
      font-size: 0.74rem;
      font-weight: 600;
      letter-spacing: -0.005em;
      max-width: 56vw;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .mx-progress-bar {
      height: 6px;
      width: 100%;
      background: rgba(15, 23, 42, 0.06);
      border-radius: 999px;
      overflow: hidden;
      margin: 0 0 18px 0;
    }
    .mx-progress-fill {
      display: block;
      height: 100%;
      background: linear-gradient(90deg, #14b8a6 0%, var(--mint) 100%);
      border-radius: 999px;
      transition: width 0.35s var(--ease-out);
    }

    /* --- Question card ----------------------------------------------- */
    .mx-question-card {
      background: #ffffff;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 22px 22px;
      margin: 0 0 18px 0;
      box-shadow: var(--shadow-card);
    }
    .mx-question-type {
      display: inline-block;
      padding: 3px 10px;
      border-radius: 999px;
      background: rgba(13, 148, 136, 0.08);
      color: var(--mint);
      font-size: 0.66rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }
    .mx-question-topic {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--navy);
      letter-spacing: -0.015em;
      margin: 10px 0 6px 0;
      line-height: 1.35;
    }
    .mx-question-hint {
      font-size: 0.82rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 0;
    }
    .mx-question-hint strong {
      color: var(--navy);
      font-weight: 600;
    }

    /* --- Listen stage (TTS player wrapper) --------------------------- */
    .mx-listen-stage {
      background: rgba(248, 250, 252, 0.85);
      border: 1px solid rgba(15, 23, 42, 0.04);
      border-radius: var(--radius-md);
      padding: 14px 14px 6px 14px;
      margin: 0 0 16px 0;
    }
    .mx-stage-eyebrow {
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 8px;
      display: block;
    }
    .mx-listen-stage .mx-stage-eyebrow { color: var(--mint); }
    .mx-listen-prep {
      font-size: 0.84rem;
      line-height: 1.55;
      color: var(--text-secondary);
      margin: 0 0 10px 0;
    }
    .mx-listen-ready-label {
      font-size: 0.88rem;
      font-weight: 600;
      color: #0f766e;
      margin: 0 0 8px 0;
    }

    /* --- Record stage (the screen's emotional center) ---------------- */
    .mx-record-stage {
      position: relative;
      background: linear-gradient(160deg, #0f172a 0%, #134e4a 55%, #0d9488 130%);
      border-radius: var(--radius-lg);
      padding: 24px 22px 18px 22px;
      margin: 0 0 18px 0;
      color: #ffffff !important;
      box-shadow: 0 14px 36px rgba(13, 148, 136, 0.18), 0 2px 8px rgba(15, 23, 42, 0.18);
      overflow: hidden;
    }
    /* Dark studio panel: always light text (never inherit page dark text). */
    .mx-record-stage,
    .mx-record-stage p,
    .mx-record-stage div,
    .mx-record-stage span,
    .mx-record-stage strong,
    .mx-record-stage b {
      color: #ffffff !important;
    }
    .mx-record-stage::before {
      /* Soft glowing orb behind the recorder to give the dark panel a
       * sense of life without animating anything expensive. */
      content: "";
      position: absolute;
      top: -40px; right: -30px;
      width: 180px; height: 180px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(204, 251, 241, 0.28) 0%, transparent 70%);
      pointer-events: none;
    }
    .mx-record-eyebrow {
      font-size: 0.66rem;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: rgba(204, 251, 241, 0.9) !important;
      margin: 0;
    }
    .mx-record-title {
      font-size: 1.15rem;
      font-weight: 700;
      margin: 6px 0 6px 0;
      color: #ffffff !important;
      letter-spacing: -0.015em;
    }
    .mx-record-hint {
      font-size: 0.84rem;
      line-height: 1.55;
      color: rgba(255, 255, 255, 0.88) !important;
      margin: 0 0 14px 0;
    }
    .mx-record-saved {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-top: 12px;
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(204, 251, 241, 0.18);
      border: 1px solid rgba(204, 251, 241, 0.25);
      color: #d1fae5 !important;
      font-size: 0.78rem;
      font-weight: 600;
      letter-spacing: -0.005em;
    }
    .mx-record-saved::before {
      content: "";
      display: block;
      width: 7px; height: 7px;
      border-radius: 50%;
      background: #34d399;
      box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.25);
    }
    .mx-record-empty {
      margin-top: 12px;
      padding: 10px 14px;
      border-radius: var(--radius-sm);
      background: rgba(255, 255, 255, 0.07);
      border: 1px dashed rgba(204, 251, 241, 0.28);
      font-size: 0.82rem;
      color: rgba(255, 255, 255, 0.88) !important;
      line-height: 1.5;
    }

    /* --- Status banners (info / warn / error inside the mock screen) - */
    .mx-status {
      padding: 12px 14px;
      border-radius: var(--radius-md);
      margin: 0 0 14px 0;
      font-size: 0.86rem;
      line-height: 1.55;
      border: 1px solid transparent;
      display: flex;
      align-items: flex-start;
      gap: 10px;
    }
    .mx-status-icon { font-size: 1rem; line-height: 1.2; }
    .mx-status--info {
      background: rgba(204, 251, 241, 0.45);
      border-color: rgba(13, 148, 136, 0.18);
      color: #0f5f57;
    }
    .mx-status--warn {
      background: rgba(254, 243, 199, 0.6);
      border-color: rgba(202, 138, 4, 0.22);
      color: #78350f;
    }
    .mx-status--error {
      background: rgba(254, 226, 226, 0.55);
      border-color: rgba(220, 38, 38, 0.22);
      color: #7f1d1d;
    }

    /* --- Streamlit widget overrides (scoped via :has) ----------------- *
     * These rules only activate when the mock view places its marker
     * in the DOM. Other pages stay untouched.
     * ----------------------------------------------------------------- */

    /* Hide Streamlit's default progress bar — we render our own ``.mx-progress-bar``. */
    section.main:has(.mx-marker) [data-testid="stProgress"],
    section.main:has(.mx-marker) [data-testid="stProgressBar"] {
      display: none !important;
    }

    /* Primary CTA ("AI 테라피 진단받기" / "다시 분석하기") — full-width
     * mint pill with confident lift. Streamlit decorates the disabled
     * state automatically; we keep its opacity logic but soften the
     * background so the disabled state doesn't look broken. */
    section.main:has(.mx-marker) .stButton > button {
      min-height: 3rem !important;
      padding: 0.65rem 1.2rem !important;
      border-radius: 14px !important;
      font-size: 0.95rem !important;
      font-weight: 700 !important;
      letter-spacing: -0.005em;
      border: 1px solid var(--border-subtle) !important;
      background: rgba(255, 255, 255, 0.92) !important;
      color: var(--navy) !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
      transition: transform 0.16s var(--ease-out), box-shadow 0.2s var(--ease-out),
                  background 0.2s var(--ease-out) !important;
    }
    section.main:has(.mx-marker) .stButton > button:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 8px 20px rgba(13, 148, 136, 0.18) !important;
      border-color: rgba(13, 148, 136, 0.35) !important;
    }
    section.main:has(.mx-marker) .stButton > button[kind="primary"] {
      background: linear-gradient(135deg, #14b8a6 0%, var(--mint) 100%) !important;
      color: #ffffff !important;
      border-color: transparent !important;
      box-shadow: 0 10px 24px rgba(13, 148, 136, 0.28) !important;
    }
    section.main:has(.mx-marker) .stButton > button[kind="primary"]:hover:not(:disabled) {
      box-shadow: 0 14px 32px rgba(13, 148, 136, 0.35) !important;
    }
    section.main:has(.mx-marker) .stButton > button:disabled {
      opacity: 0.55 !important;
      cursor: not-allowed !important;
      transform: none !important;
    }

    /* Per-question expander — match the pattern screen's card aesthetic. */
    section.main:has(.mx-marker) div[data-testid="stExpander"] {
      margin: 0 0 10px 0;
    }
    section.main:has(.mx-marker) div[data-testid="stExpander"] details {
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md) !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    section.main:has(.mx-marker) div[data-testid="stExpander"] details[open] {
      border-color: rgba(13, 148, 136, 0.22);
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }
    section.main:has(.mx-marker) div[data-testid="stExpander"] summary {
      padding: 12px 14px !important;
      font-weight: 600 !important;
      font-size: 0.92rem !important;
      color: var(--navy) !important;
    }

    /* Status widget (``st.status``) — used during analysis. Soften its
     * default look so it feels like a calm progress card, not an alert. */
    section.main:has(.mx-marker) [data-testid="stStatus"] {
      border-radius: var(--radius-md) !important;
      border: 1px solid var(--border-subtle) !important;
      background: rgba(255, 255, 255, 0.92) !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03) !important;
    }

    /* --- Report screen --------------------------------------------- */
    .mx-report-hero {
      background: linear-gradient(140deg, rgba(204, 251, 241, 0.5) 0%, rgba(255, 255, 255, 0.92) 65%);
      border: 1px solid rgba(13, 148, 136, 0.14);
      border-radius: var(--radius-lg);
      padding: 22px 22px;
      margin: 4px 0 18px 0;
      box-shadow: var(--shadow-card);
    }
    .mx-report-hero .mx-rh-eyebrow {
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0;
    }
    .mx-report-hero .mx-rh-title {
      font-size: 1.25rem;
      font-weight: 800;
      color: var(--navy);
      letter-spacing: -0.02em;
      margin: 6px 0 0 0;
      line-height: 1.3;
    }
    .mx-report-hero .mx-rh-transcript {
      margin-top: 14px;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.7);
      border-radius: var(--radius-sm);
      font-size: 0.88rem;
      color: var(--text);
      line-height: 1.6;
      border-left: 3px solid var(--mint);
    }
    .mx-report-hero .mx-rh-meta {
      margin-top: 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .mx-report-hero .mx-rh-chip {
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid var(--border-subtle);
      font-size: 0.74rem;
      font-weight: 600;
      color: var(--text-secondary);
    }

    /* --- Coaching experience (mock report, step 6) ------------------- */
    section.main:has(.mx-marker) .mx-coach-hero {
      background: linear-gradient(135deg, rgba(240, 253, 250, 0.95) 0%, rgba(255, 255, 255, 0.98) 55%, rgba(204, 251, 241, 0.45) 100%);
      border: 1px solid rgba(13, 148, 136, 0.18);
      border-radius: var(--radius-lg);
      padding: 20px 20px 18px 20px;
      margin: 0 0 14px 0;
      box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
    }
    section.main:has(.mx-marker) .mx-coach-eyebrow {
      font-size: 0.68rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0 0 6px 0;
    }
    section.main:has(.mx-marker) .mx-coach-hero-title {
      font-size: 1.28rem;
      font-weight: 800;
      color: var(--navy);
      letter-spacing: -0.025em;
      line-height: 1.3;
      margin: 0 0 8px 0;
    }
    section.main:has(.mx-marker) .mx-coach-hero-sub {
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.6;
      margin: 0;
    }
    section.main:has(.mx-marker) .mx-coach-section {
      margin: 18px 0 6px 0;
    }
    section.main:has(.mx-marker) .mx-coach-sec-eyebrow {
      font-size: 0.62rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(13, 148, 136, 0.75);
      margin: 0 0 4px 0;
    }
    section.main:has(.mx-marker) .mx-coach-sec-title {
      font-size: 1rem;
      font-weight: 700;
      color: var(--navy);
      margin: 0 0 10px 0;
      letter-spacing: -0.02em;
    }
    section.main:has(.mx-marker) .mx-coach-chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    section.main:has(.mx-marker) .mx-coach-chip {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 10px 12px;
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid rgba(13, 148, 136, 0.14);
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
      max-width: 100%;
    }
    section.main:has(.mx-marker) .mx-coach-chip-ico {
      flex: 0 0 auto;
      color: var(--mint);
      font-weight: 800;
      font-size: 0.85rem;
      line-height: 1.4;
    }
    section.main:has(.mx-marker) .mx-coach-chip-txt {
      font-size: 0.82rem;
      color: var(--text);
      line-height: 1.45;
    }
    section.main:has(.mx-marker) .mx-coach-native .mx-coach-sec-title {
      margin-bottom: 4px;
    }
    section.main:has(.mx-marker) .mx-coach-native-body {
      font-size: 0.88rem;
      line-height: 1.65;
      color: var(--text);
      padding: 14px 16px;
      border-radius: var(--radius-md);
      background: linear-gradient(125deg, rgba(224, 242, 254, 0.55) 0%, rgba(255, 255, 255, 0.95) 100%);
      border: 1px solid rgba(59, 130, 246, 0.15);
      margin: 0 0 4px 0;
    }
    section.main:has(.mx-marker) .mx-coach-flow-grid {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    section.main:has(.mx-marker) .mx-coach-flow-card {
      padding: 12px 14px;
      border-radius: var(--radius-md);
      background: rgba(248, 250, 252, 0.95);
      border: 1px solid var(--border-subtle);
    }
    section.main:has(.mx-marker) .mx-coach-flow-title {
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--mint);
      margin: 0 0 6px 0;
    }
    section.main:has(.mx-marker) .mx-coach-flow-body {
      font-size: 0.84rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 0;
    }
    section.main:has(.mx-marker) .mx-coach-cta-preamble {
      font-size: 0.9rem;
      color: var(--text-secondary);
      text-align: center;
      padding: 14px 12px 6px 12px;
      line-height: 1.55;
    }
    section.main:has(.mx-marker) .mx-coach-mini-scores {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin: 0 0 12px 0;
      font-size: 0.78rem;
      color: var(--text-secondary);
    }
    section.main:has(.mx-marker) .mx-coach-mini-pill {
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(204, 251, 241, 0.45);
      border: 1px solid rgba(13, 148, 136, 0.2);
      font-weight: 700;
      color: var(--navy);
    }
    section.main:has(.mx-marker) .mx-coach-mini-rest {
      font-weight: 500;
    }
    section.main:has(.mx-marker) .mx-coach-pron-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin: 12px 0 0 0;
    }
    section.main:has(.mx-marker) .mx-coach-pron-chip {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      border-radius: 12px;
      background: rgba(248, 250, 252, 0.9);
      border: 1px solid var(--border-subtle);
      font-size: 0.8rem;
    }
    section.main:has(.mx-marker) .mx-coach-pron-label {
      color: var(--text-secondary);
      font-weight: 500;
    }
    section.main:has(.mx-marker) .mx-coach-pron-score {
      font-weight: 700;
      font-size: 0.85rem;
    }
    section.main:has(.mx-marker) .mx-coach-pron-feedback {
      font-size: 0.86rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 12px 0 0 0;
      padding: 10px 12px;
      border-radius: 10px;
      background: rgba(241, 245, 249, 0.8);
      border-left: 3px solid rgba(13, 148, 136, 0.3);
    }

    section.main:has(.mx-marker) .mx-coach-retry-banner {
      margin: 20px 0 8px 0;
      padding: 16px 14px;
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(204, 251, 241, 0.55) 0%, rgba(236, 253, 245, 0.9) 100%);
      border: 1px solid rgba(13, 148, 136, 0.22);
      font-size: 0.92rem;
      line-height: 1.55;
      color: var(--text-primary);
      text-align: center;
      font-weight: 500;
    }

    .mx-section-h {
      font-size: 0.74rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin: 22px 0 10px 0;
    }

    /* --- Mobile tweaks ----------------------------------------------- */
    @media (max-width: 480px) {
      .mx-question-card { padding: 18px 16px; }
      .mx-question-topic { font-size: 1.05rem; }
      .mx-record-stage { padding: 20px 16px 14px 16px; }
      .mx-record-title { font-size: 1.05rem; }
      .mx-report-hero { padding: 18px 16px; }
      .mx-report-hero .mx-rh-title { font-size: 1.12rem; }
    }

    /* ==================================================================
     * Launch light-theme lock — readable UI when OS/browser prefers dark
     * ================================================================== */
    @media (prefers-color-scheme: dark) {
      html, body,
      [data-testid="stAppViewContainer"],
      .stApp,
      main,
      section.main,
      .block-container {
        background-color: #f8faf9 !important;
        color: #111827 !important;
        color-scheme: light only !important;
      }
      .mx-record-stage,
      .mx-record-stage * {
        color: #ffffff !important;
      }
      .mx-record-stage .mx-record-hint,
      .mx-record-stage .mx-record-empty,
      .mx-record-stage p {
        color: rgba(255, 255, 255, 0.88) !important;
      }
    }

    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] .main {
      color-scheme: light only !important;
    }

    /* Streamlit / BaseWeb form controls */
    input,
    textarea,
    select,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="select"] > div,
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] > div > div,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] > div,
    div[data-testid="stMultiSelect"] > div {
      background-color: #ffffff !important;
      color: #111827 !important;
      border-color: #d1d5db !important;
      -webkit-text-fill-color: #111827 !important;
    }

    input::placeholder,
    textarea::placeholder {
      color: #9ca3af !important;
      opacity: 1 !important;
      -webkit-text-fill-color: #9ca3af !important;
    }

    /* Custom cards — explicit light surfaces (mode / topic / home / recovery) */
    .continue-card,
    .continue-card--resume,
    .continue-card--start,
    .mx-mode-card,
    .mx-landing-card,
    .mx-question-card,
    .mx-report-hero,
    .recovery-card,
    .topbar,
    .section-card,
    .final-hero,
    .grammar-fix,
    .coach-gf-card,
    section.main:has(.mx-marker) .mx-coach-hero,
    section.main:has(.mx-marker) [data-testid="stStatus"] {
      color: #111827 !important;
    }

    .continue-card .cc-meta,
    .continue-card .cc-time,
    .ds-muted,
    .mx-report-hero .mx-rh-transcript,
    .recovery-card .rv-body,
    .recovery-card .rv-meta {
      color: #6b7280 !important;
    }

    .continue-card .cc-title,
    .continue-card .cc-eyebrow,
    .mx-mode-title,
    .mx-mode-subtitle,
    .mx-report-hero .mx-rh-title,
    .recovery-card .rv-title {
      color: #111827 !important;
    }

    .continue-card--resume,
    .continue-card--start,
    .mx-mode-card,
    .mx-landing-card {
      background: #ffffff !important;
      border: 1px solid rgba(17, 24, 39, 0.08) !important;
    }

    /* Bottom nav — stay light with readable inactive labels */
    .opic-bottom-nav {
      background: #ffffff !important;
      border: 1px solid rgba(17, 24, 39, 0.08) !important;
      box-shadow:
        0 1px 2px rgba(17, 24, 39, 0.06),
        0 8px 24px rgba(17, 24, 39, 0.08) !important;
    }

    a.opic-bottom-nav__item {
      color: #6b7280 !important;
    }

    a.opic-bottom-nav__item:hover {
      color: #111827 !important;
      background: rgba(17, 24, 39, 0.04) !important;
    }

    .opic-bottom-nav__item--active,
    a.opic-bottom-nav__item.opic-bottom-nav__item--active {
      color: #0f766e !important;
      background: #e6fffa !important;
    }

    .opic-bottom-nav__ico,
    .opic-bottom-nav__label {
      color: inherit !important;
    }

    /* Streamlit widgets — keep buttons readable on light surfaces */
    .stButton > button,
    div[data-testid="stButton"] > button {
      background: rgba(255, 255, 255, 0.95) !important;
      color: #111827 !important;
      border-color: rgba(17, 24, 39, 0.12) !important;
    }

    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: linear-gradient(180deg, #14b8a6 0%, #0d9488 100%) !important;
      color: #ffffff !important;
      border-color: rgba(13, 148, 136, 0.35) !important;
    }

    /* Expanders, alerts, captions */
    [data-testid="stExpander"] details {
      background: #ffffff !important;
      color: #111827 !important;
      border-color: rgba(17, 24, 39, 0.08) !important;
    }

    [data-testid="stAlert"],
    div[data-testid="stNotification"] {
      color: #111827 !important;
    }

    .stMarkdown p,
    .stMarkdown li,
    .stMarkdown span,
    label[data-testid="stWidgetLabel"] p {
      color: inherit;
    }

    /* Light cards — explicit dark text on white surfaces */
    .tp-topic-card,
    .tp-topic-card .tp-topic-title,
    .tp-topic-card .tp-topic-sub {
      color: #111827 !important;
    }
    .tp-topic-card .tp-topic-meta {
      color: #0f766e !important;
    }
    .mx-question-card,
    .mx-question-card .mx-question-topic,
    .mx-question-card .mx-question-hint,
    .mx-question-card .mx-question-type {
      color: #111827 !important;
    }
    .mx-question-card .mx-question-hint {
      color: #4b5563 !important;
    }
    .mx-rh-chip,
    .mx-coach-chip,
    .mx-status:not(.mx-status--error):not(.mx-status--warn) {
      background: #f3f4f6 !important;
      color: #111827 !important;
    }

    /* Dark gradient surfaces — white text (must override main { color: #111827 }) */
    .mx-record-stage,
    .mx-record-stage * {
      color: #ffffff !important;
    }
    .mx-record-stage .mx-record-hint,
    .mx-record-stage .mx-record-empty,
    .mx-record-stage p {
      color: rgba(255, 255, 255, 0.88) !important;
    }
    .mx-record-stage .mx-record-eyebrow {
      color: rgba(204, 251, 241, 0.9) !important;
    }
    .mx-record-stage .mx-record-title {
      color: #ffffff !important;
    }
    .mx-record-stage .mx-record-saved {
      color: #d1fae5 !important;
    }
    /* Mic recorder sits below the card; keep Streamlit buttons outside the panel readable */
    section.main:has(.mx-record-stage) div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
      background: rgba(255, 255, 255, 0.95) !important;
      color: #111827 !important;
    }
"""


def inject_global_styles() -> None:
    import streamlit as st

    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)
