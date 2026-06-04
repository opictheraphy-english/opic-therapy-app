"""Global Streamlit CSS — premium medical AI design system."""

GLOBAL_CSS = """
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable.css");
    @import url("https://cdn.jsdelivr.net/gh/fonts-archive/BMDOHYEON/BMDOHYEON.css");

    :root {
      --font-sans: "Pretendard Variable", "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --font-display: "BM DOHYEON", var(--font-sans);
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
    p, span, div, input, textarea, select, label {
      font-family: var(--font-sans) !important;
    }

    h1, h2, h3, h4, h5, h6,
    .stButton > button,
    div[data-testid="stButton"] > button {
      font-family: var(--font-display) !important;
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
    section.main:has(.mx-record-stage) > div {
      padding-bottom: 120px !important;
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

    /* --- Quick Action Cards: per-card icon colour (option 1) -----------
       The .qa-ico SVGs use stroke="currentColor", so setting `color` on
       .qa-ico recolours the icon. `background` is the soft tinted tile.
       Pattern keeps the app's mint; the other three use blue / purple /
       amber so each function is identifiable at a glance. */
    .qa-card--pattern .qa-ico {
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    .qa-card--scripts .qa-ico {
      background: rgba(55, 138, 221, 0.12);
      color: #185FA5;
    }
    .qa-card--lectures .qa-ico {
      background: rgba(83, 74, 183, 0.12);
      color: #534AB7;
    }
    .qa-card--coaching .qa-ico {
      background: rgba(186, 117, 23, 0.14);
      color: #854F0B;
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
    /* Script-coaching report — text sections wrapped in the same boxed style. */
    .sc-report-card {
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 13px 15px;
      margin: 8px 0;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
    }
    .sc-report-card .sc-card-title {
      font-size: 0.82rem;
      font-weight: 700;
      color: #0f766e;
      margin: 0 0 8px 0;
      letter-spacing: -0.01em;
    }
    .sc-report-card .sc-card-body {
      color: #334155;
      font-size: 0.92rem;
      line-height: 1.6;
    }
    .sc-report-card .sc-card-body p { margin: 0 0 6px 0; }
    .sc-report-card .sc-card-body p:last-child { margin-bottom: 0; }
    .sc-report-card .sc-card-body ul { margin: 0; padding-left: 18px; }
    .sc-report-card .sc-card-body li { margin: 4px 0; }
    .sc-report-card .sc-q { font-weight: 600; color: #0f172a; }
    .sc-report-card .sc-script { color: #334155; white-space: pre-wrap; }
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
    .grammar-fix .gf-label,
    .coach-alt-card .gf-label {
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin: 8px 0 2px 0;
    }
    .grammar-fix .gf-label:first-child,
    .coach-alt-card .gf-label:first-child {
      margin-top: 0;
    }
    .grammar-fix .gf-val,
    .coach-alt-card .gf-val {
      font-size: 0.92rem;
      line-height: 1.5;
      margin: 0 0 4px 0;
      word-wrap: break-word;
      overflow-wrap: anywhere;
    }
    .grammar-fix .gf-val.gf-bad,
    .coach-alt-card .gf-val.gf-bad {
      color: #a16207;
      text-decoration: line-through;
      text-decoration-color: rgba(161, 98, 7, 0.35);
    }
    .grammar-fix .gf-val.gf-good {
      color: var(--mint);
      font-weight: 700;
    }
    section.main:has(.mx-marker) .mx-coach-empty-note {
      font-size: 0.86rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 4px 0 12px 0;
    }
    section.main:has(.mx-marker) .mx-coach-struct {
      padding: 12px 14px;
      border-radius: var(--radius-md);
      background: rgba(248, 250, 252, 0.95);
      border: 1px solid var(--border-subtle);
      margin-bottom: 8px;
    }
    section.main:has(.mx-marker) .mx-coach-struct-label {
      font-size: 0.72rem;
      font-weight: 700;
      color: var(--mint);
      margin: 10px 0 4px 0;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    section.main:has(.mx-marker) .mx-coach-struct-label:first-child {
      margin-top: 0;
    }
    section.main:has(.mx-marker) .mx-coach-struct-list {
      margin: 0 0 4px 0;
      padding-left: 1.1rem;
      font-size: 0.86rem;
      line-height: 1.55;
      color: var(--text);
    }
    section.main:has(.mx-marker) .mx-coach-struct-miss {
      color: var(--text-secondary);
    }
    section.main:has(.mx-marker) .mx-coach-example-body {
      font-size: 0.9rem;
      line-height: 1.65;
      color: var(--text);
      padding: 14px 16px;
      border-radius: var(--radius-md);
      background: linear-gradient(125deg, rgba(224, 242, 254, 0.55) 0%, rgba(255, 255, 255, 0.95) 100%);
      border: 1px solid rgba(59, 130, 246, 0.15);
      margin: 0 0 8px 0;
      white-space: normal;
      word-wrap: break-word;
      overflow-wrap: anywhere;
    }
    section.main:has(.mx-marker) .mx-coach-mission-list {
      margin: 0 0 12px 0;
      padding-left: 1.25rem;
      font-size: 0.9rem;
      line-height: 1.6;
      color: var(--text);
    }
    section.main:has(.mx-marker) .mx-coach-mission-item {
      margin-bottom: 6px;
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

    /* --- Pattern category tabs (st.radio horizontal, not st.tabs) ------ */
    .pat-screen .pat-tab-radio {
      margin: 0 0 14px 0;
      padding: 6px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid var(--border-subtle);
      border-radius: 999px;
      box-shadow: var(--shadow-card);
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] {
      margin: 0 !important;
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] > div {
      flex-direction: row !important;
      flex-wrap: wrap !important;
      gap: 6px !important;
      align-items: center !important;
      justify-content: center !important;
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label {
      margin: 0 !important;
      padding: 0 !important;
      background: transparent !important;
      border: none !important;
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label > div:first-child {
      display: none !important;
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label p,
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label span {
      font-size: 0.88rem !important;
      font-weight: 600 !important;
      color: #4b5563 !important;
      line-height: 1.2 !important;
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span {
      color: #ffffff !important;
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label:has(input:checked) {
      background: linear-gradient(135deg, #14b8a6 0%, var(--mint) 100%) !important;
      border-radius: 999px !important;
      padding: 8px 14px !important;
      box-shadow: 0 6px 16px rgba(13, 148, 136, 0.25);
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label:not(:has(input:checked)) {
      padding: 8px 14px !important;
      border-radius: 999px !important;
    }
    .pat-screen .pat-tab-radio [data-testid="stRadio"] label:not(:has(input:checked)):hover {
      background: rgba(13, 148, 136, 0.06) !important;
    }

    /* Hide legacy st.tabs if any leak into the pattern screen */
    .pat-screen [data-testid="stTabs"] {
      display: none !important;
      visibility: hidden !important;
      height: 0 !important;
      max-height: 0 !important;
      overflow: hidden !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: none !important;
    }

    /* --- Streamlit tab bar (legacy — kept hidden above) ---------------- */
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

    /* --- Section groups (custom toggle — not st.expander) --------------- */
    .pat-screen .pat-sec-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin: 0 0 6px 0;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    .pat-screen .pat-sec-head--open {
      border-color: rgba(13, 148, 136, 0.22);
      border-bottom-left-radius: 0;
      border-bottom-right-radius: 0;
      margin-bottom: 0;
    }
    .pat-screen .pat-sec-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #111827 !important;
      letter-spacing: -0.01em;
      line-height: 1.35;
    }
    .pat-screen .pat-sec-count {
      flex-shrink: 0;
      font-size: 0.78rem;
      font-weight: 700;
      color: #0f766e;
      background: rgba(204, 251, 241, 0.65);
      border: 1px solid rgba(13, 148, 136, 0.18);
      padding: 4px 10px;
      border-radius: 999px;
    }
    .pat-screen .pat-sec-body {
      margin: 0 0 12px 0;
      padding: 12px 12px 4px 12px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid rgba(13, 148, 136, 0.22);
      border-top: none;
      border-radius: 0 0 var(--radius-md) var(--radius-md);
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
    }
    .pat-screen .pat-sec-head--inline {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .pat-screen .pat-sec-head--inline .pat-sec-title {
      flex: 1 1 auto;
      min-width: 0;
    }

    /* Shared small chevron (section + pattern row) — one icon only. */
    .pat-screen .pat-chevron {
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      color: #0f766e;
      background: rgba(13, 148, 136, 0.12);
      transition: transform 0.16s var(--ease-out);
    }
    .pat-screen .pat-chevron svg {
      width: 16px;
      height: 16px;
    }
    .pat-screen .pat-sec-head--open .pat-chevron,
    .pat-screen .pat-row--open .pat-chevron {
      transform: rotate(90deg);
    }

    /* Section header: tappable stack (invisible button — no second arrow). */
    .pat-screen .pat-sec-stack {
      display: block;
      margin-bottom: 8px;
    }
    .pat-screen div[data-testid="stVerticalBlock"]:has(.pat-sec-stack) {
      position: relative !important;
    }
    .pat-screen div[data-testid="stVerticalBlock"]:has(.pat-sec-stack)
      > div[data-testid="stElementContainer"]:has(.pat-sec-stack),
    .pat-screen div[data-testid="stVerticalBlock"]:has(.pat-sec-stack)
      .pat-sec-head,
    .pat-screen div[data-testid="stVerticalBlock"]:has(.pat-sec-stack)
      .pat-sec-head * {
      pointer-events: none !important;
    }
    .pat-screen div[data-testid="stVerticalBlock"]:has(.pat-sec-stack)
      > div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]) {
      position: absolute !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      height: 48px !important;
      z-index: 3 !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    .pat-screen div[data-testid="stVerticalBlock"]:has(.pat-sec-stack)
      > div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"])
      > div[data-testid="stButton"]
      > button {
      width: 100% !important;
      height: 48px !important;
      min-height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      border: none !important;
      background: transparent !important;
      color: transparent !important;
      box-shadow: none !important;
      cursor: pointer !important;
    }

    /* --- Pattern row (tappable list item, topic-practice card tone) --- */
    .pat-screen .pat-row-stack {
      display: block;
    }
    .pat-screen .pat-row {
      display: flex;
      align-items: center;
      gap: 10px;
      background: #ffffff;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 12px 14px 12px 18px;
      margin: 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
      transition: box-shadow 0.18s var(--ease-out), border-color 0.18s var(--ease-out);
      position: relative;
    }
    .pat-screen .pat-row::before {
      content: "";
      position: absolute;
      left: 0;
      top: 12px;
      bottom: 12px;
      width: 3px;
      border-radius: 3px;
      background: linear-gradient(180deg, var(--mint) 0%, rgba(13, 148, 136, 0.4) 100%);
    }
    .pat-screen .pat-row--open {
      border-color: rgba(13, 148, 136, 0.28);
      border-bottom-left-radius: 0;
      border-bottom-right-radius: 0;
    }
    .pat-screen .pat-row-body {
      flex: 1 1 auto;
      min-width: 0;
    }
    .pat-screen .pat-detail-panel {
      margin: 0 0 10px 0;
      padding: 12px 14px 14px 14px;
      background: rgba(255, 255, 255, 0.98);
      border: 1px solid rgba(13, 148, 136, 0.22);
      border-top: none;
      border-radius: 0 0 var(--radius-md) var(--radius-md);
      box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
    }
    .pat-screen .pat-detail-usage {
      font-size: 0.8rem;
      color: var(--text-secondary);
      line-height: 1.5;
      margin: 0 0 10px 0;
    }
    .pat-screen .pat-detail-block {
      margin: 0 0 10px 0;
      padding: 12px 14px;
      background: rgba(248, 250, 252, 0.9);
      border: 1px solid rgba(15, 23, 42, 0.06);
      border-radius: var(--radius-sm);
    }
    .pat-screen .pat-detail-block-title {
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0 0 8px 0;
    }
    .pat-screen .pat-ex-line {
      padding: 8px 0;
      border-top: 1px solid rgba(15, 23, 42, 0.05);
    }
    .pat-screen .pat-ex-line:first-of-type {
      border-top: none;
      padding-top: 0;
    }
    .pat-screen .pat-ex-line-label {
      display: block;
      font-size: 0.68rem;
      font-weight: 700;
      color: #0f766e;
      margin-bottom: 4px;
    }
    .pat-screen .pat-ex-line-en {
      font-size: 0.86rem;
      line-height: 1.55;
      color: var(--navy);
      margin: 0;
    }
    .pat-screen .pat-ex-line-ko {
      font-size: 0.78rem;
      color: var(--text-secondary);
      line-height: 1.45;
      margin: 4px 0 0 0;
    }
    .pat-screen .pat-detail-tip {
      font-size: 0.8rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 0 0 10px 0;
      padding: 8px 10px;
      background: rgba(254, 243, 199, 0.35);
      border-radius: var(--radius-sm);
      border: 1px solid rgba(245, 158, 11, 0.15);
    }
    .pat-screen .pat-detail-tip-label {
      font-weight: 700;
      color: #92400e;
      margin-right: 4px;
    }
    /* Transparent overlay toggle on each pattern row (pat-list-marker scope). */
    .pat-screen:has(.pat-list-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-row-stack) {
      position: relative !important;
      margin-bottom: 6px !important;
    }
    .pat-screen:has(.pat-list-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-row-stack)
      > div[data-testid="stElementContainer"]:has(.pat-row-stack),
    .pat-screen:has(.pat-list-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-row-stack)
      .pat-row,
    .pat-screen:has(.pat-list-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-row-stack)
      .pat-row * {
      pointer-events: none !important;
    }
    .pat-screen:has(.pat-list-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-row-stack)
      > div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]) {
      position: absolute !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      height: 64px !important;
      border: none !important;
      background: transparent !important;
      box-shadow: none !important;
      z-index: 3 !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    .pat-screen:has(.pat-list-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-row-stack)
      > div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"])
      > div[data-testid="stButton"]
      > button {
      width: 100% !important;
      height: 100% !important;
      min-height: 0 !important;
      border: none !important;
      background: transparent !important;
      color: transparent !important;
      box-shadow: none !important;
      cursor: pointer !important;
    }
    .pat-screen:has(.pat-list-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-row-stack):has(
        div[data-testid="stButton"] > button:hover
      )
      .pat-row {
      border-color: rgba(13, 148, 136, 0.35) !important;
      box-shadow: 0 4px 14px rgba(13, 148, 136, 0.12) !important;
    }
    /* Shared collapsible sections (mock survey / report / patterns) */
    .mx-survey-head,
    .mx-col-head,
    .pat-sec-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin: 0 0 6px 0;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    .mx-survey-title,
    .mx-col-title,
    .pat-sec-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #111827 !important;
      letter-spacing: -0.01em;
      line-height: 1.35;
    }
    .mx-survey-count,
    .mx-col-count,
    .pat-sec-count {
      flex-shrink: 0;
      font-size: 0.78rem;
      font-weight: 700;
      color: #0f766e;
      background: rgba(204, 251, 241, 0.65);
      border: 1px solid rgba(13, 148, 136, 0.18);
      padding: 4px 10px;
      border-radius: 999px;
    }
    .mx-survey-body,
    .mx-col-body,
    .pat-sec-body {
      margin: 0 0 12px 0;
      padding: 12px 12px 4px 12px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid rgba(13, 148, 136, 0.16);
      border-radius: var(--radius-md);
    }
    section.main:has(.mx-marker) .mx-survey-head--open,
    section.main:has(.mx-marker) .mx-col-head--open,
    .pat-screen .pat-sec-head--open {
      border-color: rgba(13, 148, 136, 0.22);
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

    /* --- Pattern card action buttons (열기 / 예문 더보기 / 접기) ------------ */
    .pat-screen div[data-testid="stButton"]:has(button[key*="pat_detail"]),
    .pat-screen div[data-testid="stButton"]:has(button[key*="pat_ex_toggle"]) {
      margin-top: 8px !important;
    }
    .pat-screen div[data-testid="stButton"]:has(button[key*="pat_detail"]) > button,
    .pat-screen div[data-testid="stButton"]:has(button[key*="pat_ex_toggle"]) > button {
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
    .pat-screen div[data-testid="stButton"]:has(button[key*="pat_detail"]) > button:hover,
    .pat-screen div[data-testid="stButton"]:has(button[key*="pat_ex_toggle"]) > button:hover {
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
    /* --- Final report preview (real mock completion) ------------------- */
    .mx-fr-preview {
      margin: 16px 0 18px 0;
      padding: 16px 18px;
      border-radius: 18px;
      background: linear-gradient(165deg, rgba(204, 251, 241, 0.55) 0%, #ffffff 72%);
      border: 1px solid rgba(13, 148, 136, 0.18);
      box-shadow: 0 10px 28px rgba(13, 148, 136, 0.08);
    }
    .mx-frp-eyebrow {
      margin: 0 0 12px 0;
      font-size: 1.05rem;
      font-weight: 800;
      color: #0f766e;
      letter-spacing: -0.02em;
    }
    .mx-frp-stats {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 8px;
    }
    .mx-frp-stats li {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.9rem;
      color: var(--text-secondary);
    }
    .mx-frp-label {
      font-weight: 600;
    }
    .mx-frp-val {
      font-weight: 800;
      color: var(--mint);
    }
    .mx-frp-pending {
      margin: 12px 0 0 0;
      font-size: 0.84rem;
      color: #0f766e;
      line-height: 1.45;
    }
    .mx-frp-insights-title {
      margin: 14px 0 8px 0;
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
    }
    .mx-frp-insights {
      margin: 0;
      padding-left: 1.15rem;
      color: var(--text-secondary);
      font-size: 0.9rem;
      line-height: 1.55;
    }
    .mx-frp-insights-note {
      margin: 12px 0 0 0;
      font-size: 0.88rem;
      color: var(--text-secondary);
      line-height: 1.5;
    }
    .mx-fr-progress {
      margin: 0 0 14px 0;
      padding: 10px 14px;
      border-radius: 14px;
      background: var(--mint-muted);
      border: 1px solid rgba(13, 148, 136, 0.12);
    }
    .mx-fr-progress-title {
      margin: 0;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
    }
    .mx-fr-progress-line {
      margin: 4px 0 0 0;
      font-size: 1rem;
      font-weight: 800;
      color: var(--mint);
    }
    .mx-fr-progress-meta {
      margin: 4px 0 0 0;
      font-size: 0.82rem;
      color: var(--text-secondary);
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

    /* Learning portal — sample report vs practice mode grid */
    section.main:has(.mx-landing-marker) .mx-portal-sample-section {
      margin-bottom: 28px;
      padding-bottom: 20px;
      border-bottom: 1px solid rgba(17, 24, 39, 0.08);
    }
    section.main:has(.mx-landing-marker) .mx-portal-practice-intro {
      margin: 4px 0 14px;
    }
    section.main:has(.mx-landing-marker) .mx-portal-section-title {
      margin: 0;
      font-size: 1.05rem;
      font-weight: 700;
      color: #111827;
      letter-spacing: -0.02em;
    }
    section.main:has(.mx-landing-marker) .mx-muted-note {
      margin: 10px 0 0;
      font-size: 0.78rem;
      line-height: 1.45;
      color: #6b7280;
    }
    section.main:has(.mx-landing-marker) .mx-portal-practice-marker ~ div[data-testid="stHorizontalBlock"] {
      gap: 14px;
      align-items: stretch;
    }
    section.main:has(.mx-landing-marker) .mx-portal-practice-marker ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
      display: flex;
      flex-direction: column;
      gap: 12px;
      justify-content: flex-start;
    }
    section.main:has(.mx-landing-marker) .mx-portal-mode-card {
      position: relative;
      /* Fixed, identical height for every card so the start buttons (which sit
         directly below each card) line up across columns. ``flex: 0 0 auto``
         stops Streamlit's column from stretching cards to uneven heights. */
      min-height: 144px;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      gap: 8px;
      flex: 0 0 auto;
      margin-bottom: 0;
    }
    /* "추천 · 약 5분" badge pinned top-right so it adds no card height —
       keeps the 5-min card the same height as 실전 모의고사 → buttons align. */
    section.main:has(.mx-landing-marker) .mx-portal-mode-card .mx-mode-badge {
      position: absolute;
      top: 12px;
      right: 12px;
      margin: 0 !important;
      padding: 3px 10px;
      border-radius: 999px;
      background: rgba(37, 99, 235, 0.12);
      color: #2563eb !important;
      font-size: 11px;
      font-weight: 700;
      line-height: 1.4;
    }
    /* Title shouldn't run under the pinned badge (only the badge card). */
    section.main:has(.mx-landing-marker) .mx-portal-mode-card:has(.mx-mode-badge) .cc-title {
      padding-right: 76px;
    }
    section.main:has(.mx-landing-marker) .mx-portal-mode-spacer {
      min-height: 1px;
      visibility: hidden;
    }
    section.main:has(.mx-landing-marker) .mx-portal-practice-marker ~ div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button {
      width: 100%;
    }

    /* ------------------------------------------------------------------
     * Portal card alignment — version-independent (Streamlit 1.50 renders
     * the main container as ``stMain``, so the older ``section.main`` scope
     * above no longer matches). ``.mx-portal-mode-card`` is unique to this
     * portal, so we size it directly (no main-section dependency). All four
     * cards share one fixed height → the start buttons that follow each card
     * line up across columns. ----------------------------------------- */
    .mx-portal-mode-card {
      position: relative !important;
      min-height: 112px !important;
      height: 112px !important;
      padding: 15px 18px !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: flex-start !important;
      gap: 5px !important;
      flex: 0 0 auto !important;
      margin: 0 0 10px 0 !important;
    }
    .mx-portal-mode-card .mx-mode-badge {
      position: absolute;
      top: 14px;
      right: 14px;
      margin: 0 !important;
      padding: 3px 10px;
      border-radius: 999px;
      background: rgba(37, 99, 235, 0.12);
      color: #2563eb !important;
      font-size: 11px;
      font-weight: 700;
      line-height: 1.4;
    }
    .mx-portal-mode-card:has(.mx-mode-badge) .cc-title {
      padding-right: 80px;
    }

    @media (max-width: 640px) {
      .mx-portal-mode-card {
        min-height: 118px !important;
        height: 118px !important;
      }
    }

    @media (max-width: 640px) {
      section.main:has(.mx-landing-marker) .mx-portal-sample-section {
        margin-bottom: 22px;
        padding-bottom: 16px;
      }
      section.main:has(.mx-landing-marker) .mx-portal-mode-card {
        min-height: 132px;
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
    .mx-listen-compact {
      margin: 0 0 14px 0;
      padding: 12px 14px;
      border-radius: 14px;
      background: #f8fafc;
      border: 1px solid rgba(17, 24, 39, 0.08);
    }
    .mx-listen-compact-label {
      margin: 0 0 8px 0;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #64748b;
    }
    .mx-listen-compact-cap {
      margin: 8px 0 0 0;
      font-size: 0.72rem;
      color: #94a3b8;
    }
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button {
      font-size: 0.88rem !important;
      padding: 0.35rem 0.75rem !important;
      min-height: 2.25rem !important;
      background: #ffffff !important;
      color: #0f766e !important;
      border: 1px solid rgba(13, 148, 136, 0.35) !important;
      box-shadow: none !important;
    }
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button[kind="primary"],
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: #ffffff !important;
      color: #0f766e !important;
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
    .mx-record-stage .mx-rec-timer {
      margin: 0 0 16px 0;
      padding: 16px 18px;
      border-radius: 20px;
      background: linear-gradient(165deg, rgba(255, 255, 255, 0.98) 0%, rgba(240, 253, 250, 0.96) 100%);
      border: 1px solid rgba(13, 148, 136, 0.22);
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
      color: #0f172a !important;
      text-align: center;
    }
    .mx-record-stage .mx-rec-timer-label,
    .mx-record-stage .mx-answer-timer-label {
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #0f766e !important;
      margin: 0;
    }
    .mx-answer-timer-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }
    .mx-answer-timer-status {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      background: rgba(13, 148, 136, 0.12);
      color: #0f766e !important;
    }
    .mx-answer-timer-status--idle {
      background: rgba(100, 116, 139, 0.14);
      color: #64748b !important;
    }
    .mx-answer-timer-status--warn,
    .mx-answer-timer-status--up {
      background: rgba(234, 88, 12, 0.14);
      color: #c2410c !important;
    }
    .mx-record-title--live {
      font-size: 1.15rem;
      font-weight: 700;
      margin: 0 0 8px 0;
      color: #ffffff !important;
    }
    .mx-record-stage .mx-rec-timer-value {
      font-size: 2rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      color: #0f766e !important;
      margin: 0 0 10px 0;
      line-height: 1.1;
      font-variant-numeric: tabular-nums;
    }
    .mx-record-stage .mx-rec-timer-progress {
      display: block;
      width: 100%;
      height: 6px;
      border-radius: 999px;
      background: rgba(13, 148, 136, 0.12);
      overflow: hidden;
      margin: 0 0 10px 0;
    }
    .mx-record-stage .mx-rec-timer-progress-fill {
      display: block;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #14b8a6 0%, #0d9488 100%);
      transition: width 0.35s ease;
    }
    .mx-record-stage .mx-rec-timer-helper {
      font-size: 0.8rem;
      line-height: 1.45;
      margin: 0;
      color: #64748b !important;
    }
    .mx-record-stage .mx-rec-timer--idle {
      background: rgba(255, 255, 255, 0.96);
    }
    .mx-record-stage .mx-rec-timer--idle .mx-rec-timer-value {
      color: #334155 !important;
    }
    .mx-record-stage .mx-rec-timer--normal .mx-rec-timer-value {
      color: #0f766e !important;
    }
    .mx-record-stage .mx-rec-timer--warn {
      border-color: rgba(234, 88, 12, 0.5);
      background: linear-gradient(165deg, rgba(255, 251, 235, 0.98) 0%, rgba(255, 247, 237, 0.98) 100%);
    }
    .mx-record-stage .mx-rec-timer--warn .mx-rec-timer-value {
      color: #c2410c !important;
    }
    .mx-record-stage .mx-rec-timer--warn .mx-rec-timer-progress-fill {
      background: linear-gradient(90deg, #fb923c 0%, #ea580c 100%);
    }
    .mx-record-stage .mx-rec-timer--warn .mx-rec-timer-helper {
      color: #c2410c !important;
      font-weight: 600;
    }
    .mx-record-stage .mx-rec-timer--up {
      border-color: rgba(220, 38, 38, 0.45);
      background: linear-gradient(165deg, rgba(254, 242, 242, 0.98) 0%, rgba(255, 247, 247, 0.98) 100%);
    }
    .mx-record-stage .mx-rec-timer--up .mx-rec-timer-value {
      color: #b91c1c !important;
    }
    .mx-record-stage .mx-rec-timer--up .mx-rec-timer-progress-fill {
      background: linear-gradient(90deg, #f87171 0%, #dc2626 100%);
    }
    .mx-record-stage .mx-rec-timer--up .mx-rec-timer-helper {
      color: #b91c1c !important;
      font-weight: 600;
    }
    .mx-daily-usage {
      margin: 8px 0 12px 0;
      font-size: 0.85rem;
      color: var(--text-secondary);
    }
    .mx-ai-wait-footnote {
      margin: 0 0 8px 0;
      font-size: 0.82rem;
      color: var(--text-secondary);
      line-height: 1.45;
    }
    .tp-mini-topic {
      margin-top: 6px;
      font-size: 0.9rem;
      color: var(--text-secondary);
    }
    /* Hide internal Streamlit / iframe widget key labels (e.g. mic_*_follow_right) */
    section.main div[data-testid="stCustomComponent"] [data-testid="stWidgetLabel"],
    section.main div[data-testid="stCustomComponent"] label {
      display: none !important;
      height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      overflow: hidden !important;
      visibility: hidden !important;
    }
    .mx-record-status {
      margin: 8px 0 4px 0;
      font-size: 0.88rem;
      color: var(--text-secondary);
      line-height: 1.5;
    }
    section.main:has(.mx-record-stage) .mx-record-status {
      color: rgba(255, 255, 255, 0.88) !important;
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

    /* Status widget (``st.status``) — legacy; analysis uses .mx-ai-wait */
    section.main:has(.mx-marker) [data-testid="stStatus"] {
      border-radius: var(--radius-md) !important;
      border: 1px solid var(--border-subtle) !important;
      background: rgba(255, 255, 255, 0.92) !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03) !important;
    }

    /* --- AI analysis waiting screen -------------------------------- */
    .mx-ai-wait-marker {
      display: none !important;
    }
    .mx-ai-wait {
      max-width: 520px;
      margin: 8px auto 20px auto;
      padding: 24px 20px 20px 20px;
      border-radius: var(--radius-lg);
      background: linear-gradient(145deg, rgba(255, 255, 255, 0.98) 0%, rgba(236, 253, 245, 0.55) 100%);
      border: 1px solid rgba(13, 148, 136, 0.16);
      box-shadow: var(--shadow-card);
      text-align: center;
    }
    .mx-ai-wait-anim {
      position: relative;
      width: 72px;
      height: 72px;
      margin: 0 auto 14px auto;
    }
    .mx-ai-wait-ring {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      border: 3px solid rgba(13, 148, 136, 0.15);
      border-top-color: var(--mint);
      animation: mxWaitSpin 1.1s linear infinite;
    }
    @keyframes mxWaitSpin {
      to { transform: rotate(360deg); }
    }
    .mx-ai-wait-mic {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--mint);
      animation: mxWaitPulse 1.6s ease-in-out infinite;
    }
    @keyframes mxWaitPulse {
      0%, 100% { transform: scale(1); opacity: 0.85; }
      50% { transform: scale(1.06); opacity: 1; }
    }
    .mx-ai-wait-bubble {
      position: absolute;
      top: 4px;
      right: -2px;
      width: 18px;
      height: 14px;
      border-radius: 10px 10px 10px 2px;
      background: rgba(204, 251, 241, 0.9);
      border: 1px solid rgba(13, 148, 136, 0.25);
      animation: mxWaitBubble 1.8s ease-in-out infinite;
    }
    @keyframes mxWaitBubble {
      0%, 100% { transform: scale(0.92); opacity: 0.7; }
      50% { transform: scale(1.05); opacity: 1; }
    }
    .mx-ai-wait-dots {
      display: flex;
      justify-content: center;
      gap: 6px;
      margin: 0 0 12px 0;
    }
    .mx-ai-wait-dots span {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--mint);
      animation: mxWaitBounce 1.2s ease-in-out infinite;
    }
    .mx-ai-wait-dots span:nth-child(2) { animation-delay: 0.15s; }
    .mx-ai-wait-dots span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes mxWaitBounce {
      0%, 80%, 100% { transform: translateY(0); opacity: 0.45; }
      40% { transform: translateY(-6px); opacity: 1; }
    }
    .mx-ai-wait-title {
      font-size: 1.2rem;
      font-weight: 800;
      color: var(--navy);
      margin: 0 0 8px 0;
      letter-spacing: -0.02em;
    }
    .mx-ai-wait-sub {
      font-size: 0.9rem;
      line-height: 1.55;
      color: var(--text-secondary);
      margin: 0 0 10px 0;
    }
    .mx-ai-wait-stage {
      font-size: 0.8rem;
      color: var(--mint);
      font-weight: 600;
      margin: 0 0 14px 0;
    }
    .mx-ai-wait-tip {
      margin-top: 6px;
      padding: 14px 16px;
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--border-subtle);
      text-align: left;
    }
    .mx-ai-wait-tip-eyebrow {
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0 0 10px 0;
    }
    .mx-ai-wait-tip-label {
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin: 10px 0 2px 0;
    }
    .mx-ai-wait-tip-label:first-of-type {
      margin-top: 0;
    }
    .mx-ai-wait-tip-pattern {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--navy);
      margin: 0;
      line-height: 1.4;
    }
    .mx-ai-wait-tip-text,
    .mx-ai-wait-tip-example {
      font-size: 0.88rem;
      line-height: 1.5;
      color: var(--text);
      margin: 0;
    }
    .mx-ai-wait-tip-example {
      color: var(--text-secondary);
      font-style: italic;
    }

    .mx-speech-debug {
      margin: 10px 0 14px 0;
      padding: 10px 12px;
      border-radius: var(--radius-md);
      background: rgba(15, 23, 42, 0.04);
      border: 1px dashed rgba(13, 148, 136, 0.35);
      font-size: 0.72rem;
      line-height: 1.45;
      color: var(--text-muted);
    }
    .mx-speech-debug-label {
      font-weight: 700;
      margin: 0 0 4px 0;
      color: var(--text-secondary);
    }
    .mx-speech-debug-body {
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
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
      :root {
        color-scheme: light only !important;
      }
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
      /* White card surfaces — keep light even if the UA tries to auto-dark.
         Accent icon boxes / badges use explicit rgba and are left untouched,
         and mint-gradient .continue-card variants keep their own background. */
      .tp-card,
      .tq-card,
      .tq-answer-card-top,
      .tq-saved-section,
      .tq-saved-recording-top,
      .section-card,
      .glass-card,
      .glass-card-quiet,
      .topbar {
        background-color: #ffffff !important;
        color: #111827 !important;
      }
      .tp-card-title,
      .tq-question,
      .tq-answer-title,
      .tq-saved-status-text,
      .tq-saved-label,
      .tq-saved-transcript {
        color: #111827 !important;
      }
      .tp-card-sub,
      .tq-question-ko,
      .tq-answer-desc,
      .tq-saved-transcript--empty {
        color: #6b7280 !important;
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

    /* Card surfaces — mint-tinted (was flat #ffffff). The light-mode
       override previously forced a plain white background, which hid the
       intended mint gradient from the base .continue-card rules. These
       values restore a visible mint tint (design option "B"): a 15%-mint
       diagonal wash with a slightly stronger mint border. Text-color
       overrides above are kept as-is so readability is unaffected. */
    .continue-card--resume,
    .continue-card--start,
    .mx-mode-card,
    .mx-landing-card {
      background:
        linear-gradient(135deg, rgba(13, 148, 136, 0.15) 0%, #ffffff 100%) !important;
      border: 1px solid rgba(13, 148, 136, 0.24) !important;
    }

    .mx-mode-badge {
      margin: 10px 0 0;
      font-size: 12px;
      font-weight: 600;
      color: #2563eb !important;
      letter-spacing: -0.01em;
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

    /* Topic-practice primary buttons follow the selected topic's accent
       (scoped marker .tq-accent-scope--* beats the global teal rule above).
       Mock exams plant no marker, so they keep the teal default. */
    [data-testid="stMain"]:has(.tq-accent-scope) .tq-accent-scope { display: none !important; }
    [data-testid="stMain"]:has(.tq-accent-scope--teal) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--teal) div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: linear-gradient(180deg, #14b8a6 0%, #0d9488 100%) !important;
      border-color: rgba(13, 148, 136, 0.35) !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--blue) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--blue) div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: linear-gradient(180deg, #3b8ae0 0%, #2c6fb8 100%) !important;
      border-color: rgba(55, 138, 221, 0.35) !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--purple) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--purple) div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: linear-gradient(180deg, #6a5fd0 0%, #534ab7 100%) !important;
      border-color: rgba(83, 74, 183, 0.35) !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--pink) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--pink) div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: linear-gradient(180deg, #d9537e 0%, #b83f66 100%) !important;
      border-color: rgba(217, 83, 126, 0.35) !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--amber) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--amber) div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: linear-gradient(180deg, #be7b18 0%, #8a560f 100%) !important;
      border-color: rgba(186, 117, 23, 0.40) !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--coral) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--coral) div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: linear-gradient(180deg, #d85a30 0%, #b23f1c 100%) !important;
      border-color: rgba(216, 90, 48, 0.35) !important;
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

    /* Headings in Streamlit markdown beat .stMarkdown { font-family: sans } */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
      font-family: var(--font-display) !important;
    }

    /* --- Topic practice cards (tp-card) — after light-mode overrides -------- */
    .tp-cards-marker {
      display: none !important;
    }
    .tp-card {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      overflow: visible;
      border-radius: 16px;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.06);
      color: inherit !important;
      margin: 0;
      pointer-events: none;
      transition: transform 0.16s var(--ease-out), box-shadow 0.16s var(--ease-out),
        border-color 0.16s var(--ease-out);
    }
    .tp-card-ico {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      border-radius: 11px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(13, 148, 136, 0.10);
      color: #0f766e;
      margin: 0;
    }
    .tp-card-ico svg {
      width: 20px;
      height: 20px;
      stroke-width: 2;
    }
    .tp-card-body {
      display: flex;
      flex-direction: column;
      gap: 1px;
      min-width: 0;
      flex: 1 1 auto;
      overflow: visible;
    }
    .tp-card-title {
      font-family: var(--font-display) !important;
      font-size: 14px;
      font-weight: 500;
      color: var(--navy);
      letter-spacing: -0.01em;
      line-height: 1.2;
      margin: 0;
    }
    .tp-card-sub {
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.35;
      margin: 0;
      overflow: visible;
    }
    /* Right-aligned chevron in a circular accent button — clear "tap me" cue. */
    .tp-card-chevron {
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      margin-left: 8px;
      color: #0f766e;
      background: rgba(13, 148, 136, 0.12);
      transition: transform 0.16s var(--ease-out), background 0.16s var(--ease-out);
    }
    .tp-card-chevron svg {
      width: 18px;
      height: 18px;
    }
    /* Card = single tappable unit — transparent st.button overlays the card
       (topic-practice grid only, Streamlit 1.50). The card markdown is the
       visible surface; the button sits on top (inset:0) and receives clicks. */
    /* Positioning anchor for the absolute overlay button. Both the column and
       its vertical block are made relative so inset:0 always sizes to the card
       even if Streamlit's wrapper nesting changes. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card) {
      position: relative;
    }
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      > [data-testid="stVerticalBlock"] {
      position: relative;
      gap: 0 !important;
      height: auto !important;
    }
    /* Let the card's containers grow to the card's true height so the overlay
       (sized to the column) covers the whole card — not a flex-clipped strip. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card) {
      align-self: flex-start !important;
      height: auto !important;
    }
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      div[data-testid="stElementContainer"]:has(.tp-card) {
      height: auto !important;
    }
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      div[data-testid="stMarkdown"]:has(.tp-card) {
      margin-bottom: 0 !important;
    }
    /* The markdown container ships a negative bottom margin (-1rem) that pulls
       the card up and shrinks its element-container's reported height (58→42),
       which previously starved the overlay. Zero it so the column wraps the
       full card and the overlay covers all of it. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      div[data-testid="stMarkdownContainer"]:has(.tp-card) {
      margin-bottom: 0 !important;
    }
    /* The whole card visual (wrapper + card + every child) must NOT capture
       clicks — all clicks fall through to the transparent overlay button so
       the entire card surface is tappable, not just the arrow. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      div[data-testid="stElementContainer"]:has(.tp-card),
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      div[data-testid="stMarkdown"]:has(.tp-card),
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card) .tp-card,
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card) .tp-card * {
      pointer-events: none !important;
    }
    /* Streamlit sets .element-container { position: relative } by default, which
       would trap an absolute stButton inside its own (collapsed, 0-height)
       wrapper. So make the button's element-container ITSELF the overlay layer,
       sized to the column, and let the inner button fill it. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]) {
      position: absolute !important;
      inset: 0 !important;
      height: 100% !important;
      z-index: 3 !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      div[data-testid="stButton"] {
      position: static !important;
      width: 100% !important;
      height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      div[data-testid="stButton"]
      > button {
      width: 100% !important;
      height: 100% !important;
      min-height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      border: none !important;
      border-radius: 16px !important;
      background: transparent !important;
      box-shadow: none !important;
      color: transparent !important;
      cursor: pointer !important;
      pointer-events: auto !important;
    }
    /* Lift the card when the overlay button is hovered/focused (desktop). */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .tp-card,
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .tp-card {
      transform: translateY(-2px);
      border-color: rgba(13, 148, 136, 0.35) !important;
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06), 0 10px 24px rgba(13, 148, 136, 0.16) !important;
    }
    /* Hover: nudge the arrow right + fill its circle a touch. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .tp-card-chevron {
      transform: translateX(2px);
      filter: brightness(0.96);
    }
    /* Tap feedback (mobile + desktop): press the card in slightly. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:active)
      .tp-card {
      transform: translateY(0) scale(0.985);
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
    }
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:active)
      .tp-card-chevron {
      transform: translateX(1px) scale(0.94);
    }
    .tp-card--teal .tp-card-ico {
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    .tp-card--blue .tp-card-ico {
      background: rgba(55, 138, 221, 0.12);
      color: #185FA5;
    }
    .tp-card--purple .tp-card-ico {
      background: rgba(83, 74, 183, 0.12);
      color: #534AB7;
    }
    .tp-card--pink .tp-card-ico {
      background: rgba(217, 83, 126, 0.12);
      color: #993556;
    }
    .tp-card--amber .tp-card-ico {
      background: rgba(186, 117, 23, 0.14);
      color: #854F0B;
    }
    .tp-card--coral .tp-card-ico {
      background: rgba(216, 90, 48, 0.12);
      color: #993C1D;
    }
    .tp-card--teal .tp-card-chevron {
      color: #0F6E56; background: rgba(13, 148, 136, 0.14);
    }
    .tp-card--blue .tp-card-chevron {
      color: #185FA5; background: rgba(55, 138, 221, 0.14);
    }
    .tp-card--purple .tp-card-chevron {
      color: #534AB7; background: rgba(83, 74, 183, 0.14);
    }
    .tp-card--pink .tp-card-chevron {
      color: #993556; background: rgba(217, 83, 126, 0.14);
    }
    .tp-card--amber .tp-card-chevron {
      color: #854F0B; background: rgba(186, 117, 23, 0.16);
    }
    .tp-card--coral .tp-card-chevron {
      color: #993C1D; background: rgba(216, 90, 48, 0.14);
    }

    /* --- Topic practice question screen (tq-*) — scoped like tp-cards ----- */
    .tq-screen-marker {
      display: none !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 0 0 12px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      flex: 1 1 auto;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip-ico {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      border-radius: 11px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip-ico svg {
      width: 20px;
      height: 20px;
      stroke-width: 2;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip-name {
      font-family: var(--font-display) !important;
      font-size: 15px;
      font-weight: 500;
      color: var(--navy);
      letter-spacing: -0.01em;
      line-height: 1.2;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-progress {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
      flex-shrink: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-progress-bars {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-progress-seg {
      width: 22px;
      height: 5px;
      border-radius: 3px;
      background: rgba(17, 24, 39, 0.10);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-progress-seg--on {
      background: #0d9488;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-progress-text {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      letter-spacing: 0.02em;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-progress--bar {
      min-width: 88px;
      max-width: 120px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-progress-track {
      width: 100%;
      height: 5px;
      border-radius: 3px;
      background: rgba(17, 24, 39, 0.10);
      overflow: hidden;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-progress-fill {
      display: block;
      height: 100%;
      border-radius: 3px;
      background: #0d9488;
      transition: width 0.2s ease;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-header-eyebrow {
      font-family: var(--font-display) !important;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-secondary);
      letter-spacing: -0.01em;
      line-height: 1.25;
      flex: 1 1 auto;
      min-width: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-card {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      border-radius: 16px;
      padding: 14px 14px 16px 14px;
      margin: 0 0 14px 0;
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.02),
        0 6px 16px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-type-badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      line-height: 1.2;
      padding: 5px 10px;
      border-radius: 20px;
      margin: 0 0 10px 0;
      letter-spacing: -0.01em;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-question {
      font-size: 17px;
      font-weight: 500;
      line-height: 1.5;
      color: var(--navy);
      margin: 0 0 8px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-question-ko {
      font-size: 12px;
      line-height: 1.45;
      color: var(--text-muted);
      margin: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-card,
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-card-top {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.02),
        0 6px 16px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-card-top {
      margin: 14px 0 0 0;
      padding: 18px 18px 14px 18px;
      border-radius: 16px 16px 0 0;
      border-bottom: none;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-head {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 10px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-ico {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
      flex-shrink: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-ico svg {
      width: 16px;
      height: 16px;
      stroke-width: 2;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-title {
      font-family: var(--font-display) !important;
      font-size: 15px;
      font-weight: 500;
      color: var(--navy);
      letter-spacing: -0.01em;
      line-height: 1.25;
      margin: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-desc {
      font-size: 12px;
      line-height: 1.45;
      color: var(--text-secondary);
      margin: 0 0 12px 36px;
    }
    @keyframes tq-wave-pulse {
      0%, 100% {
        transform: scaleY(0.35);
      }
      50% {
        transform: scaleY(1);
      }
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 56px;
      padding: 12px 14px;
      margin: 0;
      border-radius: 12px;
      background: #f4f4f5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-bars {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 3px;
      height: 36px;
      margin: 0;
      padding: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-bar {
      display: block;
      width: 4px;
      min-height: 12px;
      border-radius: 2px;
      flex-shrink: 0;
      animation: none;
      transform-origin: center center;
      background: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar {
      animation: tq-wave-pulse 1.05s ease-in-out infinite;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(1) { animation-delay: 0s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(2) { animation-delay: 0.036s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(3) { animation-delay: 0.071s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(4) { animation-delay: 0.107s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(5) { animation-delay: 0.143s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(6) { animation-delay: 0.179s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(7) { animation-delay: 0.214s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(8) { animation-delay: 0.250s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(9) { animation-delay: 0.286s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(10) { animation-delay: 0.321s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(11) { animation-delay: 0.357s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(12) { animation-delay: 0.393s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(13) { animation-delay: 0.429s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(14) { animation-delay: 0.464s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--active .tq-wave-bar:nth-child(15) { animation-delay: 0.500s; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--teal {
      background: rgba(13, 148, 136, 0.06);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--teal .tq-wave-bar {
      background: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--blue {
      background: rgba(55, 138, 221, 0.06);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--blue .tq-wave-bar {
      background: #185FA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--purple {
      background: rgba(83, 74, 183, 0.06);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--purple .tq-wave-bar {
      background: #534AB7;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--pink {
      background: rgba(217, 83, 126, 0.06);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--pink .tq-wave-bar {
      background: #993556;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--amber {
      background: rgba(186, 117, 23, 0.06);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--amber .tq-wave-bar {
      background: #854F0B;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--coral {
      background: rgba(216, 90, 48, 0.06);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-wave-slot--coral .tq-wave-bar {
      background: #993C1D;
    }
    [data-testid="stMain"]:has(.tq-screen-marker)
      div[data-testid="stElementContainer"]:has(.tq-answer-card-top) {
      margin-bottom: 0 !important;
      padding-bottom: 0 !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker)
      div[data-testid="stElementContainer"]:has(.tq-answer-card-top)
      + div[data-testid="stElementContainer"] {
      margin-top: 0 !important;
      margin-bottom: 10px !important;
      padding-top: 0 !important;
      border: 0.5px solid rgba(17, 24, 39, 0.08) !important;
      border-top: none !important;
      border-radius: 0 0 16px 16px !important;
      background: rgba(255, 255, 255, 0.98) !important;
      overflow: hidden;
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.02),
        0 6px 16px rgba(15, 23, 42, 0.04) !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker)
      div[data-testid="stElementContainer"]:has(.tq-answer-card-top)
      + div[data-testid="stElementContainer"]
      iframe[data-testid="stCustomComponentV1"],
    [data-testid="stMain"]:has(.tq-screen-marker)
      div[data-testid="stElementContainer"]:has(.tq-answer-card-top)
      + div[data-testid="stElementContainer"]
      iframe {
      border-radius: 0 0 16px 16px !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-ico--teal {
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-ico--blue {
      background: rgba(55, 138, 221, 0.12);
      color: #185FA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-ico--purple {
      background: rgba(83, 74, 183, 0.12);
      color: #534AB7;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-ico--pink {
      background: rgba(217, 83, 126, 0.12);
      color: #993556;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-ico--amber {
      background: rgba(186, 117, 23, 0.14);
      color: #854F0B;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-answer-ico--coral {
      background: rgba(216, 90, 48, 0.12);
      color: #993C1D;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip--teal .tq-topic-chip-ico {
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip--blue .tq-topic-chip-ico {
      background: rgba(55, 138, 221, 0.12);
      color: #185FA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip--purple .tq-topic-chip-ico {
      background: rgba(83, 74, 183, 0.12);
      color: #534AB7;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip--pink .tq-topic-chip-ico {
      background: rgba(217, 83, 126, 0.12);
      color: #993556;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip--amber .tq-topic-chip-ico {
      background: rgba(186, 117, 23, 0.14);
      color: #854F0B;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-topic-chip--coral .tq-topic-chip-ico {
      background: rgba(216, 90, 48, 0.12);
      color: #993C1D;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-type-badge--teal {
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-type-badge--blue {
      background: rgba(55, 138, 221, 0.12);
      color: #185FA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-type-badge--purple {
      background: rgba(83, 74, 183, 0.12);
      color: #534AB7;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-type-badge--pink {
      background: rgba(217, 83, 126, 0.12);
      color: #993556;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-type-badge--amber {
      background: rgba(186, 117, 23, 0.14);
      color: #854F0B;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-type-badge--coral {
      background: rgba(216, 90, 48, 0.12);
      color: #993C1D;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-header:has(.tq-topic-chip--teal) .tq-progress-seg--on {
      background: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-header:has(.tq-topic-chip--blue) .tq-progress-seg--on {
      background: #185FA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-header:has(.tq-topic-chip--purple) .tq-progress-seg--on {
      background: #534AB7;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-header:has(.tq-topic-chip--pink) .tq-progress-seg--on {
      background: #993556;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-header:has(.tq-topic-chip--amber) .tq-progress-seg--on {
      background: #854F0B;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-header:has(.tq-topic-chip--coral) .tq-progress-seg--on {
      background: #993C1D;
    }

    /* --- Topic / exam saved answer screen (tq-saved-*) ------------------- */
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 0 0 14px 0;
      padding: 4px 2px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-ico {
      flex-shrink: 0;
      width: 40px;
      height: 40px;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-ico svg {
      width: 22px;
      height: 22px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-text {
      font-family: var(--font-display) !important;
      font-size: 18px;
      font-weight: 600;
      color: var(--navy);
      letter-spacing: -0.02em;
      line-height: 1.25;
      margin: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      border-radius: 16px;
      padding: 14px 14px 16px 14px;
      margin: 0 0 14px 0;
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.02),
        0 6px 16px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-recording-top {
      margin-bottom: 0;
      padding-bottom: 12px;
      border-radius: 16px 16px 0 0;
      border-bottom: none;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-head {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 0 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-ico {
      flex-shrink: 0;
      width: 28px;
      height: 28px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-ico svg {
      width: 16px;
      height: 16px;
      stroke-width: 2;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-label {
      font-family: var(--font-display) !important;
      font-size: 14px;
      font-weight: 600;
      color: var(--navy);
      letter-spacing: -0.01em;
      line-height: 1.25;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-transcript {
      font-size: 14px;
      line-height: 1.55;
      color: var(--navy);
      margin: 12px 0 0 0;
      white-space: pre-wrap;
      word-break: break-word;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-transcript--empty {
      color: var(--text-muted);
      font-size: 13px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker)
      div[data-testid="stElementContainer"]:has(.tq-saved-recording-top) {
      margin-bottom: 0 !important;
      padding-bottom: 0 !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker)
      div[data-testid="stElementContainer"]:has(.tq-saved-recording-top)
      + div[data-testid="stElementContainer"] {
      margin-top: 0 !important;
      margin-bottom: 14px !important;
      padding: 8px 14px 12px 14px !important;
      border: 0.5px solid rgba(17, 24, 39, 0.08) !important;
      border-top: none !important;
      border-radius: 0 0 16px 16px !important;
      background: #ffffff !important;
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.02),
        0 6px 16px rgba(15, 23, 42, 0.04) !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker)
      div[data-testid="stElementContainer"]:has(.tq-saved-recording-top)
      + div[data-testid="stElementContainer"] {
      overflow: hidden;
    }
    [data-testid="stMain"]:has(.tq-screen-marker)
      div[data-testid="stElementContainer"]:has(.tq-saved-recording-top)
      + div[data-testid="stElementContainer"]
      iframe {
      display: block;
      width: 100%;
      border: none;
      border-radius: 0 0 12px 12px;
      min-height: 88px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-ico--teal {
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-ico--blue {
      background: rgba(55, 138, 221, 0.12);
      color: #185FA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-ico--purple {
      background: rgba(83, 74, 183, 0.12);
      color: #534AB7;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-ico--pink {
      background: rgba(217, 83, 126, 0.12);
      color: #993556;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-ico--amber {
      background: rgba(186, 117, 23, 0.14);
      color: #854F0B;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-status-ico--coral {
      background: rgba(216, 90, 48, 0.12);
      color: #993C1D;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-ico--teal {
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-ico--blue {
      background: rgba(55, 138, 221, 0.12);
      color: #185FA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-ico--purple {
      background: rgba(83, 74, 183, 0.12);
      color: #534AB7;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-ico--pink {
      background: rgba(217, 83, 126, 0.12);
      color: #993556;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-ico--amber {
      background: rgba(186, 117, 23, 0.14);
      color: #854F0B;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-section-ico--coral {
      background: rgba(216, 90, 48, 0.12);
      color: #993C1D;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-saved-actions {
      margin-top: 4px;
    }

    /* --- AI feedback screen (tq-feedback-*) — same tone as tq-saved-* with an
       emphasized, accent-tinted summary card. ----------------------------- */
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 2px 0 12px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-ico {
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-ico svg {
      width: 15px;
      height: 15px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-text {
      font-family: var(--font-display) !important;
      font-size: 14px;
      font-weight: 600;
      color: #111827;
      letter-spacing: -0.01em;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-ico--teal {
      background: rgba(13, 148, 136, 0.12); color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-ico--blue {
      background: rgba(55, 138, 221, 0.12); color: #185FA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-ico--purple {
      background: rgba(83, 74, 183, 0.12); color: #534AB7;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-ico--pink {
      background: rgba(217, 83, 126, 0.12); color: #993556;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-ico--amber {
      background: rgba(186, 117, 23, 0.14); color: #854F0B;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-label-ico--coral {
      background: rgba(216, 90, 48, 0.12); color: #993C1D;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary {
      background: rgba(13, 148, 136, 0.06);
      border: 1px solid rgba(13, 148, 136, 0.25);
      border-radius: 14px;
      padding: 14px;
      margin: 0 0 8px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary-label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.02em;
      color: #0F6E56;
      margin: 0 0 4px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary-text {
      margin: 0;
      font-size: 14px;
      line-height: 1.55;
      color: #111827;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--teal {
      background: rgba(13, 148, 136, 0.06); border-color: rgba(13, 148, 136, 0.25);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--teal .tq-feedback-summary-label { color: #0F6E56; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--blue {
      background: rgba(55, 138, 221, 0.06); border-color: rgba(55, 138, 221, 0.25);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--blue .tq-feedback-summary-label { color: #185FA5; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--purple {
      background: rgba(83, 74, 183, 0.06); border-color: rgba(83, 74, 183, 0.25);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--purple .tq-feedback-summary-label { color: #534AB7; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--pink {
      background: rgba(217, 83, 126, 0.06); border-color: rgba(217, 83, 126, 0.25);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--pink .tq-feedback-summary-label { color: #993556; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--amber {
      background: rgba(186, 117, 23, 0.07); border-color: rgba(186, 117, 23, 0.27);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--amber .tq-feedback-summary-label { color: #854F0B; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--coral {
      background: rgba(216, 90, 48, 0.06); border-color: rgba(216, 90, 48, 0.25);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary--coral .tq-feedback-summary-label { color: #993C1D; }

    /* Feedback section cards (잘한 점 / 고칠 점 / 표현 / 업그레이드 / 키워드 / 미션) */
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 14px;
      padding: 12px;
      margin: 0 0 8px 0;
      height: 100%;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-head {
      display: flex;
      align-items: center;
      gap: 6px;
      margin: 0 0 6px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico {
      flex-shrink: 0;
      width: 22px;
      height: 22px;
      border-radius: 7px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico svg {
      width: 14px;
      height: 14px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: -0.01em;
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-body {
      margin: 0;
      font-size: 13px;
      line-height: 1.55;
      color: #4b5563;
      white-space: pre-wrap;
    }
    /* Accent variants: label + icon color, and filled background. */
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--teal .tq-feedback-section-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--teal { color: #0F6E56; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--teal { background: rgba(13, 148, 136, 0.12); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--teal.tq-feedback-section--filled { background: rgba(13, 148, 136, 0.06); border-color: rgba(13, 148, 136, 0.25); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--blue .tq-feedback-section-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--blue { color: #185FA5; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--blue { background: rgba(55, 138, 221, 0.12); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--blue.tq-feedback-section--filled { background: rgba(55, 138, 221, 0.06); border-color: rgba(55, 138, 221, 0.25); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--purple .tq-feedback-section-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--purple { color: #534AB7; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--purple { background: rgba(83, 74, 183, 0.12); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--purple.tq-feedback-section--filled { background: rgba(83, 74, 183, 0.06); border-color: rgba(83, 74, 183, 0.25); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--pink .tq-feedback-section-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--pink { color: #993556; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--pink { background: rgba(217, 83, 126, 0.12); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--pink.tq-feedback-section--filled { background: rgba(217, 83, 126, 0.06); border-color: rgba(217, 83, 126, 0.25); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--amber .tq-feedback-section-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--amber { color: #854F0B; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--amber { background: rgba(186, 117, 23, 0.14); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--amber.tq-feedback-section--filled { background: rgba(186, 117, 23, 0.08); border-color: rgba(186, 117, 23, 0.27); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--coral .tq-feedback-section-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--coral { color: #993C1D; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section-ico--coral { background: rgba(216, 90, 48, 0.12); }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-section--coral.tq-feedback-section--filled { background: rgba(216, 90, 48, 0.06); border-color: rgba(216, 90, 48, 0.25); }

    /* Keyword pill chips */
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-chip {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 600;
      line-height: 1.2;
      background: #ffffff;
      border: 1px solid rgba(13, 148, 136, 0.40);
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-chip--teal { border-color: rgba(13, 148, 136, 0.40); color: #0F6E56; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-chip--blue { border-color: rgba(55, 138, 221, 0.40); color: #185FA5; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-chip--purple { border-color: rgba(83, 74, 183, 0.40); color: #534AB7; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-chip--pink { border-color: rgba(217, 83, 126, 0.40); color: #993556; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-chip--amber { border-color: rgba(186, 117, 23, 0.42); color: #854F0B; }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-chip--coral { border-color: rgba(216, 90, 48, 0.40); color: #993C1D; }
"""


def inject_global_styles() -> None:
    import streamlit as st

    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)
