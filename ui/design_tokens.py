"""Design tokens — single source of truth for OPIc Therapy Clinic UI.

New screens: import constants from this module (colors, radii, type, spacing).
CSS: ``get_css_variables()`` injects ``:root`` custom properties; ``styles.py``
builds ``GLOBAL_CSS`` via ``_GLOBAL_CSS_TEMPLATE.format(**FORMAT_KWARGS)``.
HTML cards may use ``var(--brand-700)`` etc. after injection.
"""

from __future__ import annotations

# --- Brand green ---
BRAND_900 = "#0b3d31"  # Deepest brand — dark emphasis
BRAND_700 = "#0f6e56"  # Main brand — primary actions, key labels
BRAND_500 = "#1d9e75"  # Mid green — chevrons, icons, secondary actions
BRAND_300 = "#9fd4bf"  # Soft green — card hover border
BRAND_200 = "#d7ece2"  # Light green fill — chevron hover background
BRAND_100 = "#e1f5ee"  # Icon tile background
BRAND_50 = "#eefaf5"  # Subtle green surface — chevron circle fill
ON_GREEN_SUB = "#bfe4d4"  # Subtitle text on green hero cards

# --- Neutral ---
TEXT_900 = "#1f2a24"  # Primary body text (dark)
TEXT_600 = "#5f6b64"  # Secondary / meta text
TEXT_400 = "#8a948d"  # Captions, card subtitles
TEXT_200 = "#c4cbc6"  # Disabled / placeholder (reserved)
BORDER = "#e5e7e2"  # Card & control borders
HAIRLINE = "#f0f2f0"  # Footer dividers (reserved)
DASHED = "#e5ece8"  # Dashed row separators in goal lists
BG_HOVER = "#fafcfb"  # Hover surface on white cards
BG_APP = "#f6f8f6"  # App page background shell

# --- Accent ---
AMBER_BG = "#fff4e3"  # Badge background — “처음이라면”
AMBER_TEXT = "#854f0b"  # Badge / warning text
AMBER_ICON = "#ba7517"  # Amber icon accent (reserved)

# --- Radius (px) ---
RADIUS_LG = 16  # Large cards, hero
RADIUS_MD = 14  # Standard cards
RADIUS_SM = 12  # Compact cards, shortcuts
RADIUS_TILE = 10  # Icon tiles
RADIUS_PILL = 999  # Pills, circular badges

# --- Font size (px) ---
FS_TITLE = 18  # Screen / hero titles
FS_SECTION = 15  # Section headings
FS_CARD = 13.5  # Card titles
FS_BODY = 12.5  # Body, shortcut labels
FS_CAPTION = 11  # Captions, goal strip
FS_BADGE = 10.5  # Small badges

# --- Spacing (px) ---
PAD_CARD = 16  # Standard card padding
PAD_CARD_LG = 18  # Hero / roomy card padding
GAP_CARD = 10  # In-card / grid gaps
GAP_SECTION = 16  # Section vertical rhythm (reserved)

# --- Components ---
CHEVRON_SIZE = 32  # Quiet chevron circle — BRAND_50 fill, BRAND_500 glyph

# --- Typography / font ---
FONT_FAMILY = (
    '"Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, '
    'system-ui, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif'
)
PRETENDARD_IMPORT_URL = (
    "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/"
    "variable/pretendardvariable-dynamic-subset.min.css"
)
LETTER_SPACING_BODY = "-0.01em"
LETTER_SPACING_TITLE = "-0.02em"
LINE_HEIGHT_BODY = "1.55"
LINE_HEIGHT_TITLE = "1.35"


def get_pretendard_import() -> str:
    """Single @import for Pretendard Variable (dynamic-subset CDN).

    Injected once at the top of ``GLOBAL_CSS``. If jsDelivr is blocked or offline,
    ``FONT_FAMILY`` falls through to system UI fonts without breaking layout.
    """
    return f'@import url("{PRETENDARD_IMPORT_URL}");'


