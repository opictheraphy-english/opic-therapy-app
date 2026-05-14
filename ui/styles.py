"""Global Streamlit CSS — premium medical AI design system."""

GLOBAL_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
      --mint: #0d9488;
      --mint-soft: #ccfbf1;
      --mint-muted: rgba(13, 148, 136, 0.12);
      --navy: #0f172a;
      --navy-soft: #1e293b;
      --bg-warm: #fafaf9;
      --bg-page: linear-gradient(180deg, #fafaf9 0%, #f4f4f5 48%, #f1f5f9 100%);
      --surface: rgba(255, 255, 255, 0.72);
      --border-subtle: rgba(15, 23, 42, 0.08);
      --text: #0f172a;
      --text-secondary: #475569;
      --text-muted: #64748b;
      --text-soft: #94a3b8;
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

    html, body, [class*="css"], .stMarkdown { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; color: var(--text); }

    /* Lock html/body background to the page gradient so anchor navigations
     * (?nav=...) don't flash white between the old page unload and the new
     * Streamlit shell paint. */
    html, body {
      background: #f4f4f5 !important;
      background-color: #f4f4f5 !important;
    }

    .stApp {
      background: var(--bg-page) !important;
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
      padding-bottom: 6.5rem !important;
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

    /* ------------------------------------------------------------------
     * Smart feedback cards — grammar fix + alternative expressions
     * ------------------------------------------------------------------ */
    .grammar-fix {
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 12px 14px;
      margin: 6px 0;
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
      color: #b91c1c;
      text-decoration: line-through;
      text-decoration-color: rgba(185, 28, 28, 0.4);
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

    .alt-card {
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 12px 14px;
      margin: 6px 0;
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

    /* Floating bottom navigation */
    .bottom-nav-dock {
      position: fixed;
      left: 50%;
      transform: translateX(-50%);
      bottom: max(12px, env(safe-area-inset-bottom, 12px));
      width: min(560px, calc(100vw - 28px));
      z-index: 10000;
      pointer-events: none;
    }
    .bottom-nav-inner {
      pointer-events: auto;
      display: flex;
      justify-content: space-between;
      align-items: stretch;
      gap: 4px;
      padding: 10px 12px;
      background: rgba(255, 255, 255, 0.68);
      backdrop-filter: saturate(180%) blur(20px);
      -webkit-backdrop-filter: saturate(180%) blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.7);
      border-radius: 22px;
      box-shadow:
        0 4px 24px rgba(15, 23, 42, 0.08),
        0 1px 0 rgba(255, 255, 255, 0.9) inset;
      /* No fade-up animation on rerun — the dock should *feel* persistent.
       * Re-animating it on every nav switch is the strongest "page reloaded"
       * signal the user sees. */
    }
    .bottom-nav-inner a.nav-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 8px 4px;
      min-height: 52px;
      border-radius: 16px;
      text-decoration: none !important;
      color: var(--text-muted) !important;
      font-size: 0.62rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      transition: color 0.2s ease, background 0.2s ease, transform 0.15s ease;
    }
    .bottom-nav-inner a.nav-item .nav-ico {
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-soft);
      transition: color 0.2s ease;
    }
    .bottom-nav-inner a.nav-item:hover {
      color: var(--navy) !important;
      background: rgba(15, 23, 42, 0.04);
    }
    .bottom-nav-inner a.nav-item:hover .nav-ico { color: var(--navy); }
    .bottom-nav-inner a.nav-item.active {
      color: var(--mint) !important;
      background: var(--mint-muted);
    }
    .bottom-nav-inner a.nav-item.active .nav-ico {
      color: var(--mint);
    }
    .bottom-nav-inner a.nav-item:active {
      transform: scale(0.97);
    }
    .nav-label {
      line-height: 1.2;
      max-width: 64px;
      text-align: center;
    }

    .page-bottom-space { height: 96px; }

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
"""


def inject_global_styles() -> None:
    import streamlit as st

    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)
