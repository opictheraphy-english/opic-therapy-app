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
      --bg-page: #FAFAF9;
      --surface: #ffffff;
      --border-subtle: rgba(17, 24, 39, 0.08);
      --text: #111827;
      --text-secondary: #4b5563;
      --text-muted: #6b7280;
      --text-soft: #9ca3af;
      --color-background-primary: #ffffff;
      --color-background-secondary: #f4f4f5;
      --color-text-primary: #111827;
      --color-text-secondary: #4b5563;
      --color-text-tertiary: #9ca3af;
      --color-border-tertiary: rgba(17, 24, 39, 0.08);
      --border-radius-lg: 16px;
      --danger-soft: #fecaca;
      --danger-text: #b91c1c;
      --radius-lg: 16px;
      --radius-md: 10px;
      --radius-sm: 10px;
      --shadow-float: 0 1px 2px rgba(15, 23, 42, 0.04);
      --shadow-card: 0 1px 2px rgba(15, 23, 42, 0.04);
      --space-1: 8px;
      --space-2: 16px;
      --space-3: 20px;
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
      background: #FAFAF9 !important;
      background-color: #FAFAF9 !important;
      color: #111827 !important;
      color-scheme: light only !important;
    }

    [data-testid="stAppViewContainer"] {
      background: #FAFAF9 !important;
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
      background: #ffffff;
      border: 1px solid rgba(15, 23, 42, 0.06);
      box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02);
    }
    .topbar .tb-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 10px;
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
      font-weight: 500;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #94a3b8;
      line-height: 1.2;
    }
    .topbar .tb-title {
      font-size: 1rem;
      font-weight: 500;
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
      font-weight: 500;
      letter-spacing: -0.03em;
      color: var(--navy);
      line-height: 1.15;
      margin: 0 0 var(--space-1) 0;
    }
    .ds-hero-tag {
      font-size: 0.75rem;
      font-weight: 500;
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
      font-weight: 500;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin: var(--space-4) 0 var(--space-2) 0;
    }
    .ds-h2 {
      font-size: 1.35rem;
      font-weight: 500;
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
      padding: var(--space-3);
      border-radius: var(--radius-lg);
      border: 1px solid var(--border-subtle);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      margin-bottom: var(--space-2);
      transition: border-color 0.2s ease;
    }
    .glass-card:hover {
      border-color: rgba(13, 148, 136, 0.15);
    }

    .glass-card-quiet {
      background: #ffffff;
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
      max-width: 420px !important;
      margin: 0 auto !important;
      padding-top: 1rem !important;
      padding-bottom: 5rem !important;
      padding-left: 1rem !important;
      padding-right: 1rem !important;
    }
    section.main:has(.onb-marker) .onb-wrap,
    [data-testid="stMain"]:has(.onb-marker) .onb-wrap {
      max-width: 420px;
      margin: 0 auto;
      box-sizing: border-box;
    }
    section.main:has(.onb-marker) .onb-card,
    [data-testid="stMain"]:has(.onb-marker) .onb-card {
      background: #ffffff;
      border: 0.5px solid rgba(0, 0, 0, 0.12);
      border-radius: 16px;
      padding: 28px 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
      box-sizing: border-box;
    }
    section.main:has(.onb-marker) .onb-brand,
    [data-testid="stMain"]:has(.onb-marker) .onb-brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    section.main:has(.onb-marker) .onb-brand-icon,
    [data-testid="stMain"]:has(.onb-marker) .onb-brand-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: #E1F5EE;
      color: #0F6E56;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      overflow: hidden;
    }
    section.main:has(.onb-marker) .onb-brand-icon svg,
    [data-testid="stMain"]:has(.onb-marker) .onb-brand-icon svg {
      display: block;
      width: 40px;
      height: 40px;
    }
    section.main:has(.onb-marker) .onb-brand-text,
    [data-testid="stMain"]:has(.onb-marker) .onb-brand-text {
      font-family: var(--font-sans) !important;
      font-size: 14px;
      font-weight: 500;
      color: #0F6E56;
    }
    section.main:has(.onb-marker) .onb-copy,
    [data-testid="stMain"]:has(.onb-marker) .onb-copy {
      text-align: left;
    }
    section.main:has(.onb-marker) .onb-title-entry,
    [data-testid="stMain"]:has(.onb-marker) .onb-title-entry,
    section.main:has(.onb-marker) .stMarkdown h1.onb-title-entry,
    [data-testid="stMain"]:has(.onb-marker) .stMarkdown h1.onb-title-entry {
      font-family: var(--font-sans) !important;
      font-size: 22px !important;
      font-weight: 500 !important;
      line-height: 1.4 !important;
      margin: 0 0 8px 0 !important;
      color: #1a1a1a !important;
      text-align: left;
      letter-spacing: 0 !important;
    }
    section.main:has(.onb-marker) .onb-sub-hero,
    [data-testid="stMain"]:has(.onb-marker) .onb-sub-hero {
      font-family: var(--font-sans) !important;
      font-size: 15px;
      color: #5f5e5a;
      line-height: 1.7;
      margin: 0;
      text-align: left;
    }
    section.main:has(.onb-marker) .onb-steps,
    [data-testid="stMain"]:has(.onb-marker) .onb-steps {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin: 0;
      padding: 0;
    }
    section.main:has(.onb-marker) .onb-step-card,
    [data-testid="stMain"]:has(.onb-marker) .onb-step-card {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #f5f4f0;
      border-radius: 8px;
      padding: 12px 14px;
      box-sizing: border-box;
    }
    section.main:has(.onb-marker) .onb-step-num,
    [data-testid="stMain"]:has(.onb-marker) .onb-step-num {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #9FE1CB;
      color: #04342C;
      font-family: var(--font-sans) !important;
      font-size: 14px;
      font-weight: 500;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      line-height: 1;
    }
    section.main:has(.onb-marker) .onb-step-ico,
    [data-testid="stMain"]:has(.onb-marker) .onb-step-ico {
      color: #0F6E56;
      display: flex;
      align-items: center;
      flex-shrink: 0;
    }
    section.main:has(.onb-marker) .onb-step-ico svg,
    [data-testid="stMain"]:has(.onb-marker) .onb-step-ico svg {
      display: block;
      width: 18px;
      height: 18px;
    }
    section.main:has(.onb-marker) .onb-step-title,
    [data-testid="stMain"]:has(.onb-marker) .onb-step-title {
      font-family: var(--font-sans) !important;
      font-size: 15px;
      color: #1a1a1a;
      flex: 1;
      min-width: 0;
      line-height: 1.4;
    }
    section.main:has(.onb-marker) .onb-cta-gap {
      height: 24px;
    }
    section.main:has(.onb-marker) .onb-footnote,
    [data-testid="stMain"]:has(.onb-marker) .onb-footnote {
      font-family: var(--font-sans) !important;
      font-size: 13px;
      color: #888780;
      text-align: center;
      margin: 12px 0 0 0;
    }
    section.main:has(.onb-marker) div[data-testid="stElementContainer"] {
      max-width: 100%;
    }
    section.main:has(.onb-marker) div[data-testid="stLinkButton"] {
      width: 100%;
    }
    section.main:has(.onb-marker) div[data-testid="stLinkButton"] > a,
    section.main:has(.onb-marker) a[data-testid="stLinkButton"] {
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      gap: 8px !important;
      width: 100% !important;
      box-sizing: border-box !important;
      padding: 14px !important;
      min-height: unset !important;
      border-radius: 8px !important;
      background: #0F6E56 !important;
      color: #ffffff !important;
      font-family: var(--font-sans) !important;
      font-size: 16px !important;
      font-weight: 500 !important;
      line-height: 1.4 !important;
      text-decoration: none !important;
      border: none !important;
      box-shadow: none !important;
    }
    section.main:has(.onb-marker) div[data-testid="stLinkButton"] > a::before,
    section.main:has(.onb-marker) a[data-testid="stLinkButton"]::before {
      content: "";
      display: inline-block;
      width: 18px;
      height: 18px;
      flex-shrink: 0;
      background: center / contain no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23FFC107' d='M43.611 20.083H42V20H24v8h11.303C33.654 32.657 29.083 36 24 36c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z'/%3E%3Cpath fill='%23FF3D00' d='M6.306 14.691l6.571 4.819C14.655 16.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z'/%3E%3Cpath fill='%234CAF50' d='M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z'/%3E%3Cpath fill='%231976D2' d='M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002 6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z'/%3E%3C/svg%3E");
    }
    section.main:has(.onb-marker) div[data-testid="stButton"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] {
      width: 100%;
    }
    section.main:has(.onb-marker) div[data-testid="stButton"]:has(> button[kind="secondary"]),
    section.main:has(.onb-marker) div[data-testid="stButton"]:has(> button[data-testid="baseButton-secondary"]),
    section.main:has(.onb-marker) div[data-testid="stButton"]:has(> button[data-testid="stBaseButton-secondary"]),
    section.main:has(.onb-marker) div[data-testid="stButton"]:has(button[data-testid="stBaseButton-secondary"]),
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"]:has(> button[kind="secondary"]),
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"]:has(> button[data-testid="baseButton-secondary"]),
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"]:has(> button[data-testid="stBaseButton-secondary"]),
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"]:has(button[data-testid="stBaseButton-secondary"]) {
      margin-top: 10px;
    }
    section.main:has(.onb-marker) div[data-testid="stButton"] > button,
    section.main:has(.onb-marker) div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"],
    section.main:has(.onb-marker) div[data-testid="stButton"] button[data-testid="stBaseButton-primary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
      width: 100% !important;
      box-sizing: border-box !important;
      border-radius: 8px !important;
      min-height: unset !important;
      font-family: var(--font-sans) !important;
      letter-spacing: 0 !important;
      box-shadow: none !important;
    }
    section.main:has(.onb-marker) div[data-testid="stButton"] > button[kind="primary"],
    section.main:has(.onb-marker) div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    section.main:has(.onb-marker) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
    section.main:has(.onb-marker) div[data-testid="stButton"] button[data-testid="stBaseButton-primary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
      padding: 14px !important;
      background: #0F6E56 !important;
      color: #ffffff !important;
      border: none !important;
      font-size: 16px !important;
      font-weight: 500 !important;
    }
    section.main:has(.onb-marker) div[data-testid="stButton"] > button[kind="secondary"],
    section.main:has(.onb-marker) div[data-testid="stButton"] > button[data-testid="baseButton-secondary"],
    section.main:has(.onb-marker) div[data-testid="stButton"] > button[data-testid="stBaseButton-secondary"],
    section.main:has(.onb-marker) div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] > button[kind="secondary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] > button[data-testid="baseButton-secondary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] > button[data-testid="stBaseButton-secondary"],
    [data-testid="stMain"]:has(.onb-marker) div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] {
      padding: 12px !important;
      background: transparent !important;
      color: var(--color-text-secondary) !important;
      border: 0.5px solid rgba(17, 24, 39, 0.16) !important;
      font-size: 14px !important;
      font-weight: 500 !important;
    }
    section.main:has(.onb-marker) div[data-testid="stAlert"],
    section.main:has(.onb-marker) div[data-testid="stNotification"] {
      margin-top: 12px;
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
      background: #fafaf9 !important;
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
      flex-direction: column;
      justify-content: center;
      align-items: center;
      min-height: min(72vh, 520px);
      text-align: center;
    }
    section.main:has(.splash-marker) .splash-logo {
      line-height: 0;
    }
    section.main:has(.splash-marker) .splash-logo svg {
      display: block;
    }
    section.main:has(.splash-marker) .splash-brand {
      margin: 14px 0 0 0;
      font-size: 24px;
      font-weight: 500;
      letter-spacing: -0.02em;
      color: #111827;
    }
    section.main:has(.splash-marker) .splash-sub {
      margin: 6px 0 0 0;
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: #888780;
    }
    section.main:has(.splash-marker) .splash-line {
      margin: 18px 0 0 0;
      font-size: 14px;
      line-height: 1.55;
      font-weight: 400;
      color: #444441;
    }
    section.main:has(.splash-marker) .splash-dots {
      display: flex;
      justify-content: center;
      gap: 10px;
      margin: 16px 0 0 0;
    }
    section.main:has(.splash-marker) .splash-dots span {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: #1d9e75;
      opacity: 0.35;
      animation: splash-dot 1.05s ease-in-out infinite;
    }
    section.main:has(.splash-marker) .splash-dots span:nth-child(2) { animation-delay: 0.18s; }
    section.main:has(.splash-marker) .splash-dots span:nth-child(3) { animation-delay: 0.36s; }
    @keyframes splash-dot {
      0%, 80%, 100% { transform: scale(0.92); opacity: 0.35; }
      40% { transform: scale(1.15); opacity: 1; }
    }
    @media (prefers-reduced-motion: reduce) {
      section.main:has(.splash-marker) .splash-dots span {
        animation: none;
        opacity: 0.75;
        transform: none;
      }
    }

    /* Hero */
    .home-hero {
      border-radius: var(--radius-lg);
      padding: var(--space-4) var(--space-3);
      margin-bottom: var(--space-3);
      background: #ffffff;
      border: 1px solid var(--border-subtle);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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
      background: #ffffff;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: var(--space-2);
      text-align: left;
    }
    .metric-label { font-size: 0.7rem; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }
    .metric-value { font-size: 1.35rem; font-weight: 500; color: var(--navy); letter-spacing: -0.02em; }
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
      border-color: rgba(13, 148, 136, 0.2);
    }
    .feature-tile .ft-title { font-weight: 500; font-size: 1rem; color: var(--navy); margin-bottom: 8px; }
    .feature-tile .ft-body { font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5; }

    /* ------------------------------------------------------------------
     * Home "이어하기" (resume mock exam) card
     * ------------------------------------------------------------------ */
    .resume-card {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 18px 20px;
      border-radius: 16px;
      background: #ffffff;
      border: 1px solid rgba(13, 148, 136, 0.22);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      margin: 0 0 var(--space-3) 0;
    }
    .resume-card .rc-eyebrow {
      font-size: 0.68rem;
      font-weight: 500;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
    }
    .resume-card .rc-title {
      font-size: 1.05rem;
      font-weight: 500;
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
      border-radius: 10px;
      text-decoration: none !important;
      font-weight: 500;
      font-size: 0.95rem;
      transition: transform 0.12s ease, box-shadow 0.18s ease, background 0.18s ease;
    }
    .resume-card .rc-action.rc-primary {
      background: var(--mint);
      color: #ffffff !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .resume-card .rc-action.rc-primary:hover {
      background: #0b8076;
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
      font-weight: 500;
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

    /* --- 1) Greeting — design B card ----------------------------------- */
    .greeting-card {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 14px;
      margin: 6px 0 18px 0;
      padding: 14px 16px;
      border-radius: var(--border-radius-lg);
      background: var(--color-background-primary);
      border: 0.5px solid var(--color-border-tertiary);
      box-shadow: var(--shadow-card);
    }
    .greeting-avatar {
      flex-shrink: 0;
      width: 46px;
      height: 46px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: #E1F5EE;
      color: #0F6E56;
      font-size: 16px;
      font-weight: 500;
      line-height: 1;
      letter-spacing: -0.01em;
    }
    .greeting-body {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
      flex: 1 1 auto;
    }
    .greeting-date {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 4px;
      min-width: 0;
    }
    .greeting-date-icon {
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 14px;
      height: 14px;
      color: var(--color-text-tertiary);
    }
    .greeting-date-icon svg {
      width: 14px;
      height: 14px;
    }
    .greeting-date-text {
      font-size: 12px;
      font-weight: 400;
      color: var(--color-text-tertiary);
      line-height: 1.35;
    }
    .greeting-hello {
      font-family: var(--font-display) !important;
      font-size: 16px;
      font-weight: 500;
      color: var(--color-text-primary);
      letter-spacing: -0.01em;
      line-height: 1.3;
      margin: 0;
    }
    .greeting-brand {
      font-size: 13px;
      font-weight: 400;
      color: var(--color-text-secondary);
      line-height: 1.4;
      margin: 0;
    }
    .greeting-chip {
      flex-shrink: 0;
      align-self: center;
      white-space: nowrap;
      padding: 4px 10px;
      border-radius: 999px;
      background: #E1F5EE;
      color: #0F6E56;
      font-size: 11px;
      font-weight: 500;
      line-height: 1.35;
    }
    /* Legacy greeting (other views) ------------------------------------- */
    .greeting {
      margin: 6px 0 18px 0;
      padding: 4px 4px 0 4px;
    }
    .greeting .gr-hello {
      display: flex;
      align-items: baseline;
      gap: 10px;
      font-size: clamp(1.6rem, 5vw, 2.05rem);
      font-weight: 500;
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
      font-weight: 500;
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
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    /* --- 2) Continue Study Card (primary CTA) --------------------------- */
    .continue-card {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 22px 22px 20px 22px;
      border-radius: 16px;
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
      background: #ffffff;
      pointer-events: none;
    }
    .continue-card--resume {
      background: #ffffff;
      border: 1px solid rgba(13, 148, 136, 0.22);
      box-shadow:
        0 1px 0 rgba(15, 23, 42, 0.03),
        0 12px 32px rgba(13, 148, 136, 0.10);
    }
    .continue-card--start {
      background: #ffffff;
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
      font-weight: 500;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--mint);
    }
    .continue-card .cc-time {
      font-size: 0.78rem;
      color: var(--text-muted);
      font-weight: 500;
    }
    .continue-card .cc-title {
      font-size: 1.2rem;
      font-weight: 500;
      color: var(--navy);
      letter-spacing: -0.015em;
      line-height: 1.35;
      position: relative;
      z-index: 1;
    }
    .continue-card .cc-title .cc-of {
      font-weight: 500;
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
      font-weight: 500;
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
      background: #1D9E75;
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
      border-radius: 10px;
      text-decoration: none !important;
      font-weight: 500;
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
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .continue-card .cc-action.cc-primary:hover {
      background: #0b8076;
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
      border-radius: 16px;
      background: #ffffff;
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
      border-radius: 10px;
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
      font-weight: 500;
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
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      text-align: left;
    }
    .stat-chip .st-label {
      font-size: 0.68rem;
      font-weight: 500;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
    }
    .stat-chip .st-value {
      margin-top: 4px;
      font-size: 1.4rem;
      font-weight: 500;
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

    /* --- Home screen polish (scoped — .home-screen marker in views/home.py) --- */
    [data-testid="stMain"]:has(.home-screen) .greeting-card {
      margin: 4px 0 16px 0;
    }
    [data-testid="stMain"]:has(.home-screen) .home-section-h--quick,
    [data-testid="stMain"]:has(.home-screen) .home-section-h--stats {
      font-size: 13px;
      font-weight: 500;
      color: #444441;
      letter-spacing: 0;
      margin: 18px 0 8px 4px;
    }
    [data-testid="stMain"]:has(.home-screen) .home-section-h--quick ~ div[data-testid="stHorizontalBlock"] {
      gap: 8px !important;
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 16px;
      padding: 18px 16px;
      margin: 0 0 8px 0;
      gap: 8px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card::after {
      display: none;
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card--resume,
    [data-testid="stMain"]:has(.home-screen) .continue-card--start {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card .cc-eyebrow {
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.04em;
      text-transform: none;
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card .cc-time {
      font-size: 12px;
      font-weight: 400;
      color: #888780;
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card .cc-title {
      font-size: 16px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.01em;
      line-height: 1.4;
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card .cc-muted-num,
    [data-testid="stMain"]:has(.home-screen) .continue-card .cc-title .cc-of {
      color: #888780;
      font-weight: 500;
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card .cc-desc {
      font-size: 13px;
      font-weight: 400;
      color: #5F5E5A;
      line-height: 1.5;
      margin: 0;
    }
    [data-testid="stMain"]:has(.home-screen) .continue-card .cc-progress {
      height: 5px;
      background: #F1EFE8;
      border-radius: 999px;
      margin: 2px 0 0 0;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker {
      display: none;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stHorizontalBlock"] {
      gap: 8px !important;
      margin: 0 0 20px 0 !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button {
      border-radius: 10px !important;
      font-size: 14px !important;
      font-weight: 500 !important;
      padding: 11px 12px !important;
      min-height: 0 !important;
      box-shadow: none !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: #0F6E56 !important;
      color: #ffffff !important;
      border: 1px solid rgba(15, 110, 86, 0.35) !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[kind="primary"]:hover:not(:disabled),
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover:not(:disabled) {
      background: #0b5c47 !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):not([data-testid="stBaseButton-primary"]) {
      background: rgba(136, 135, 128, 0.10) !important;
      color: #444441 !important;
      border: 0.5px solid rgba(17, 24, 39, 0.06) !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):not([data-testid="stBaseButton-primary"]):hover:not(:disabled) {
      background: rgba(136, 135, 128, 0.16) !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stElementContainer"] div[data-testid="stButton"] > button {
      border-radius: 10px !important;
      font-size: 14px !important;
      font-weight: 500 !important;
      padding: 11px 12px !important;
      min-height: 0 !important;
      box-shadow: none !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stElementContainer"] div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stElementContainer"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: #0F6E56 !important;
      color: #ffffff !important;
      border: 1px solid rgba(15, 110, 86, 0.35) !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stElementContainer"] div[data-testid="stButton"] > button[kind="primary"]:hover:not(:disabled),
    [data-testid="stMain"]:has(.home-screen) .home-continue-actions-marker ~ div[data-testid="stElementContainer"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover:not(:disabled) {
      background: #0b5c47 !important;
    }
    [data-testid="stMain"]:has(.home-screen) .qa-card {
      padding: 14px;
      border-radius: 16px;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      box-shadow: none;
      gap: 8px;
      min-height: 0;
      transition: border-color 0.18s ease, background 0.18s ease;
    }
    [data-testid="stMain"]:has(.home-screen) .qa-card:hover {
      border-color: rgba(17, 24, 39, 0.18);
      background: #ffffff;
      box-shadow: none;
      transform: none;
    }
    [data-testid="stMain"]:has(.home-screen) .qa-card:active {
      transform: translateY(1px);
    }
    [data-testid="stMain"]:has(.home-screen) .qa-card .qa-ico {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      margin-bottom: 0;
    }
    [data-testid="stMain"]:has(.home-screen) .qa-card .qa-ico svg {
      width: 18px;
      height: 18px;
    }
    [data-testid="stMain"]:has(.home-screen) .qa-card .qa-title {
      font-size: 14px;
      font-weight: 500;
      color: #111827;
      margin-top: 0;
    }
    [data-testid="stMain"]:has(.home-screen) .qa-card .qa-sub {
      font-size: 12px;
      color: #888780;
    }
    [data-testid="stMain"]:has(.home-screen) .stats-row {
      gap: 8px;
      margin: 0 0 8px 0;
    }
    [data-testid="stMain"]:has(.home-screen) .stat-chip {
      background: #F1EFE8;
      border: none;
      border-radius: 10px;
      padding: 12px;
      box-shadow: none;
    }
    [data-testid="stMain"]:has(.home-screen) .stat-chip .st-label {
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0;
      text-transform: none;
      color: #5F5E5A;
    }
    [data-testid="stMain"]:has(.home-screen) .stat-chip .st-value {
      margin-top: 4px;
      font-size: 18px;
      font-weight: 500;
      color: #111827;
    }
    [data-testid="stMain"]:has(.home-screen) .stat-chip .st-value--level {
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.home-screen) .stat-chip .st-value--time {
      font-size: 18px;
      line-height: 1.25;
    }
    [data-testid="stMain"]:has(.home-screen) .stat-chip .st-hint {
      display: none;
    }
    @media (max-width: 390px) {
      [data-testid="stMain"]:has(.home-screen) .continue-card .cc-title {
        font-size: 15px;
      }
      [data-testid="stMain"]:has(.home-screen) .stat-chip .st-value,
      [data-testid="stMain"]:has(.home-screen) .stat-chip .st-value--time {
        font-size: 16px;
      }
    }

    /* --- Home dashboard v2 (step 1 — views/home.py) -------------------- */
    [data-testid="stMain"]:has(.home-screen) .home-dash-header {
      display: flex;
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 4px 0 14px 0;
      padding: 0 2px;
    }
    [data-testid="stMain"]:has(.home-screen) .home-dash-header-left {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 10px;
      min-width: 0;
      flex: 1 1 auto;
    }
    [data-testid="stMain"]:has(.home-screen) .home-dash-avatar {
      flex-shrink: 0;
      width: 40px;
      height: 40px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: #e1f5ee;
      color: #0f6e56;
      font-size: 15px;
      font-weight: 500;
      line-height: 1;
    }
    [data-testid="stMain"]:has(.home-screen) .home-dash-header-text {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    [data-testid="stMain"]:has(.home-screen) .home-dash-hello {
      font-size: 16px;
      font-weight: 500;
      color: #111827;
      line-height: 1.35;
      letter-spacing: -0.01em;
    }
    [data-testid="stMain"]:has(.home-screen) .home-dash-date {
      font-size: 12px;
      font-weight: 400;
      color: #888780;
      line-height: 1.3;
    }
    [data-testid="stMain"]:has(.home-screen) .home-dash-streak {
      flex-shrink: 0;
      display: inline-flex;
      flex-direction: row;
      align-items: center;
      gap: 4px;
      padding: 6px 10px;
      border-radius: 999px;
      background: #fff4e3;
      color: #854f0b;
      font-size: 12px;
      font-weight: 500;
      line-height: 1;
      white-space: nowrap;
    }
    [data-testid="stMain"]:has(.home-screen) .home-dash-streak-ico {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #d97706;
    }
    [data-testid="stMain"]:has(.home-screen) .home-progress-card {
      background: #ffffff;
      border: 1px solid #e5e7e2;
      border-radius: 16px;
      padding: 16px;
      margin: 0 0 12px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.home-screen) .home-progress-card--guest,
    [data-testid="stMain"]:has(.home-screen) .home-progress-card--loading {
      padding: 14px 16px;
    }
    [data-testid="stMain"]:has(.home-screen) .home-guest-stats-line {
      margin: 0;
      font-size: 13.5px;
      font-weight: 500;
      color: #5f6b64;
      line-height: 1.45;
      text-align: center;
    }
    [data-testid="stMain"]:has(.home-screen) .home-progress-card-inner {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    [data-testid="stMain"]:has(.home-screen) .home-progress-donut-wrap {
      flex-shrink: 0;
    }
    [data-testid="stMain"]:has(.home-screen) .home-progress-meta {
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 0;
      flex: 1 1 160px;
    }
    [data-testid="stMain"]:has(.home-screen) .home-progress-tagline {
      font-size: 13.5px;
      font-weight: 500;
      color: #111827;
      line-height: 1.4;
    }
    [data-testid="stMain"]:has(.home-screen) .home-week-bars {
      display: flex;
      flex-direction: row;
      align-items: flex-end;
      gap: 5px;
      height: 36px;
    }
    [data-testid="stMain"]:has(.home-screen) .home-week-bar {
      flex: 1 1 0;
      min-width: 0;
      border-radius: 4px 4px 2px 2px;
      background: #d7ece2;
    }
    [data-testid="stMain"]:has(.home-screen) .home-week-bar--recent {
      background: #1d9e75;
    }
    [data-testid="stMain"]:has(.home-screen) .home-week-bar--empty {
      background: #eceee9;
    }
    [data-testid="stMain"]:has(.home-screen) .home-progress-stats {
      font-size: 11px;
      font-weight: 400;
      color: #888780;
      line-height: 1.3;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-head {
      display: flex;
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 12px 14px;
      background: #0f6e56;
      color: #ffffff;
      border: 1px solid #d9e6df;
      border-bottom: none;
      border-radius: 16px 16px 0 0;
      overflow: hidden;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-head-left {
      display: inline-flex;
      flex-direction: row;
      align-items: center;
      gap: 6px;
      font-size: 14px;
      font-weight: 500;
      line-height: 1.2;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-target-ico {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      opacity: 0.95;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-head-count {
      font-size: 11.5px;
      font-weight: 500;
      color: #bfe4d4;
      white-space: nowrap;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-row {
      background: #ffffff;
      border-left: 1px solid #d9e6df;
      border-right: 1px solid #d9e6df;
      box-shadow: none;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-row {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 10px;
      padding: 12px 14px;
      border-top: 1px dashed #e5ece8;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-check {
      flex-shrink: 0;
      width: 21px;
      height: 21px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-check--done {
      background: #1d9e75;
      border: none;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-check--open {
      border: 1.5px solid #cfe0d7;
      background: #ffffff;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-row-text {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
      flex: 1 1 auto;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-title {
      font-size: 14px;
      font-weight: 500;
      color: #111827;
      line-height: 1.35;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-title--done {
      color: #888780;
      text-decoration: line-through;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-sub {
      font-size: 12px;
      font-weight: 400;
      color: #888780;
      line-height: 1.3;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-interactive-marker {
      display: none !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-interactive-marker
      + div[data-testid="stHorizontalBlock"] {
      margin: 0 !important;
      padding: 0 !important;
      border-left: 1px solid #d9e6df;
      border-right: 1px solid #d9e6df;
      border-top: 1px dashed #e5ece8;
      background: #ffffff;
      align-items: center !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-interactive-marker
      + div[data-testid="stHorizontalBlock"] [data-testid="column"],
    [data-testid="stMain"]:has(.home-screen) .home-goals-interactive-marker
      + div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"] {
      display: flex;
      align-items: center;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-interactive-marker
      + div[data-testid="stHorizontalBlock"] [data-testid="column"]:first-child .home-goals-row,
    [data-testid="stMain"]:has(.home-screen) .home-goals-interactive-marker
      + div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"]:first-child .home-goals-row {
      border: none !important;
      padding: 12px 0 12px 14px;
    }
    [data-testid="stMain"]:has(.home-screen) .home-goals-strip {
      padding: 10px 14px;
      border: 1px solid #d9e6df;
      border-top: 0.5px solid #e5ece8;
      border-radius: 0 0 16px 16px;
      background: #fafcfb;
      font-size: 11px;
      font-weight: 400;
      color: #5f6b64;
      line-height: 1.45;
      margin: 0 0 12px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.home-screen) .home-shortcut-card {
      display: flex;
      flex-direction: row;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 48px;
      padding: 12px 10px;
      background: #ffffff;
      border: 1px solid #e5e7e2;
      border-radius: 12px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.home-screen) .home-shortcut-ico {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #0f6e56;
      flex-shrink: 0;
    }
    [data-testid="stMain"]:has(.home-screen) .home-shortcut-label {
      font-size: 13px;
      font-weight: 500;
      color: #111827;
      line-height: 1.2;
      white-space: nowrap;
    }
    [data-testid="stMain"]:has(.home-screen) .home-shortcuts-marker {
      display: none !important;
    }
    [data-testid="stMain"]:has(.home-screen) .home-shortcuts-marker
      ~ div[data-testid="stHorizontalBlock"] {
      gap: 8px !important;
      margin: 0 0 8px 0 !important;
    }
    [data-testid="stMain"]:has(.home-screen) div[data-testid="stElementContainer"].st-key-home_goal_topic
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.home-screen) div[data-testid="stElementContainer"].st-key-home_goal_script
      div[data-testid="stButton"] > button {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      color: #0f6e56 !important;
      font-size: 13px !important;
      font-weight: 500 !important;
      padding: 0.35rem 0.5rem !important;
      min-height: 0 !important;
    }
    [data-testid="stMain"]:has(.home-screen) div[data-testid="stElementContainer"].st-key-home_shortcut_history
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.home-screen) div[data-testid="stElementContainer"].st-key-home_shortcut_pattern
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.home-screen) div[data-testid="stElementContainer"].st-key-home_shortcut_scripts
      div[data-testid="stButton"] > button {
      background: #ffffff !important;
      border: 1px solid #e5e7e2 !important;
      box-shadow: none !important;
      color: #0f6e56 !important;
      font-size: 12px !important;
      font-weight: 500 !important;
      min-height: 34px !important;
      padding: 0.25rem 0.5rem !important;
      margin-top: 6px !important;
    }
    @media (max-width: 390px) {
      [data-testid="stMain"]:has(.home-screen) .home-progress-card-inner {
        flex-direction: column;
        align-items: stretch;
      }
      [data-testid="stMain"]:has(.home-screen) .home-progress-donut-wrap {
        display: flex;
        justify-content: center;
      }
      [data-testid="stMain"]:has(.home-screen) .home-shortcut-label {
        font-size: 12px;
      }
    }

    /* ==================================================================
     * Mock-exam recovery card — analysis failure / retry surfaces.
     * Scoped to mock (mx-marker), topic practice (tq-screen-marker),
     * and mini report wrap only.
     * ================================================================== */
    section.main:has(.mx-marker) .recovery-card,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card,
    .mm-report-wrap .recovery-card {
      margin: 6px 0 16px 0;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 16px;
      overflow: hidden;
    }
    section.main:has(.mx-marker) .recovery-card .rv-stage,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-stage,
    .mm-report-wrap .recovery-card .rv-stage {
      background: #F1EFE8;
      padding: 22px 18px 14px;
      text-align: center;
    }
    section.main:has(.mx-marker) .recovery-card .rv-stage svg,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-stage svg,
    .mm-report-wrap .recovery-card .rv-stage svg {
      display: block;
      margin: 0 auto;
    }
    section.main:has(.mx-marker) .recovery-card .rv-content,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-content,
    .mm-report-wrap .recovery-card .rv-content {
      padding: 16px 18px 20px;
      text-align: center;
    }
    section.main:has(.mx-marker) .recovery-card .rv-eyebrow,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-eyebrow,
    .mm-report-wrap .recovery-card .rv-eyebrow {
      margin: 0 0 6px 0;
      font-size: 12px;
      font-weight: 500;
      color: #854F0B;
      letter-spacing: -0.01em;
    }
    section.main:has(.mx-marker) .recovery-card .rv-title,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-title,
    .mm-report-wrap .recovery-card .rv-title {
      margin: 0 0 10px 0;
      font-size: 16px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.02em;
      line-height: 1.35;
    }
    section.main:has(.mx-marker) .recovery-card--compact .rv-title,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card--compact .rv-title,
    .mm-report-wrap .recovery-card--compact .rv-title {
      font-size: 15px;
    }
    section.main:has(.mx-marker) .recovery-card .rv-body,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-body,
    .mm-report-wrap .recovery-card .rv-body {
      margin: 0;
      font-size: 13px;
      color: #5F5E5A;
      line-height: 1.6;
    }
    section.main:has(.mx-marker) .recovery-card .rv-body .rv-emphasis,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-body .rv-emphasis,
    .mm-report-wrap .recovery-card .rv-body .rv-emphasis {
      color: #0F6E56;
      font-weight: 500;
    }
    section.main:has(.mx-marker) .recovery-card .rv-meta,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-meta,
    .mm-report-wrap .recovery-card .rv-meta {
      margin-top: 12px;
      font-size: 11px;
      color: #888780;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: 4px 6px;
    }
    section.main:has(.mx-marker) .recovery-card .rv-meta .rv-sep,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card .rv-meta .rv-sep,
    .mm-report-wrap .recovery-card .rv-meta .rv-sep {
      color: #888780;
    }
    section.main:has(.mx-marker) .rv-retry-caption,
    [data-testid="stMain"]:has(.tq-screen-marker) .rv-retry-caption,
    .mm-report-wrap .rv-retry-caption {
      margin: 8px 0 0 0;
      font-size: 11px;
      color: #888780;
      text-align: center;
      line-height: 1.45;
    }
    section.main:has(.mx-marker) .recovery-card--plain,
    [data-testid="stMain"]:has(.tq-screen-marker) .recovery-card--plain {
      padding: 16px 18px;
      border-style: dashed;
      opacity: 0.95;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-screen-marker) div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
      background: #0F6E56 !important;
      color: #ffffff !important;
      border-color: transparent !important;
    }

    /* ------------------------------------------------------------------
     * Smart feedback cards — grammar fix + alternative expressions
     * ------------------------------------------------------------------ */
    .grammar-fix,
    .coach-gf-card {
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 12px 14px;
      margin: 6px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    /* Script-coaching report — text sections wrapped in the same boxed style. */
    .sc-report-card {
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 13px 15px;
      margin: 8px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .sc-report-card .sc-card-title {
      font-size: 0.82rem;
      font-weight: 500;
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
    .sc-report-card .sc-q { font-weight: 500; color: #0f172a; }
    .sc-report-card .sc-script { color: #334155; white-space: pre-wrap; }
    /* Script coaching upgrade — before/after script blocks */
    [data-testid="stMain"]:has(.sc-upgrade-ba-marker) .sc-ba-block {
      margin: 0 0 14px 0;
    }
    [data-testid="stMain"]:has(.sc-upgrade-ba-marker) .sc-ba-label {
      font-size: 12px;
      font-weight: 500;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: #888780;
      margin: 0 0 6px 0;
    }
    [data-testid="stMain"]:has(.sc-upgrade-ba-marker) .sc-ba-label--accent {
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.sc-upgrade-ba-marker) .sc-ba-original {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.sc-upgrade-ba-marker) .sc-ba-original p {
      margin: 0;
      font-size: 14px;
      font-weight: 400;
      line-height: 1.65;
      white-space: pre-wrap;
      word-break: break-word;
      color: #5F5E5A;
    }
    [data-testid="stMain"]:has(.sc-upgrade-ba-marker) .sc-ba-upgraded {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-left: 2px solid #5DCAA5;
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.sc-upgrade-ba-marker) .sc-ba-upgraded p {
      margin: 0;
      font-size: 14px;
      font-weight: 400;
      line-height: 1.65;
      white-space: pre-wrap;
      word-break: break-word;
      color: #111827;
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
      font-weight: 500;
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
      font-weight: 500;
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
      font-weight: 500;
    }
    section.main:has(.mx-marker) .mx-coach-empty-note {
      font-size: 0.86rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 4px 0 12px 0;
    }
    section.main:has(.mx-marker) .mx-coach-struct {
      padding: 12px 14px;
      border-radius: 10px;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      margin-bottom: 8px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    section.main:has(.mx-marker) .mx-coach-struct-label {
      font-size: 12px;
      font-weight: 500;
      color: #534AB7;
      margin: 10px 0 4px 0;
      text-transform: none;
      letter-spacing: 0;
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
      font-size: 13px;
      line-height: 1.7;
      color: #444441;
      padding: 12px 14px 12px 12px;
      border-radius: 0;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      border-left: 2px solid #5DCAA5;
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
      border-radius: 10px;
      padding: 12px 14px;
      margin: 6px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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
      font-weight: 500;
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
      font-weight: 500;
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
      font-weight: 500;
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
      background: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.75);
      border-radius: 16px;
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
      border-radius: 16px;
      background: transparent;
      cursor: pointer;
      font-family: inherit;
      color: var(--text-soft);
      font-size: 0.58rem;
      font-weight: 500;
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
    .stButton > button,
    .stButton button[data-testid="stBaseButton-secondary"] {
      border-radius: var(--radius-md) !important;
      font-weight: 500 !important;
      border: 0.5px solid rgba(17, 24, 39, 0.06) !important;
      background: rgba(136, 135, 128, 0.10) !important;
      color: #444441 !important;
      transition: transform 0.15s ease, box-shadow 0.2s ease, background 0.2s ease !important;
    }
    .stButton > button:hover:not(:disabled),
    .stButton button[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {
      background: rgba(136, 135, 128, 0.16) !important;
      color: #444441 !important;
      border-color: rgba(17, 24, 39, 0.06) !important;
    }

    [data-testid="stTabs"] button[data-baseweb="tab"] {
      font-weight: 500 !important;
      letter-spacing: -0.01em;
    }

    .survey-label { font-size: 1.05rem; font-weight: 500; color: var(--navy); margin-top: var(--space-3); }

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
     * Pattern screen — flat drill UX (scoped via ``.pat-screen-marker``).
     * ================================================================== */

    .pat-screen-marker {
      display: none !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) {
      max-width: 720px;
      margin-left: auto;
      margin-right: auto;
      padding: 0 4px;
      box-sizing: border-box;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) [data-testid="column"],
    [data-testid="stMain"]:has(.pat-screen-marker) [data-testid="stHorizontalBlock"] {
      max-width: 100%;
    }

    /* --- Header (text only) ----------------------------------------- */
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-hero {
      margin: 4px 0 14px 0;
      padding: 0;
      background: transparent;
      border: none;
      box-shadow: none;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-hero .pat-title {
      font-size: 18px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.02em;
      line-height: 1.3;
      margin: 0 0 4px 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-hero .pat-sub {
      font-size: 12px;
      font-weight: 400;
      color: #888780;
      line-height: 1.45;
      margin: 0;
    }

    /* --- Segment control tabs (st.radio horizontal) ------------------- */
    .pat-tab-radio-marker {
      display: none !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"]) {
      margin: 0 0 16px 0;
      padding: 3px;
      background: #F1EFE8;
      border: none;
      border-radius: 999px;
      box-shadow: none;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] {
      margin: 0 !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] > div {
      flex-direction: row !important;
      flex-wrap: nowrap !important;
      gap: 2px !important;
      align-items: stretch !important;
      justify-content: stretch !important;
      width: 100%;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] label {
      flex: 1 1 0 !important;
      min-width: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      background: transparent !important;
      border: none !important;
      justify-content: center !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] label > div:first-child {
      display: none !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] label p,
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] label span {
      font-size: 12px !important;
      font-weight: 400 !important;
      color: #5F5E5A !important;
      line-height: 1.2 !important;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span {
      color: #0F6E56 !important;
      font-weight: 500 !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] label:has(input:checked) {
      background: #ffffff !important;
      border-radius: 999px !important;
      padding: 7px 6px !important;
      box-shadow: none;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
      + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
      [data-testid="stRadio"] label:not(:has(input:checked)) {
      padding: 7px 6px !important;
      border-radius: 999px !important;
    }

    /* --- Section headers (toggle row container + overlay button) ----- */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-sec-toggle-row) {
      position: relative;
      width: 100%;
      margin: 0 0 8px 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-sec-head--open) {
      margin-bottom: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-toggle-row {
      margin: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 0;
      padding: 14px 16px;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 14px;
      box-shadow: none;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-head--open {
      border-color: rgba(15, 110, 86, 0.30);
      margin-bottom: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-title {
      flex: 1 1 auto;
      min-width: 0;
      font-size: 14px;
      font-weight: 500;
      color: #111827 !important;
      letter-spacing: 0;
      line-height: 1.35;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-meta {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
      margin-left: 4px;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 1.25rem;
      font-size: 12px;
      font-weight: 500;
      color: #0F6E56;
      background: #E1F5EE;
      border: none;
      padding: 3px 10px;
      border-radius: 999px;
      line-height: 1.2;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-chev {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1rem;
      font-size: 12px;
      line-height: 1;
      color: #888780;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-body {
      margin: 8px 0 8px 0;
      padding: 0;
      background: transparent;
      border: none;
      border-radius: 0;
      box-shadow: none;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-sec-toggle-row)
      > div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]) {
      position: absolute !important;
      inset: 0 !important;
      height: 100% !important;
      z-index: 2 !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-sec-toggle-row)
      > div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"])
      div[data-testid="stButton"] {
      width: 100% !important;
      height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-sec-toggle-row)
      > div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"])
      div[data-testid="stButton"] > button {
      width: 100% !important;
      height: 100% !important;
      min-height: 2rem !important;
      margin: 0 !important;
      padding: 0 !important;
      border: none !important;
      border-radius: 14px !important;
      background: transparent !important;
      box-shadow: none !important;
      color: transparent !important;
      cursor: pointer !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-head,
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-sec-head * {
      pointer-events: none !important;
    }

    /* --- Pattern cards (visual surface) ------------------------------- */
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card-shell--tap {
      margin: 0 0 8px 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card-shell--tap:has(.pat-card--header-open) {
      margin-bottom: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card--header {
      position: relative;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 14px;
      padding: 13px 14px;
      box-shadow: none;
      color: inherit !important;
      margin: 0;
      pointer-events: none;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card--header-open {
      border-color: rgba(15, 110, 86, 0.30);
      border-radius: 14px 14px 0 0;
      border-bottom: none;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card-detail-wrap {
      margin: 0 0 8px 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card-detail {
      background: #ffffff;
      border: 0.5px solid rgba(15, 110, 86, 0.30);
      border-top: none;
      border-radius: 0 0 14px 14px;
      padding: 12px 14px 14px 14px;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card-main {
      flex: 1 1 auto;
      min-width: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card-en {
      font-size: 14px;
      font-weight: 500;
      color: #111827;
      line-height: 1.45;
      margin: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card-ko {
      font-size: 12px;
      font-weight: 400;
      color: #888780;
      line-height: 1.45;
      margin: 4px 0 0 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-card-chevron {
      flex-shrink: 0;
      width: 28px;
      height: 28px;
      border-radius: 999px;
      background: #E1F5EE;
      color: #0F6E56;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      line-height: 1;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-pattern-label {
      font-size: 11px;
      font-weight: 500;
      color: #0F6E56;
      margin: 0 0 6px 0;
      padding-right: 36px;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-pattern-en {
      font-size: 16px;
      font-weight: 500;
      color: #111827;
      line-height: 1.4;
      margin: 0 0 6px 0;
      padding-right: 36px;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-pattern-meaning {
      font-size: 13px;
      font-weight: 400;
      color: #444441;
      line-height: 1.5;
      margin: 0 0 4px 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-pattern-usage {
      font-size: 12px;
      font-weight: 400;
      color: #888780;
      line-height: 1.45;
      margin: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-divider {
      border: none;
      border-top: 0.5px solid rgba(17, 24, 39, 0.08);
      margin: 12px 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-ex-block {
      margin: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-ex-label {
      font-size: 11px;
      font-weight: 500;
      color: #0F6E56;
      margin: 0 0 6px 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-ex-label--purple {
      color: #534AB7;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-ex-en {
      font-size: 14px;
      color: #111827;
      line-height: 1.55;
      margin: 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-ex-en--500 {
      font-weight: 500;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-ex-en--400 {
      font-weight: 400;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-ex-ko {
      font-size: 12px;
      font-weight: 400;
      color: #888780;
      line-height: 1.45;
      margin: 4px 0 0 0;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) .pat-nuance {
      margin-top: 12px;
      background: #F1EFE8;
      border-radius: 10px;
      padding: 9px 12px;
      font-size: 12px;
      font-weight: 400;
      color: #5F5E5A;
      line-height: 1.55;
    }

    /* Pattern tap column — header shell + one transparent toggle (tp-card clone).
       Only .pat-card-shell--tap columns get overlay rules; detail/buttons are outside. */
    /* Positioning anchor for the absolute overlay button. Both the column and
       its vertical block are made relative so inset:0 always sizes to the card
       even if Streamlit's wrapper nesting changes. */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap) {
      position: relative;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      > [data-testid="stVerticalBlock"] {
      position: relative;
      gap: 0 !important;
      height: auto !important;
    }
    /* Let the card's containers grow to the card's true height so the overlay
       (sized to the column) covers the whole card — not a flex-clipped strip. */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap) {
      align-self: flex-start !important;
      height: auto !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      div[data-testid="stElementContainer"]:has(.pat-card-shell--tap) {
      height: auto !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      div[data-testid="stMarkdown"]:has(.pat-card-shell--tap) {
      margin-bottom: 0 !important;
    }
    /* The markdown container ships a negative bottom margin (-1rem) that pulls
       the card up and shrinks its element-container's reported height (58→42),
       which previously starved the overlay. Zero it so the column wraps the
       full card and the overlay covers all of it. */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      div[data-testid="stMarkdownContainer"]:has(.pat-card-shell--tap) {
      margin-bottom: 0 !important;
    }
    /* The whole card visual (wrapper + card + every child) must NOT capture
       clicks — all clicks fall through to the transparent overlay button so
       the entire card surface is tappable, not just the arrow. */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      div[data-testid="stElementContainer"]:has(.pat-card-shell--tap),
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      div[data-testid="stMarkdown"]:has(.pat-card-shell--tap),
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap) .pat-card--header,
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap) .pat-card--header * {
      pointer-events: none !important;
    }
    /* Streamlit sets .element-container { position: relative } by default, which
       would trap an absolute stButton inside its own (collapsed, 0-height)
       wrapper. So make the button's element-container ITSELF the overlay layer,
       sized to the column, and let the inner button fill it. */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-card-shell--tap)
      > div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]) {
      position: absolute !important;
      inset: 0 !important;
      height: 100% !important;
      z-index: 3 !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-card-shell--tap)
      div[data-testid="stButton"] {
      position: static !important;
      width: 100% !important;
      height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stVerticalBlock"]:has(.pat-card-shell--tap)
      div[data-testid="stButton"]
      > button {
      width: 100% !important;
      height: 100% !important;
      min-height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      border: none !important;
      border-radius: 16px !important !important;
      background: transparent !important;
      box-shadow: none;
      color: transparent !important;
      cursor: pointer !important;
      pointer-events: auto !important;
    }
    /* Lift the card when the overlay button is hovered/focused (desktop). */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .pat-card--header,
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .pat-card--header {
      border-color: rgba(13, 148, 136, 0.35) !important;
    }
    /* Hover: nudge the arrow right + fill its circle a touch. */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .pat-card--header .pat-card-chevron {
      transform: translateX(2px);
    }
    /* Tap feedback (mobile + desktop): press the card in slightly. */
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:active)
      .pat-card--header {
      transform: translateY(0) scale(0.985);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.pat-screen-marker)
      div[data-testid="stColumn"]:has(.pat-card-shell--tap)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:active)
      .pat-card--header .pat-card-chevron {
      transform: translateX(1px) scale(0.94);
    }

    /* Expanded card action buttons (not overlay) ----------------------- */
    [data-testid="stMain"]:has(.pat-screen-marker) div[data-testid="stButton"]:has(button[key*="pat_ex_toggle"]),
    [data-testid="stMain"]:has(.pat-screen-marker) div[data-testid="stButton"]:has(button[key*="pat_detail_close"]) {
      margin-top: 0 !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) div[data-testid="stHorizontalBlock"]:has(button[key*="pat_detail_close"]) {
      margin-top: 8px !important;
      gap: 8px !important;
    }
    [data-testid="stMain"]:has(.pat-screen-marker) div[data-testid="stButton"]:has(button[key*="pat_ex_toggle"]) > button,
    [data-testid="stMain"]:has(.pat-screen-marker) div[data-testid="stButton"]:has(button[key*="pat_detail_close"]) > button {
      min-height: 2.35rem !important;
      padding: 8px 12px !important;
      border-radius: 10px !important;
      font-size: 13px !important;
      font-weight: 500 !important;
      color: #444441 !important;
      background: #ffffff !important;
      border: 0.5px solid #D3D1C7 !important;
      box-shadow: none !important;
    }

    @media (max-width: 480px) {
      [data-testid="stMain"]:has(.pat-screen-marker)
        div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
        + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
        [data-testid="stRadio"] label p,
      [data-testid="stMain"]:has(.pat-screen-marker)
        div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
        + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
        [data-testid="stRadio"] label span {
        font-size: 11px !important;
      }
      [data-testid="stMain"]:has(.pat-screen-marker)
        div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
        + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
        [data-testid="stRadio"] label:has(input:checked),
      [data-testid="stMain"]:has(.pat-screen-marker)
        div[data-testid="stElementContainer"]:has(.pat-tab-radio-marker)
        + div[data-testid="stElementContainer"]:has([data-testid="stRadio"])
        [data-testid="stRadio"] label:not(:has(input:checked)) {
        padding: 7px 4px !important;
      }
    }

    /* Shared collapsible sections (mock survey / report) */
    .mx-survey-head,
    .mx-col-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin: 0 0 6px 0;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .mx-survey-title,
    .mx-col-title {
      font-size: 0.95rem;
      font-weight: 500;
      color: #111827 !important;
      letter-spacing: -0.01em;
      line-height: 1.35;
    }
    .mx-survey-count,
    .mx-col-count {
      flex-shrink: 0;
      font-size: 0.78rem;
      font-weight: 500;
      color: #0f766e;
      background: rgba(204, 251, 241, 0.65);
      border: 1px solid rgba(13, 148, 136, 0.18);
      padding: 4px 10px;
      border-radius: 999px;
    }
    .mx-survey-body,
    .mx-col-body {
      margin: 0 0 12px 0;
      padding: 12px 12px 4px 12px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid rgba(13, 148, 136, 0.16);
      border-radius: var(--radius-md);
    }
    section.main:has(.mx-marker) .mx-survey-head--open,
    section.main:has(.mx-marker) .mx-col-head--open {
      border-color: rgba(13, 148, 136, 0.22);
    }

    /* --- Topic practice: selection screen (filters + compact cards) ----- */
    .tp-select-intro {
      margin-bottom: 4px;
    }
    .tp-select-summary {
      margin: 10px 0 0 0;
      font-size: 0.84rem;
      font-weight: 500;
      color: var(--text-muted);
      letter-spacing: -0.01em;
    }
    /* --- Final report preview (real mock completion) ------------------- */
    .mx-fr-preview {
      margin: 16px 0 18px 0;
      padding: 16px 18px;
      border-radius: 16px;
      background: #ffffff;
      border: 1px solid rgba(13, 148, 136, 0.18);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .mx-frp-eyebrow {
      margin: 0 0 12px 0;
      font-size: 1.05rem;
      font-weight: 500;
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
      font-weight: 500;
    }
    .mx-frp-val {
      font-weight: 500;
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
      font-weight: 500;
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
    /* --- Final report completion hero (mock v2 report) ------------- */
    .mx-fr-hero {
      margin: 16px 0 18px 0;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 16px;
      overflow: hidden;
    }
    .mx-fr-hero-stage {
      background: #E1F5EE;
      padding: 24px 18px 16px;
      text-align: center;
    }
    .mx-fr-celebration-scene {
      display: block;
      width: min(240px, 100%);
      height: auto;
      margin: 0 auto;
    }
    .mx-fr-hero-body {
      padding: 18px 18px 20px;
      text-align: center;
    }
    .mx-fr-hero-eyebrow {
      margin: 0 0 6px 0;
      font-size: 12px;
      font-weight: 500;
      color: #0F6E56;
      letter-spacing: -0.01em;
    }
    .mx-fr-hero-title {
      margin: 0 0 14px 0;
      font-size: 18px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.02em;
      line-height: 1.35;
    }
    .mx-fr-hero-grade {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin: 0 auto 14px auto;
      padding: 8px 18px;
      border-radius: 999px;
      background: #E1F5EE;
    }
    .mx-fr-hero-grade-label {
      font-size: 12px;
      color: #085041;
    }
    .mx-fr-hero-grade-value {
      font-size: 20px;
      font-weight: 500;
      color: #04342C;
      letter-spacing: -0.02em;
    }
    .mx-fr-hero-pending {
      margin: 0 0 14px 0;
      font-size: 0.84rem;
      color: #0f766e;
      line-height: 1.45;
    }
    .mx-fr-hero-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
      margin: 0 0 4px 0;
    }
    .mx-fr-hero-chip {
      flex: 1 1 88px;
      min-width: 88px;
      max-width: 140px;
      padding: 10px;
      border-radius: 10px;
      background: #F1EFE8;
      text-align: center;
    }
    .mx-fr-hero-chip-label {
      display: block;
      margin: 0 0 4px 0;
      font-size: 11px;
      color: #5F5E5A;
      line-height: 1.3;
    }
    .mx-fr-hero-chip-val {
      display: block;
      font-size: 15px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.01em;
    }
    .mx-fr-hero-note {
      margin: 12px 0 0 0;
      font-size: 0.88rem;
      color: #475569;
      line-height: 1.55;
      white-space: pre-wrap;
    }
    .mx-fr-progress {
      margin: 0 0 14px 0;
      padding: 10px 14px;
      border-radius: 10px;
      background: var(--mint-muted);
      border: 1px solid rgba(13, 148, 136, 0.12);
    }
    .mx-fr-progress-title {
      margin: 0;
      font-size: 0.72rem;
      font-weight: 500;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
    }
    .mx-fr-progress-line {
      margin: 4px 0 0 0;
      font-size: 1rem;
      font-weight: 500;
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
      font-weight: 500;
    }
    .tp-filter-label {
      font-size: 0.72rem;
      font-weight: 500;
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
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .tp-topic-title {
      font-size: 1.02rem;
      font-weight: 500;
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
      font-weight: 500;
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

    /* --- Learning portal v2 (grid — views/mock_exam.py render_learning_portal) --- */
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-header {
      display: flex;
      flex-direction: row;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin: 2px 0 14px 0;
      padding: 0 2px;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-header-left {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
      flex: 1 1 auto;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-title {
      font-size: 18px;
      font-weight: 500;
      color: #111827;
      line-height: 1.35;
      letter-spacing: -0.01em;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-subtitle {
      font-size: 12.5px;
      font-weight: 400;
      color: #8a948d;
      line-height: 1.4;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-target-pill {
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      padding: 6px 11px;
      border-radius: 999px;
      background: #eefaf5;
      border: 1px solid #b9e7d6;
      color: #0f6e56;
      font-size: 12px;
      font-weight: 500;
      line-height: 1;
      white-space: nowrap;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-hero-marker,
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-grid-marker {
      display: none !important;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-hero-card {
      display: flex;
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      background: #0f6e56;
      border-radius: 16px;
      padding: 16px 18px;
      margin: 0 0 6px 0;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-hero-card-left {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 12px;
      min-width: 0;
      flex: 1 1 auto;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-hero-icon {
      flex-shrink: 0;
      width: 40px;
      height: 40px;
      border-radius: 11px;
      background: #1d9e75;
      color: #ffffff;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-hero-icon svg {
      width: 22px;
      height: 22px;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-hero-card-text {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-hero-card-title {
      font-size: 15px;
      font-weight: 500;
      color: #ffffff;
      line-height: 1.35;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-hero-card-sub {
      font-size: 12px;
      font-weight: 400;
      color: #bfe4d4;
      line-height: 1.35;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-hero-card-arrow {
      flex-shrink: 0;
      width: 32px;
      height: 32px;
      border-radius: 999px;
      background: #ffffff;
      color: #0f6e56;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) div[data-testid="stElementContainer"].st-key-learn_hero_mock
      div[data-testid="stButton"] > button {
      background: #ffffff !important;
      border: 1px solid #cfe0d7 !important;
      box-shadow: none !important;
      color: #0f6e56 !important;
      font-size: 13px !important;
      font-weight: 500 !important;
      min-height: 38px !important;
      margin: 0 0 12px 0 !important;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-grid-marker
      ~ div[data-testid="stHorizontalBlock"] {
      gap: 10px !important;
      margin: 0 0 10px 0 !important;
      align-items: stretch !important;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: #ffffff;
      border: 0.5px solid #e5e7e2;
      border-radius: 14px;
      padding: 15px;
      min-height: 118px;
      margin: 0 0 6px 0;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-card-top {
      display: flex;
      flex-direction: row;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-icon {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: #e1f5ee;
      color: #0f6e56;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-icon svg {
      width: 20px;
      height: 20px;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-badge {
      flex-shrink: 0;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 10.5px;
      font-weight: 500;
      line-height: 1.2;
      white-space: nowrap;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-badge--amber {
      background: #fff4e3;
      color: #854f0b;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-badge--teal {
      background: #eefaf5;
      color: #0f6e56;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-card-title {
      font-size: 14px;
      font-weight: 500;
      color: #111827;
      line-height: 1.35;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) .learn-grid-card-sub {
      font-size: 11.5px;
      font-weight: 400;
      color: #8a948d;
      line-height: 1.4;
    }
    [data-testid="stMain"]:has(.learn-portal-screen) div[data-testid="stElementContainer"].st-key-learn_card_mini
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.learn-portal-screen) div[data-testid="stElementContainer"].st-key-learn_card_topic
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.learn-portal-screen) div[data-testid="stElementContainer"].st-key-learn_card_keyword
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.learn-portal-screen) div[data-testid="stElementContainer"].st-key-learn_card_script
      div[data-testid="stButton"] > button {
      background: #ffffff !important;
      border: 1px solid #e5e7e2 !important;
      box-shadow: none !important;
      color: #0f6e56 !important;
      font-size: 12px !important;
      font-weight: 500 !important;
      min-height: 34px !important;
      padding: 0.25rem 0.5rem !important;
    }
    @media (max-width: 420px) {
      [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-grid-marker
        ~ div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
      }
      [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-grid-marker
        ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
      [data-testid="stMain"]:has(.learn-portal-screen) .learn-portal-grid-marker
        ~ div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: 100% !important;
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
      font-weight: 500;
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
    section.main:has(.mx-landing-marker) .mx-portal-practice-marker ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.mx-portal-card) {
      gap: 0;
    }
    section.main:has(.mx-landing-marker) .mx-portal-mode-spacer {
      min-height: 1px;
      visibility: hidden;
    }

    @media (max-width: 640px) {
      section.main:has(.mx-landing-marker) .mx-portal-sample-section {
        margin-bottom: 22px;
        padding-bottom: 16px;
      }
    }

    /* Learning portal — design-A cards (overlay tap; all 5 practice modes) */
    .mx-portal-cards-marker {
      display: none !important;
    }
    .mx-portal-card {
      position: relative;
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 12px;
      min-height: 72px;
      padding: 14px 14px 14px 16px;
      overflow: hidden;
      border-radius: 16px;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      color: inherit !important;
      margin: 0;
      pointer-events: none;
      transition: transform 0.16s var(--ease-out), box-shadow 0.16s var(--ease-out),
        border-color 0.16s var(--ease-out);
    }
    .mx-portal-card-accent {
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      border-radius: 0;
      pointer-events: none;
    }
    .mx-portal-card-badge {
      display: inline-flex;
      align-items: center;
      flex-shrink: 0;
      margin: 0;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 500;
      line-height: 1.35;
      pointer-events: none;
    }
    .mx-portal-card-badge--teal {
      background: rgba(13, 148, 136, 0.12);
      color: #0F6E56 !important;
    }
    .mx-portal-card-badge--blue {
      background: rgba(37, 99, 235, 0.12);
      color: #2563eb !important;
    }
    .mx-portal-card-ico {
      flex-shrink: 0;
      width: 40px;
      height: 40px;
      border-radius: 10px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      margin: 0;
      pointer-events: none;
    }
    .mx-portal-card-ico svg {
      width: 22px;
      height: 22px;
      stroke-width: 2;
    }
    .mx-portal-card-body {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
      flex: 1 1 auto;
      overflow: visible;
      padding-right: 40px;
      pointer-events: none;
    }
    .mx-portal-card-title-row {
      display: flex;
      flex-direction: row;
      align-items: center;
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
    }
    .mx-portal-card-title {
      font-family: var(--font-display) !important;
      font-size: 15px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.01em;
      line-height: 1.25;
      margin: 0;
    }
    .mx-portal-card-sub {
      font-size: 12px;
      color: #6b7280;
      line-height: 1.4;
      margin: 0;
    }
    .mx-portal-card-chevron {
      position: absolute;
      right: 12px;
      top: 50%;
      transform: translateY(-50%);
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 999px;
      pointer-events: none;
    }
    .mx-portal-card-chevron svg {
      width: 18px;
      height: 18px;
    }
    .mx-portal-card--real-mock .mx-portal-card-accent { background: #1D9E75; }
    .mx-portal-card--real-mock .mx-portal-card-ico { background: #E1F5EE; color: #0F6E56; }
    .mx-portal-card--real-mock .mx-portal-card-chevron { color: #0F6E56; background: rgba(13, 148, 136, 0.14); }
    .mx-portal-card--mini-mock .mx-portal-card-accent { background: #378ADD; }
    .mx-portal-card--mini-mock .mx-portal-card-ico { background: #E6F1FB; color: #185FA5; }
    .mx-portal-card--mini-mock .mx-portal-card-chevron { color: #185FA5; background: rgba(55, 138, 221, 0.14); }
    .mx-portal-card--topic .mx-portal-card-accent { background: #7F77DD; }
    .mx-portal-card--topic .mx-portal-card-ico { background: #EEEDFE; color: #534AB7; }
    .mx-portal-card--topic .mx-portal-card-chevron { color: #534AB7; background: rgba(127, 119, 221, 0.14); }
    .mx-portal-card--script .mx-portal-card-accent { background: #D85A30; }
    .mx-portal-card--script .mx-portal-card-ico { background: #FAECE7; color: #993C1D; }
    .mx-portal-card--script .mx-portal-card-chevron { color: #993C1D; background: rgba(216, 90, 48, 0.14); }
    .mx-portal-card--keyword .mx-portal-card-accent { background: #EF9F27; }
    .mx-portal-card--keyword .mx-portal-card-ico { background: #FAEEDA; color: #854F0B; }
    .mx-portal-card--keyword .mx-portal-card-chevron { color: #854F0B; background: rgba(239, 159, 39, 0.16); }
    .mx-portal-card--home-start .mx-portal-card-accent { background: #1D9E75; }
    .mx-portal-card--home-start .mx-portal-card-ico { background: #E1F5EE; color: #0F6E56; }
    .mx-portal-card--home-start .mx-portal-card-chevron { color: #0F6E56; background: rgba(13, 148, 136, 0.14); }
    .mx-portal-card--home-history .mx-portal-card-accent { background: #888780; }
    .mx-portal-card--home-history .mx-portal-card-ico { background: #F1EFE8; color: #5F5E5A; }
    .mx-portal-card--home-history .mx-portal-card-chevron { color: #5F5E5A; background: rgba(136, 135, 128, 0.14); }
    .mx-portal-card--home-quick-pattern .mx-portal-card-accent { background: #378ADD; }
    .mx-portal-card--home-quick-pattern .mx-portal-card-ico { background: #E6F1FB; color: #185FA5; }
    .mx-portal-card--home-quick-pattern .mx-portal-card-chevron { color: #185FA5; background: rgba(55, 138, 221, 0.14); }
    .mx-portal-card--home-quick-scripts .mx-portal-card-accent { background: #EF9F27; }
    .mx-portal-card--home-quick-scripts .mx-portal-card-ico { background: #FAEEDA; color: #854F0B; }
    .mx-portal-card--home-quick-scripts .mx-portal-card-chevron { color: #854F0B; background: rgba(239, 159, 39, 0.16); }
    .mx-portal-card--home-quick-lectures .mx-portal-card-accent { background: #7F77DD; }
    .mx-portal-card--home-quick-lectures .mx-portal-card-ico { background: #EEEDFE; color: #534AB7; }
    .mx-portal-card--home-quick-lectures .mx-portal-card-chevron { color: #534AB7; background: rgba(127, 119, 221, 0.14); }
    .mx-portal-card--home-quick-coaching .mx-portal-card-accent { background: #D85A30; }
    .mx-portal-card--home-quick-coaching .mx-portal-card-ico { background: #FAECE7; color: #993C1D; }
    .mx-portal-card--home-quick-coaching .mx-portal-card-chevron { color: #993C1D; background: rgba(216, 90, 48, 0.14); }
    .mx-portal-card--compact {
      min-height: 58px;
      padding: 10px 10px 10px 12px;
      gap: 8px;
    }
    .mx-portal-card--compact .mx-portal-card-ico {
      width: 34px;
      height: 34px;
      border-radius: 8px;
    }
    .mx-portal-card--compact .mx-portal-card-ico svg {
      width: 18px;
      height: 18px;
    }
    .mx-portal-card--compact .mx-portal-card-body {
      padding-right: 32px;
    }
    .mx-portal-card--compact .mx-portal-card-title {
      font-size: 13px;
    }
    .mx-portal-card--compact .mx-portal-card-sub {
      font-size: 11px;
      line-height: 1.35;
    }
    .mx-portal-card--compact .mx-portal-card-chevron {
      right: 8px;
      width: 24px;
      height: 24px;
    }
    .mx-portal-card--compact .mx-portal-card-chevron svg {
      width: 16px;
      height: 16px;
    }
    [data-testid="stMain"]:has(.home-screen) .mx-portal-card--home-history {
      margin-top: 10px;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card) {
      position: relative;
      align-self: flex-start !important;
      height: auto !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"] {
      position: relative;
      gap: 0 !important;
      height: auto !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stElementContainer"]:has(.mx-portal-card) {
      height: auto !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stMarkdown"]:has(.mx-portal-card) {
      margin-bottom: 0 !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stMarkdownContainer"]:has(.mx-portal-card) {
      margin-bottom: 0 !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stElementContainer"]:has(.mx-portal-card),
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stMarkdown"]:has(.mx-portal-card),
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card) .mx-portal-card,
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card) .mx-portal-card * {
      pointer-events: none !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stElementContainer"]:has(> div[data-testid="stButton"]) {
      position: absolute !important;
      inset: 0 !important;
      height: 100% !important;
      z-index: 3 !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stButton"] {
      position: static !important;
      width: 100% !important;
      height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
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
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--real-mock,
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--real-mock {
      border-color: rgba(29, 158, 117, 0.35) !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--mini-mock,
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--mini-mock {
      border-color: rgba(55, 138, 221, 0.35) !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--topic,
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--topic {
      border-color: rgba(127, 119, 221, 0.35) !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--script,
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--script {
      border-color: rgba(216, 90, 48, 0.35) !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--keyword,
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--keyword {
      border-color: rgba(239, 159, 39, 0.35) !important;
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card-chevron {
      transform: translateY(-50%) translateX(2px);
    }
    [data-testid="stMain"]:has(.mx-portal-cards-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:active)
      .mx-portal-card {
      transform: translateY(0) scale(0.985);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    /* Home — design-A cards (overlay tap; start + history + quick actions) */
    .home-card-grid-marker {
      display: none !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-home_start_primary),
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-home_open_history),
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_PATTERN),
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_SCRIPTS),
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_LECTURES),
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_script_coaching) {
      position: relative;
      align-self: flex-start !important;
      height: auto !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-home_start_primary)
      > [data-testid="stVerticalBlock"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-home_open_history)
      > [data-testid="stVerticalBlock"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_PATTERN)
      > [data-testid="stVerticalBlock"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_SCRIPTS)
      > [data-testid="stVerticalBlock"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_LECTURES)
      > [data-testid="stVerticalBlock"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_script_coaching)
      > [data-testid="stVerticalBlock"] {
      position: relative;
      gap: 0 !important;
      height: auto !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stElementContainer"]:has(.mx-portal-card) {
      height: auto !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stMarkdown"]:has(.mx-portal-card) {
      margin-bottom: 0 !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stMarkdownContainer"]:has(.mx-portal-card) {
      margin-bottom: 0 !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stElementContainer"]:has(.mx-portal-card),
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      div[data-testid="stMarkdown"]:has(.mx-portal-card),
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card) .mx-portal-card,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card) .mx-portal-card * {
      pointer-events: none !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-home_start_primary,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-home_open_history,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_PATTERN,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_SCRIPTS,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_LECTURES,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_script_coaching {
      position: absolute !important;
      inset: 0 !important;
      height: 100% !important;
      z-index: 3 !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-home_start_primary
      div[data-testid="stButton"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-home_open_history
      div[data-testid="stButton"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_PATTERN
      div[data-testid="stButton"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_SCRIPTS
      div[data-testid="stButton"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_LECTURES
      div[data-testid="stButton"],
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_script_coaching
      div[data-testid="stButton"] {
      position: static !important;
      width: 100% !important;
      height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-home_start_primary
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-home_open_history
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_PATTERN
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_SCRIPTS
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_LECTURES
      div[data-testid="stButton"] > button,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stElementContainer"].st-key-qa_nav_script_coaching
      div[data-testid="stButton"] > button {
      width: 100% !important;
      height: 100% !important;
      min-height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      border: none !important;
      border-radius: 16px !important;
      background: transparent !important;
      box-shadow: none !important;
      opacity: 0 !important;
      color: transparent !important;
      -webkit-text-fill-color: transparent !important;
      font-size: 0 !important;
      line-height: 0 !important;
      cursor: pointer !important;
      pointer-events: auto !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card--compact)
      div[data-testid="stElementContainer"][class*="st-key-"]
      div[data-testid="stButton"] > button {
      border-radius: 12px !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-home_start_primary)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--home-start,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-home_start_primary)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--home-start {
      border-color: rgba(29, 158, 117, 0.35) !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-home_open_history)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--home-history,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-home_open_history)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--home-history {
      border-color: rgba(136, 135, 128, 0.35) !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_PATTERN)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--home-quick-pattern,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_PATTERN)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--home-quick-pattern {
      border-color: rgba(55, 138, 221, 0.35) !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_SCRIPTS)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--home-quick-scripts,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_SCRIPTS)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--home-quick-scripts {
      border-color: rgba(239, 159, 39, 0.35) !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_LECTURES)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--home-quick-lectures,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_LECTURES)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--home-quick-lectures {
      border-color: rgba(127, 119, 221, 0.35) !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_script_coaching)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card--home-quick-coaching,
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.st-key-qa_nav_script_coaching)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:focus-visible)
      .mx-portal-card--home-quick-coaching {
      border-color: rgba(216, 90, 48, 0.35) !important;
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .mx-portal-card-chevron {
      transform: translateY(-50%) translateX(2px);
    }
    [data-testid="stMain"]:has(.home-card-grid-marker)
      div[data-testid="stColumn"]:has(.mx-portal-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:active)
      .mx-portal-card {
      transform: translateY(0) scale(0.985);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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
      margin: 4px 0 0 0;
    }
    .mx-progress-meta {
      display: flex;
      align-items: center;
      min-width: 0;
    }
    .mx-progress-eyebrow {
      display: none;
    }
    .mx-progress-count {
      font-size: 14px;
      font-weight: 500;
      letter-spacing: -0.01em;
      color: #111827;
    }
    .mx-progress-count .mx-progress-num {
      color: #111827;
      font-weight: 500;
    }
    .mx-progress-count .mx-progress-of {
      color: #888780;
      font-weight: 400;
    }
    .mx-progress-chip {
      align-self: center;
      flex-shrink: 0;
      padding: 4px 10px;
      border-radius: 999px;
      background: #E1F5EE;
      color: #0F6E56;
      font-size: 12px;
      font-weight: 500;
      letter-spacing: -0.005em;
      max-width: 56vw;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .mx-progress-bar {
      height: 4px;
      width: 100%;
      background: #F1EFE8;
      border-radius: 999px;
      overflow: hidden;
      margin: 8px 0 16px 0;
    }
    .mx-progress-fill {
      display: block;
      height: 100%;
      background: #1D9E75;
      border-radius: 999px;
      transition: width 0.35s var(--ease-out);
    }

    /* --- Question card ----------------------------------------------- */
    .mx-question-card {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      border-radius: 16px;
      padding: 18px 16px;
      margin: 0 0 14px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .mx-question-type {
      display: none;
    }
    .mx-question-topic {
      font-size: 15px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.01em;
      margin: 0;
      line-height: 1.55;
    }
    .mx-question-hint {
      font-size: 0.82rem;
      color: var(--text-secondary);
      line-height: 1.55;
      margin: 0;
    }
    .mx-question-hint strong {
      color: var(--navy);
      font-weight: 500;
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
      font-weight: 500;
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
      font-weight: 500;
      color: #0f766e;
      margin: 0 0 8px 0;
    }
    .mx-listen-compact {
      margin: 0 0 14px 0;
      padding: 12px 14px;
      border-radius: 10px;
      background: #f8fafc;
      border: 1px solid rgba(17, 24, 39, 0.08);
    }
    .mx-listen-compact-label {
      margin: 0 0 8px 0;
      font-size: 0.78rem;
      font-weight: 500;
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
      box-shadow: none;
    }
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button[kind="primary"],
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button[kind="secondary"],
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button[data-testid="baseButton-secondary"],
    section.main:has(.mx-marker) .mx-listen-compact div[data-testid="stButton"] > button[data-testid="stBaseButton-secondary"] {
      background: #ffffff !important;
      color: #0f766e !important;
    }

    /* --- Record stage (the screen's emotional center) ---------------- */
    .mx-record-stage {
      position: relative;
      background: #0f172a;
      border-radius: 16px;
      padding: 18px 16px 14px 16px;
      margin: 0 0 14px 0;
      color: #ffffff !important;
      box-shadow: none;
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
      background: none;
      pointer-events: none;
      opacity: 0;
    }
    .mx-record-eyebrow {
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #9FE1CB !important;
      margin: 0 0 12px 0;
    }
    .mx-record-title {
      font-size: 1.15rem;
      font-weight: 500;
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
      margin: 0 0 12px 0;
      padding: 14px;
      border-radius: 10px;
      background: #1e293b;
      border: none;
      box-shadow: none;
      color: #ffffff !important;
      text-align: center;
    }
    .mx-record-stage .mx-rec-timer-label,
    .mx-record-stage .mx-answer-timer-label {
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #94a3b8 !important;
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
      font-weight: 500;
      letter-spacing: 0.02em;
      background: rgba(148, 163, 184, 0.18);
      color: #cbd5e1 !important;
    }
    .mx-answer-timer-status--idle {
      background: rgba(148, 163, 184, 0.18);
      color: #94a3b8 !important;
    }
    .mx-answer-timer-status--warn,
    .mx-answer-timer-status--up {
      background: rgba(251, 146, 60, 0.16);
      color: #fdba74 !important;
    }
    .mx-record-title--live {
      font-size: 1.15rem;
      font-weight: 500;
      margin: 0 0 8px 0;
      color: #ffffff !important;
    }
    .mx-record-stage .mx-rec-timer-value {
      font-size: 28px;
      font-weight: 500;
      letter-spacing: 0.02em;
      color: #ffffff !important;
      margin: 0 0 10px 0;
      line-height: 1.1;
      font-variant-numeric: tabular-nums;
    }
    .mx-record-stage .mx-rec-timer-progress {
      display: block;
      width: 100%;
      height: 4px;
      border-radius: 999px;
      background: #334155;
      overflow: hidden;
      margin: 0 0 8px 0;
    }
    .mx-record-stage .mx-rec-timer-progress-fill {
      display: block;
      height: 100%;
      border-radius: 999px;
      background: #5DCAA5;
      transition: width 0.35s ease;
    }
    .mx-record-stage .mx-rec-timer-helper {
      font-size: 12px;
      line-height: 1.45;
      margin: 0;
      color: #94a3b8 !important;
    }
    .mx-record-stage .mx-rec-timer--idle {
      background: #1e293b;
    }
    .mx-record-stage .mx-rec-timer--idle .mx-rec-timer-value {
      color: #ffffff !important;
    }
    .mx-record-stage .mx-rec-timer--normal .mx-rec-timer-value {
      color: #ffffff !important;
    }
    .mx-record-stage .mx-rec-timer--warn {
      background: #1e293b;
      border: none;
    }
    .mx-record-stage .mx-rec-timer--warn .mx-rec-timer-value {
      color: #fb923c !important;
    }
    .mx-record-stage .mx-rec-timer--warn .mx-rec-timer-progress-fill {
      background: #fb923c;
    }
    .mx-record-stage .mx-rec-timer--warn .mx-rec-timer-helper {
      color: #fdba74 !important;
      font-weight: 500;
    }
    .mx-record-stage .mx-rec-timer--up {
      background: #1e293b;
      border: none;
    }
    .mx-record-stage .mx-rec-timer--up .mx-rec-timer-value {
      color: #f87171 !important;
    }
    .mx-record-stage .mx-rec-timer--up .mx-rec-timer-progress-fill {
      background: #f87171;
    }
    .mx-record-stage .mx-rec-timer--up .mx-rec-timer-helper {
      color: #fca5a5 !important;
      font-weight: 500;
    }
    /* V2 exam screens — client-side answer countdown (topic / mini / real mock) */
    [data-testid="stMain"]:has(.tq-screen-marker) .mx-record-stage--v2 {
      margin-bottom: 10px;
      border-radius: 16px;
      padding-bottom: 12px;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .mx-record-stage--v2 .tq-answer-card-top {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      margin: 0 !important;
      padding: 0 !important;
      border-radius: 0 !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .mx-record-stage--v2 .tq-answer-title,
    [data-testid="stMain"]:has(.tq-screen-marker) .mx-record-stage--v2 .tq-answer-desc {
      color: rgba(255, 255, 255, 0.92) !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer {
      margin: 0 0 14px 0;
      padding: 14px;
      border-radius: 10px;
      background: #1e293b;
      border: none;
      box-shadow: none;
      text-align: center;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer .mx-rec-timer-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer .mx-answer-timer-label {
      color: #94a3b8 !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer .mx-rec-timer-value {
      font-size: 28px;
      font-weight: 500;
      letter-spacing: 0.02em;
      font-variant-numeric: tabular-nums;
      margin: 0 0 10px 0;
      line-height: 1.1;
      color: #ffffff !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer .mx-rec-timer-progress {
      height: 4px;
      margin: 0 0 8px 0;
      background: #334155;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer .mx-rec-timer-progress-fill {
      background: #5DCAA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--warn {
      animation: opic-answer-timer-pulse 1.1s ease-in-out infinite;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--warn .mx-rec-timer-value {
      color: #fb923c !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--warn .mx-rec-timer-progress-fill {
      background: #fb923c !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--up {
      animation: opic-answer-timer-pulse 0.85s ease-in-out infinite;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--up .mx-rec-timer-value {
      color: #f87171 !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--up .mx-rec-timer-progress-fill {
      background: #f87171 !important;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-teal .mx-rec-timer-progress-fill,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-blue .mx-rec-timer-progress-fill,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-purple .mx-rec-timer-progress-fill,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-pink .mx-rec-timer-progress-fill,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-amber .mx-rec-timer-progress-fill,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-coral .mx-rec-timer-progress-fill {
      background: #5DCAA5;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-teal .mx-rec-timer-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-teal.mx-rec-timer--normal .mx-rec-timer-value,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-blue .mx-rec-timer-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-blue.mx-rec-timer--normal .mx-rec-timer-value,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-purple .mx-rec-timer-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-purple.mx-rec-timer--normal .mx-rec-timer-value,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-pink .mx-rec-timer-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-pink.mx-rec-timer--normal .mx-rec-timer-value,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-amber .mx-rec-timer-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-amber.mx-rec-timer--normal .mx-rec-timer-value,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-coral .mx-rec-timer-label,
    [data-testid="stMain"]:has(.tq-screen-marker) .opic-answer-timer.mx-rec-timer--accent-coral.mx-rec-timer--normal .mx-rec-timer-value {
      color: #ffffff !important;
    }
    @keyframes opic-answer-timer-pulse {
      0%, 100% { box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08); }
      50% { box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.22), 0 8px 22px rgba(234, 88, 12, 0.14); }
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
      background: rgba(255, 255, 255, 0.08);
      border: none;
      color: #9FE1CB !important;
      font-size: 12px;
      font-weight: 500;
      letter-spacing: -0.005em;
    }
    .mx-record-saved::before {
      content: "";
      display: block;
      width: 7px; height: 7px;
      border-radius: 50%;
      background: #34d399;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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
      border-radius: 10px !important !important;
      font-size: 0.95rem !important;
      font-weight: 500 !important;
      letter-spacing: -0.005em;
      border: 0.5px solid rgba(17, 24, 39, 0.06) !important;
      background: rgba(136, 135, 128, 0.10) !important;
      color: #444441 !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      transition: transform 0.16s var(--ease-out), box-shadow 0.2s var(--ease-out),
                  background 0.2s var(--ease-out) !important;
    }
    section.main:has(.mx-marker) .stButton > button:hover:not(:disabled) {
      background: rgba(136, 135, 128, 0.16) !important;
      color: #444441 !important;
      border-color: rgba(17, 24, 39, 0.06) !important;
    }
    section.main:has(.mx-marker) .stButton > button[kind="primary"] {
      background: #0F6E56 !important;
      color: #ffffff !important;
      border-color: transparent !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    section.main:has(.mx-marker) .stButton > button[kind="primary"]:hover:not(:disabled) {
      background: #0b5c47 !important;
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
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    section.main:has(.mx-marker) div[data-testid="stExpander"] details[open] {
      border-color: rgba(13, 148, 136, 0.22);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    section.main:has(.mx-marker) div[data-testid="stExpander"] summary {
      padding: 12px 14px !important;
      font-weight: 500 !important;
      font-size: 0.92rem !important;
      color: var(--navy) !important;
    }

    /* Status widget (``st.status``) — legacy; analysis uses .mx-ai-wait */
    section.main:has(.mx-marker) [data-testid="stStatus"] {
      border-radius: var(--radius-md) !important;
      border: 1px solid var(--border-subtle) !important;
      background: rgba(255, 255, 255, 0.92) !important;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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
      background: #ffffff;
      border: 1px solid rgba(13, 148, 136, 0.16);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      text-align: center;
    }
    .mx-ai-wait-anim {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      margin: 0 auto 16px auto;
    }
    .mx-ai-wait-wave {
      display: block;
    }
    .mx-ai-wait-wave-line {
      stroke-dasharray: 180;
      stroke-dashoffset: 180;
      animation: mxWaitWaveFlow 2s linear infinite;
    }
    @keyframes mxWaitWaveFlow {
      to { stroke-dashoffset: 0; }
    }
    @media (prefers-reduced-motion: reduce) {
      .mx-ai-wait-wave-line {
        animation: none;
        stroke-dashoffset: 0;
      }
    }
    .mx-ai-wait-title {
      font-size: 1.2rem;
      font-weight: 500;
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
      font-weight: 500;
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
      font-weight: 500;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--mint);
      margin: 0 0 10px 0;
    }
    .mx-ai-wait-tip-label {
      font-size: 0.68rem;
      font-weight: 500;
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
      font-weight: 500;
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

    /* --- History list empty state ------------------------------------ */
    .hist-list-marker {
      display: none !important;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-date-header {
      font-size: 13px;
      font-weight: 500;
      color: #888780;
      margin: 16px 0 8px 0;
      padding-top: 6px;
      border-top: 0.5px solid rgba(17, 24, 39, 0.08);
      text-align: left;
      line-height: 1.4;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-date-header--first {
      margin-top: 4px;
      padding-top: 0;
      border-top: none;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-card {
      max-width: 420px;
      margin: 20px auto 0 auto;
      padding: 0;
      overflow: hidden;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 16px;
      box-sizing: border-box;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-stage {
      position: relative;
      background: #E1F5EE;
      padding: 26px 18px 18px;
      text-align: center;
      overflow: hidden;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-char-wrap {
      position: relative;
      z-index: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-wave {
      display: block;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-chip {
      position: absolute;
      z-index: 0;
      background: #ffffff;
      font-size: 11px;
      font-weight: 500;
      padding: 4px 10px;
      border-radius: 999px;
      line-height: 1.2;
      white-space: nowrap;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-chip--desc {
      top: 16px;
      left: 18px;
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-chip--role {
      top: 34px;
      right: 16px;
      color: #534AB7;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-chip--cmp {
      bottom: 20px;
      left: 24px;
      color: #185FA5;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-body {
      padding: 18px 18px 20px;
      text-align: center;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-title {
      font-size: 16px;
      font-weight: 500;
      color: #111827;
      margin: 0 0 8px 0;
      line-height: 1.35;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-sub {
      font-size: 13px;
      font-weight: 400;
      color: #888780;
      margin: 0 0 18px 0;
      line-height: 1.6;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-preview-label {
      font-size: 11px;
      font-weight: 500;
      color: #B4B2A9;
      margin: 0 0 10px 0;
      text-align: left;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel {
      display: flex;
      align-items: center;
      gap: 10px;
      border: 1px dashed #D3D1C7;
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 8px;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel--primary {
      opacity: 0.75;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel--secondary {
      opacity: 0.45;
      margin-bottom: 16px;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel-tile {
      flex-shrink: 0;
      width: 34px;
      height: 34px;
      border-radius: 10px;
      background: #F1EFE8;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel-bars {
      flex: 1 1 auto;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel-bar {
      height: 8px;
      border-radius: 999px;
      background: #F1EFE8;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel-bar--w72 { width: 72%; }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel-bar--w46 { width: 46%; }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel-bar--w64 { width: 64%; }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel-bar--w38 { width: 38%; }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-skel-pill {
      flex-shrink: 0;
      background: #F1EFE8;
      color: #B4B2A9;
      font-size: 11px;
      font-weight: 500;
      padding: 4px 8px;
      border-radius: 999px;
      line-height: 1.2;
      white-space: nowrap;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-cta {
      display: block;
      width: 100%;
      box-sizing: border-box;
      background: #0F6E56;
      color: #ffffff !important;
      font-size: 14px;
      font-weight: 500;
      padding: 13px;
      border-radius: 10px;
      text-align: center;
      text-decoration: none !important;
      line-height: 1.2;
    }
    [data-testid="stMain"]:has(.hist-list-marker) .hist-empty-cta:hover {
      color: #ffffff !important;
      text-decoration: none !important;
      opacity: 0.92;
    }

    /* History — script coaching before/after */
    [data-testid="stMain"]:has(.hist-script-screen) .hist-sc-question {
      font-size: 14px;
      font-weight: 500;
      color: #111827;
      line-height: 1.55;
      margin: 0 0 14px 0;
      word-break: break-word;
    }
    [data-testid="stMain"]:has(.hist-script-screen) .hist-sc-legacy-note {
      font-size: 13px;
      font-weight: 400;
      color: #888780;
      margin: 0 0 12px 0;
      line-height: 1.5;
    }
    [data-testid="stMain"]:has(.hist-script-screen) .sc-ba-block {
      margin: 0 0 14px 0;
    }
    [data-testid="stMain"]:has(.hist-script-screen) .sc-ba-label {
      font-size: 12px;
      font-weight: 500;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: #888780;
      margin: 0 0 6px 0;
    }
    [data-testid="stMain"]:has(.hist-script-screen) .sc-ba-label--accent {
      color: #0F6E56;
    }
    [data-testid="stMain"]:has(.hist-script-screen) .sc-ba-original {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.hist-script-screen) .sc-ba-original p {
      margin: 0;
      font-size: 14px;
      font-weight: 400;
      line-height: 1.65;
      white-space: pre-wrap;
      word-break: break-word;
      color: #5F5E5A;
    }
    [data-testid="stMain"]:has(.hist-script-screen) .sc-ba-upgraded {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.10);
      border-left: 2px solid #5DCAA5;
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.hist-script-screen) .sc-ba-upgraded p {
      margin: 0;
      font-size: 14px;
      font-weight: 400;
      line-height: 1.65;
      white-space: pre-wrap;
      word-break: break-word;
      color: #111827;
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
      font-weight: 500;
      margin: 0 0 4px 0;
      color: var(--text-secondary);
    }
    .mx-speech-debug-body {
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }

    /* --- Report screen --------------------------------------------- */
    .mx-report-hero {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      border-radius: 16px;
      padding: 18px 16px;
      margin: 4px 0 16px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .mx-report-hero .mx-rh-eyebrow {
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.02em;
      text-transform: none;
      color: #0F6E56;
      margin: 0;
    }
    .mx-report-hero .mx-rh-title {
      font-size: 16px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.02em;
      margin: 6px 0 0 0;
      line-height: 1.35;
    }
    .mx-report-hero .mx-rh-transcript {
      margin-top: 12px;
      padding: 0 0 0 10px;
      background: transparent;
      border-radius: 0;
      font-size: 13px;
      color: #444441;
      line-height: 1.7;
      border-left: 2px solid #5DCAA5;
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
      background: #F1EFE8;
      border: none;
      font-size: 12px;
      font-weight: 500;
      color: #5F5E5A;
    }

    /* --- Coaching experience (mock report, step 6) ------------------- */
    section.main:has(.mx-marker) .mx-coach-hero {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      border-radius: 16px;
      padding: 18px 16px;
      margin: 0 0 14px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    section.main:has(.mx-marker) .mx-coach-eyebrow {
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.02em;
      text-transform: none;
      color: #0F6E56;
      margin: 0 0 6px 0;
    }
    section.main:has(.mx-marker) .mx-coach-hero-title {
      font-size: 16px;
      font-weight: 500;
      color: #111827;
      letter-spacing: -0.02em;
      line-height: 1.35;
      margin: 0 0 8px 0;
    }
    section.main:has(.mx-marker) .mx-coach-hero-sub {
      font-size: 13px;
      color: #444441;
      line-height: 1.7;
      margin: 0;
    }
    section.main:has(.mx-marker) .mx-coach-section {
      margin: 18px 0 6px 0;
    }
    section.main:has(.mx-marker) .mx-coach-sec-eyebrow {
      font-size: 12px;
      font-weight: 500;
      letter-spacing: 0;
      text-transform: none;
      color: #993C1D;
      margin: 0 0 4px 0;
    }
    section.main:has(.mx-marker) .mx-coach-section[aria-label="잘한 점"] .mx-coach-sec-eyebrow {
      color: #3B6D11;
    }
    section.main:has(.mx-marker) .mx-coach-section[aria-label="문법 교정"] .mx-coach-sec-eyebrow,
    section.main:has(.mx-marker) .mx-coach-section[aria-label="표현 업그레이드"] .mx-coach-sec-eyebrow {
      color: #993C1D;
    }
    section.main:has(.mx-marker) .mx-coach-section[aria-label="원어민 업그레이드"] .mx-coach-sec-eyebrow,
    section.main:has(.mx-marker) .mx-coach-section[aria-label="발음·강세 전달력"] .mx-coach-sec-eyebrow {
      color: #534AB7;
    }
    section.main:has(.mx-marker) .mx-coach-sec-title {
      font-size: 1rem;
      font-weight: 500;
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
      border-radius: 10px;
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      max-width: 100%;
    }
    section.main:has(.mx-marker) .mx-coach-section[aria-label="잘한 점"] .mx-coach-chip {
      background: #ffffff;
      border-color: rgba(59, 109, 17, 0.14);
    }
    section.main:has(.mx-marker) .mx-coach-section[aria-label="잘한 점"] .mx-coach-chip-ico {
      color: #3B6D11;
    }
    section.main:has(.mx-marker) .mx-coach-chip-ico {
      flex: 0 0 auto;
      color: var(--mint);
      font-weight: 500;
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
      background: #ffffff;
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
      font-weight: 500;
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
      font-weight: 500;
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
      border-radius: 10px;
      background: rgba(248, 250, 252, 0.9);
      border: 1px solid var(--border-subtle);
      font-size: 0.8rem;
    }
    section.main:has(.mx-marker) .mx-coach-pron-label {
      color: var(--text-secondary);
      font-weight: 500;
    }
    section.main:has(.mx-marker) .mx-coach-pron-score {
      font-weight: 500;
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
      background: #ffffff;
      border: 1px solid rgba(13, 148, 136, 0.22);
      font-size: 0.92rem;
      line-height: 1.55;
      color: var(--text-primary);
      text-align: center;
      font-weight: 500;
    }

    .mx-section-h {
      font-size: 0.74rem;
      font-weight: 500;
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
        background-color: #FAFAF9 !important;
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

    /* Multiselect chips — wrap + no horizontal clip (BaseWeb Control/Value + Tag) */
    div[data-testid="stMultiSelect"] .stMultiSelect [data-baseweb="select"],
    div[data-testid="stMultiSelect"] [data-baseweb="select"] {
      width: 100% !important;
      max-width: 100% !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
      display: flex !important;
      height: auto !important;
      min-height: 2.75rem !important;
      max-height: none !important;
      overflow: visible !important;
      overflow-x: visible !important;
      align-items: flex-start !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div > div:first-child {
      display: flex !important;
      flex: 1 1 auto !important;
      flex-wrap: wrap !important;
      align-items: center !important;
      align-content: flex-start !important;
      gap: 4px 6px !important;
      width: 100% !important;
      min-width: 0 !important;
      height: auto !important;
      max-height: none !important;
      overflow: visible !important;
      overflow-x: visible !important;
      overflow-y: visible !important;
    }
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"],
    div[data-testid="stMultiSelect"] [data-baseweb="tag"] {
      display: inline-flex !important;
      width: auto !important;
      max-width: none !important;
      flex: 0 0 auto !important;
      flex-shrink: 0 !important;
      white-space: nowrap !important;
      overflow: visible !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="tag"] > span {
      overflow: visible !important;
      text-overflow: clip !important;
      white-space: nowrap !important;
      max-width: none !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="select"] input {
      flex: 1 1 2.5rem !important;
      min-width: 2.5rem !important;
      width: auto !important;
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
      background: #ffffff !important;
      border: 1px solid rgba(13, 148, 136, 0.24) !important;
    }

    .mx-mode-badge {
      margin: 10px 0 0;
      font-size: 12px;
      font-weight: 500;
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

    /* Streamlit widgets — secondary (default) buttons: light gray tone.
       Streamlit 1.50 nests <button> under tooltip wrappers inside stButton,
       so use descendant + stBaseButton-* selectors (not only > button). */
    .stButton > button,
    .stButton button[data-testid="stBaseButton-secondary"],
    div[data-testid="stButton"] > button,
    div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] {
      background: rgba(136, 135, 128, 0.10) !important;
      color: #444441 !important;
      border: 0.5px solid rgba(17, 24, 39, 0.06) !important;
      font-weight: 500 !important;
    }
    .stButton > button:hover:not(:disabled),
    .stButton button[data-testid="stBaseButton-secondary"]:hover:not(:disabled),
    div[data-testid="stButton"] > button:hover:not(:disabled),
    div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {
      background: rgba(136, 135, 128, 0.16) !important;
      color: #444441 !important;
      border-color: rgba(17, 24, 39, 0.06) !important;
    }

    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
    div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
      background: rgba(15, 110, 86, 0.12) !important;
      color: #085041 !important;
      border: none !important;
      font-weight: 500 !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover:not(:disabled),
    div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover:not(:disabled),
    div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover:not(:disabled),
    div[data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
      background: rgba(15, 110, 86, 0.18) !important;
      color: #085041 !important;
    }

    /* Topic-practice primary buttons follow the selected topic's accent
       (scoped marker .tq-accent-scope--* beats the global teal rule above).
       Mock exams plant no marker, so they keep the teal default. */
    [data-testid="stMain"]:has(.tq-accent-scope) .tq-accent-scope { display: none !important; }
    [data-testid="stMain"]:has(.tq-accent-scope--teal) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--teal) div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--teal) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
      background: rgba(15, 110, 86, 0.12) !important;
      color: #085041 !important;
      border: none !important;
      font-weight: 500 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--teal) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
      background: rgba(15, 110, 86, 0.18) !important;
      color: #085041 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--blue) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--blue) div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--blue) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
      background: rgba(24, 95, 165, 0.12) !important;
      color: #0C447C !important;
      border: none !important;
      font-weight: 500 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--blue) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
      background: rgba(24, 95, 165, 0.18) !important;
      color: #0C447C !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--purple) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--purple) div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--purple) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
      background: rgba(83, 74, 183, 0.12) !important;
      color: #3C3489 !important;
      border: none !important;
      font-weight: 500 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--purple) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
      background: rgba(83, 74, 183, 0.18) !important;
      color: #3C3489 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--pink) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--pink) div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--pink) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
      background: rgba(217, 83, 126, 0.12) !important;
      color: #72243E !important;
      border: none !important;
      font-weight: 500 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--pink) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
      background: rgba(217, 83, 126, 0.18) !important;
      color: #72243E !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--amber) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--amber) div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--amber) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
      background: rgba(133, 79, 11, 0.12) !important;
      color: #633806 !important;
      border: none !important;
      font-weight: 500 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--amber) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
      background: rgba(133, 79, 11, 0.18) !important;
      color: #633806 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--coral) div[data-testid="stButton"] > button[kind="primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--coral) div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    [data-testid="stMain"]:has(.tq-accent-scope--coral) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
      background: rgba(216, 90, 48, 0.12) !important;
      color: #712B13 !important;
      border: none !important;
      font-weight: 500 !important;
    }
    [data-testid="stMain"]:has(.tq-accent-scope--coral) div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
      background: rgba(216, 90, 48, 0.18) !important;
      color: #712B13 !important;
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
    .mx-status:not(.mx-status--error):not(.mx-status--warn) {
      background: #F1EFE8 !important;
      color: #5F5E5A !important;
      border: none !important;
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
      color: #9FE1CB !important;
    }
    /* Mic recorder sits below the card; keep Streamlit buttons outside the panel readable */
    section.main:has(.mx-record-stage) div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):not([data-testid="stBaseButton-primary"]),
    section.main:has(.mx-record-stage) div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] {
      background: rgba(136, 135, 128, 0.10) !important;
      color: #444441 !important;
      border: 0.5px solid rgba(17, 24, 39, 0.06) !important;
    }

    /* Headings in Streamlit markdown beat .stMarkdown { font-family: sans } */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
      font-family: var(--font-display) !important;
    }
    section.main:has(.onb-marker) .stMarkdown h1.onb-title-entry,
    [data-testid="stMain"]:has(.onb-marker) .stMarkdown h1.onb-title-entry,
    .onb-wrap h1.onb-title-entry {
      font-family: var(--font-sans) !important;
      font-size: 22px !important;
      font-weight: 500 !important;
      line-height: 1.4 !important;
      margin: 0 0 8px 0 !important;
      color: #1a1a1a !important;
      text-align: left;
      letter-spacing: 0 !important;
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
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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
      border-radius: 10px;
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
    /* Pattern tap column — header shell + one transparent toggle (tp-card clone).
       Only .pat-card-shell--tap columns get overlay rules; detail/buttons are outside. */
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
      border-radius: 16px !important !important;
      background: transparent !important;
      box-shadow: none;
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
      border-color: rgba(13, 148, 136, 0.35) !important;
    }
    /* Hover: nudge the arrow right + fill its circle a touch. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:hover)
      .tp-card-chevron {
      transform: translateX(2px);
    }
    /* Tap feedback (mobile + desktop): press the card in slightly. */
    [data-testid="stMain"]:has(.tp-cards-marker)
      div[data-testid="stColumn"]:has(.tp-card)
      > [data-testid="stVerticalBlock"]:has(div[data-testid="stButton"] > button:active)
      .tp-card {
      transform: translateY(0) scale(0.985);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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
      justify-content: flex-start;
      gap: 12px;
      margin: 0 0 8px 0;
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
      border-radius: 10px;
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
      font-weight: 500;
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
      font-weight: 500;
      color: var(--text-secondary);
      letter-spacing: -0.01em;
      line-height: 1.25;
      flex: 1 1 auto;
      min-width: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-card,
    [data-testid="stMain"]:has(.tq-screen-marker) .mx-question-card.tq-card {
      background: #ffffff;
      border: 0.5px solid rgba(17, 24, 39, 0.08);
      border-radius: 16px;
      padding: 18px 16px;
      margin: 0 0 14px 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-type-badge {
      display: none;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-question,
    [data-testid="stMain"]:has(.tq-screen-marker) .mx-question-topic.tq-question {
      font-size: 15px;
      font-weight: 500;
      line-height: 1.55;
      color: #111827;
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
      border-radius: 10px;
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

    /* ── Examiner avatar (SVG + CSS; prefix examiner-avatar-) ── */
    .tq-examiner-beside-row,
    .tq-examiner-avatar-row {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      margin: 0 0 10px 0;
    }
    .tq-examiner-beside-row--recording {
      margin-top: 0;
      margin-bottom: 0;
    }
    .tq-examiner-beside-row__body,
    .tq-examiner-avatar-row__body {
      flex: 1 1 auto;
      min-width: 0;
    }
    .examiner-avatar-slot {
      flex: 0 0 auto;
      display: flex;
      align-items: flex-start;
      justify-content: center;
    }
    .examiner-avatar-slot:empty {
      width: 0;
      min-width: 0;
      margin: 0;
      padding: 0;
      overflow: hidden;
    }
    .examiner-avatar-host {
      width: var(--ea-size, 100px);
      height: var(--ea-size, 100px);
      flex-shrink: 0;
    }
    .examiner-avatar {
      width: 100%;
      height: 100%;
    }
    .examiner-avatar-svg {
      display: block;
      width: 100%;
      height: 100%;
    }
    .examiner-avatar-frame {
      filter: drop-shadow(0 1px 4px rgba(11, 61, 49, 0.12));
    }
    .examiner-avatar-eye-open {
      transform-origin: center;
      transform-box: fill-box;
      animation: examiner-avatar-eye-open 3.6s ease-in-out infinite;
    }
    .examiner-avatar-eye-highlight {
      pointer-events: none;
    }
    .examiner-avatar-eye-closed {
      opacity: 0;
      transform-origin: center;
      transform-box: fill-box;
      animation: examiner-avatar-eye-closed 3.6s ease-in-out infinite;
    }
    .examiner-avatar-eye--l .examiner-avatar-eye-open,
    .examiner-avatar-eye--l .examiner-avatar-eye-closed {
      animation-delay: 0.05s;
    }
    .examiner-avatar-eye--r .examiner-avatar-eye-open,
    .examiner-avatar-eye--r .examiner-avatar-eye-closed {
      animation-delay: 0.18s;
    }
    @keyframes examiner-avatar-eye-open {
      0%, 42%, 58%, 100% { opacity: 1; transform: scaleY(1); }
      50% { opacity: 0; transform: scaleY(0.15); }
    }
    @keyframes examiner-avatar-eye-closed {
      0%, 42%, 58%, 100% { opacity: 0; }
      50% { opacity: 1; }
    }
    .examiner-avatar-mouth-shape {
      display: none;
    }
    .examiner-avatar-mouth--closed {
      display: block;
    }
    .examiner-avatar[data-mode="speaking"] .examiner-avatar-mouth--closed {
      display: block;
      animation: examiner-avatar-mouth-closed 0.45s steps(1) infinite;
    }
    .examiner-avatar[data-mode="speaking"] .examiner-avatar-mouth--half {
      display: block;
      animation: examiner-avatar-mouth-half 0.45s steps(1) infinite;
    }
    .examiner-avatar[data-mode="speaking"] .examiner-avatar-mouth--open {
      display: block;
      animation: examiner-avatar-mouth-open 0.45s steps(1) infinite;
    }
    @keyframes examiner-avatar-mouth-closed {
      0%, 66% { opacity: 1; }
      67%, 100% { opacity: 0; }
    }
    @keyframes examiner-avatar-mouth-half {
      0%, 32% { opacity: 0; }
      33%, 66% { opacity: 1; }
      67%, 100% { opacity: 0; }
    }
    @keyframes examiner-avatar-mouth-open {
      0%, 66% { opacity: 0; }
      67%, 100% { opacity: 1; }
    }
    .examiner-avatar-head,
    .examiner-avatar-hair,
    .examiner-avatar-face {
      transform-box: fill-box;
    }
    .examiner-avatar[data-mode="listening"] .examiner-avatar-head,
    .examiner-avatar[data-mode="listening"] .examiner-avatar-hair,
    .examiner-avatar[data-mode="listening"] .examiner-avatar-face {
      transform-origin: 50px 52px;
      animation: examiner-avatar-listen-tilt 1.2s ease-in-out infinite alternate;
    }
    @keyframes examiner-avatar-listen-tilt {
      0% { transform: rotate(-2deg); }
      100% { transform: rotate(2deg); }
    }
    .examiner-avatar[data-mode="nodding"] .examiner-avatar-head,
    .examiner-avatar[data-mode="nodding"] .examiner-avatar-hair,
    .examiner-avatar[data-mode="nodding"] .examiner-avatar-face {
      transform-origin: 50px 52px;
      animation: examiner-avatar-nod 0.25s ease-in-out 6 forwards;
    }
    @keyframes examiner-avatar-nod {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(4px); }
    }
    .examiner-avatar[data-mode="nodding"] .examiner-avatar-mouth--closed,
    .examiner-avatar[data-mode="nodding"] .examiner-avatar-mouth--half,
    .examiner-avatar[data-mode="nodding"] .examiner-avatar-mouth--open {
      display: none;
    }
    .examiner-avatar[data-mode="nodding"] .examiner-avatar-mouth--smile {
      display: block;
    }
    @media (max-width: 520px) {
      .tq-examiner-beside-row,
      .tq-examiner-avatar-row {
        gap: 8px;
      }
      .tq-examiner-beside-row--question {
        flex-wrap: wrap;
      }
      .examiner-avatar-host {
        --ea-size: 84px;
      }
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
      border-radius: 0 0 16px !important 16px !important;
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
      border-radius: 0 0 16px !important 16px !important;
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
      border-radius: 10px;
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
      font-weight: 500;
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
      font-weight: 500;
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
      border-radius: 0 0 16px !important 16px !important;
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
      border-radius: 0 0 10px 12px;
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
      font-weight: 500;
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
      border-radius: 10px;
      padding: 14px;
      margin: 0 0 8px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary-label {
      display: block;
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.02em;
      color: #0F6E56;
      margin: 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin: 0 0 4px 0;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary-level-pill {
      flex-shrink: 0;
      background: #E1F5EE;
      color: #04342C;
      font-size: 13px;
      font-weight: 500;
      padding: 4px 12px;
      border-radius: 999px;
      letter-spacing: -0.01em;
      white-space: nowrap;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary-level-pill--missing {
      background: #F3F4F6;
      color: #6B7280;
      font-weight: 500;
    }
    [data-testid="stMain"]:has(.tq-screen-marker) .tq-feedback-summary-scope {
      margin: 0 0 6px 0;
      font-size: 11px;
      font-weight: 400;
      color: #888780;
      line-height: 1.35;
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
      border-radius: 10px;
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
      font-weight: 500;
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
      font-weight: 500;
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

    /* Onboarding card — final cascade (beats Streamlit default h1 / display font) */
    .onb-wrap { max-width: 420px; margin: 0 auto; box-sizing: border-box; }
    .onb-card {
      background: #ffffff;
      border: 0.5px solid rgba(0, 0, 0, 0.12);
      border-radius: 16px;
      padding: 28px 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
      box-sizing: border-box;
    }
    .onb-brand { display: flex; align-items: center; gap: 10px; }
    .onb-brand-icon {
      width: 40px; height: 40px; border-radius: 50%;
      background: #E1F5EE; color: #0F6E56;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      overflow: hidden;
    }
    .onb-brand-icon svg { display: block; width: 40px; height: 40px; }
    .onb-brand-text {
      font-family: var(--font-sans) !important;
      font-size: 14px; font-weight: 500; color: #0F6E56;
    }
    h1.onb-title-entry,
    .stMarkdown h1.onb-title-entry,
    .onb-wrap h1.onb-title-entry {
      font-family: var(--font-sans) !important;
      font-size: 22px !important;
      font-weight: 500 !important;
      line-height: 1.4 !important;
      margin: 0 0 8px 0 !important;
      color: #1a1a1a !important;
      text-align: left;
      letter-spacing: 0 !important;
    }
    .onb-sub-hero {
      font-family: var(--font-sans) !important;
      font-size: 15px; color: #5f5e5a; line-height: 1.7; margin: 0; text-align: left;
    }
    .onb-steps { display: flex; flex-direction: column; gap: 10px; margin: 0; padding: 0; }
    .onb-step-card {
      display: flex; align-items: center; gap: 8px;
      background: #f5f4f0; border-radius: 8px; padding: 12px 14px; box-sizing: border-box;
    }
    .onb-step-num {
      width: 28px; height: 28px; border-radius: 50%;
      background: #9FE1CB; color: #04342C;
      font-family: var(--font-sans) !important;
      font-size: 14px; font-weight: 500;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .onb-step-ico { color: #0F6E56; display: flex; align-items: center; flex-shrink: 0; }
    .onb-step-ico svg { display: block; width: 18px; height: 18px; }
    .onb-step-title {
      font-family: var(--font-sans) !important;
      font-size: 15px; color: #1a1a1a; flex: 1; min-width: 0;
    }
    .onb-footnote {
      font-family: var(--font-sans) !important;
      font-size: 13px; color: #888780; text-align: center; margin: 12px 0 0 0;
    }

    /* Scripts tab — external Smart Store link (must open outside Streamlit iframe) */
    section.main:has(.scripts-store-marker) a.scripts-store-cta,
    [data-testid="stMain"]:has(.scripts-store-marker) a.scripts-store-cta {
      display: block;
      width: 100%;
      box-sizing: border-box;
      text-align: center;
      text-decoration: none;
      padding: 0.65rem 1rem;
      border-radius: 0.5rem;
      font-family: var(--font-sans) !important;
      font-size: 1rem;
      font-weight: 500;
      color: #ffffff !important;
      background: #0F6E56;
      border: 1px solid rgba(15, 118, 110, 0.35);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    section.main:has(.scripts-store-marker) a.scripts-store-cta:hover,
    [data-testid="stMain"]:has(.scripts-store-marker) a.scripts-store-cta:hover {
      background: #0b5c47;
      color: #ffffff !important;
    }
"""


def inject_multiselect_chip_scroll_fix() -> None:
    """Reset BaseWeb multiselect value-container scrollLeft (clips first chip char)."""
    import streamlit.components.v1 as components

    components.html(
        """
<script>
(function () {
  const doc = window.parent.document;
  function reset() {
    doc.querySelectorAll(
      '[data-testid="stMultiSelect"] [data-baseweb="select"] > div > div:first-child'
    ).forEach(function (el) {
      if (el && el.scrollLeft) el.scrollLeft = 0;
    });
  }
  reset();
  var obs = new MutationObserver(reset);
  obs.observe(doc.body, { childList: true, subtree: true, attributes: true });
  window.addEventListener("load", reset);
})();
</script>
        """,
        height=0,
        width=0,
    )


def inject_global_styles() -> None:
    import streamlit as st

    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)