def get_css_variables() -> str:
    """Return ``:root { --token: value; }`` block for design-token CSS variables."""
    return f"""
    :root {{
      --font-family: {FONT_FAMILY};
      --font-sans: {FONT_FAMILY};
      --font-display: {FONT_FAMILY};
      --letter-spacing-body: {LETTER_SPACING_BODY};
      --letter-spacing-title: {LETTER_SPACING_TITLE};
      --line-height-body: {LINE_HEIGHT_BODY};
      --line-height-title: {LINE_HEIGHT_TITLE};
      --brand-900: {BRAND_900};
      --brand-700: {BRAND_700};
      --brand-500: {BRAND_500};
      --brand-300: {BRAND_300};
      --brand-200: {BRAND_200};
      --brand-100: {BRAND_100};
      --brand-50: {BRAND_50};
      --on-green-sub: {ON_GREEN_SUB};
      --text-900: {TEXT_900};
      --text-600: {TEXT_600};
      --text-400: {TEXT_400};
      --text-200: {TEXT_200};
      --border: {BORDER};
      --hairline: {HAIRLINE};
      --dashed: {DASHED};
      --bg-hover: {BG_HOVER};
      --bg-app: {BG_APP};
      --amber-bg: {AMBER_BG};
      --amber-text: {AMBER_TEXT};
      --amber-icon: {AMBER_ICON};
      --radius-lg: {RADIUS_LG}px;
      --radius-md: {RADIUS_MD}px;
      --radius-sm: {RADIUS_SM}px;
      --radius-tile: {RADIUS_TILE}px;
      --radius-pill: {RADIUS_PILL}px;
      --fs-title: {FS_TITLE}px;
      --fs-section: {FS_SECTION}px;
      --fs-card: {FS_CARD}px;
      --fs-body: {FS_BODY}px;
      --fs-caption: {FS_CAPTION}px;
      --fs-badge: {FS_BADGE}px;
      --pad-card: {PAD_CARD}px;
      --pad-card-lg: {PAD_CARD_LG}px;
      --gap-card: {GAP_CARD}px;
      --gap-section: {GAP_SECTION}px;
      --chevron-size: {CHEVRON_SIZE}px;
    }}
"""


def get_format_kwargs() -> dict[str, str | int | float]:
    """Keyword args for ``_GLOBAL_CSS_TEMPLATE.format(**FORMAT_KWARGS)``."""
    return {
        "FONT_FAMILY": FONT_FAMILY,
        "LETTER_SPACING_BODY": LETTER_SPACING_BODY,
        "LETTER_SPACING_TITLE": LETTER_SPACING_TITLE,
        "LINE_HEIGHT_BODY": LINE_HEIGHT_BODY,
        "LINE_HEIGHT_TITLE": LINE_HEIGHT_TITLE,
        "BRAND_900": BRAND_900,
        "BRAND_700": BRAND_700,
        "BRAND_500": BRAND_500,
        "BRAND_300": BRAND_300,
        "BRAND_200": BRAND_200,
        "BRAND_100": BRAND_100,
        "BRAND_50": BRAND_50,
        "ON_GREEN_SUB": ON_GREEN_SUB,
        "TEXT_900": TEXT_900,
        "TEXT_600": TEXT_600,
        "TEXT_400": TEXT_400,
        "TEXT_200": TEXT_200,
        "BORDER": BORDER,
        "HAIRLINE": HAIRLINE,
        "DASHED": DASHED,
        "BG_HOVER": BG_HOVER,
        "BG_APP": BG_APP,
        "AMBER_BG": AMBER_BG,
        "AMBER_TEXT": AMBER_TEXT,
        "AMBER_ICON": AMBER_ICON,
        "RADIUS_LG": RADIUS_LG,
        "RADIUS_MD": RADIUS_MD,
        "RADIUS_SM": RADIUS_SM,
        "RADIUS_TILE": RADIUS_TILE,
        "RADIUS_PILL": RADIUS_PILL,
        "FS_TITLE": FS_TITLE,
        "FS_SECTION": FS_SECTION,
        "FS_CARD": FS_CARD,
        "FS_BODY": FS_BODY,
        "FS_CAPTION": FS_CAPTION,
        "FS_BADGE": FS_BADGE,
        "PAD_CARD": PAD_CARD,
        "PAD_CARD_LG": PAD_CARD_LG,
        "GAP_CARD": GAP_CARD,
        "GAP_SECTION": GAP_SECTION,
        "CHEVRON_SIZE": CHEVRON_SIZE,
    }


FORMAT_KWARGS = get_format_kwargs()
