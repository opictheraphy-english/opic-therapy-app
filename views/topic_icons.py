"""Inline SVG icons for topic-practice cards.

Same format as home._QA_ICONS — maps an icon name to an inline SVG string.
Icons are Tabler outline icons; stroke uses currentColor so the surrounding
CSS (.tp-card-ico color) controls the colour.
"""

from typing import Dict

_SVG_ATTRS = (
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"'
)

TOPIC_ICONS: Dict[str, str] = {
    "home": f'<svg {_SVG_ATTRS}><path d="M5 12l-2 0l9 -9l9 9l-2 0" /> <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7" /> <path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6" /></svg>',
    "users": f'<svg {_SVG_ATTRS}><path d="M5 7a4 4 0 1 0 8 0a4 4 0 1 0 -8 0" /> <path d="M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2" /> <path d="M16 3.13a4 4 0 0 1 0 7.75" /> <path d="M21 21v-2a4 4 0 0 0 -3 -3.85" /></svg>',
    "device-tv": f'<svg {_SVG_ATTRS}><path d="M3 9a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2l0 -9" /> <path d="M16 3l-4 4l-4 -4" /></svg>',
    "masks-theater": f'<svg {_SVG_ATTRS}><path d="M13.192 9h6.616a2 2 0 0 1 1.992 2.183l-.567 6.182a4 4 0 0 1 -3.983 3.635h-1.5a4 4 0 0 1 -3.983 -3.635l-.567 -6.182a2 2 0 0 1 1.992 -2.183" /> <path d="M15 13h.01" /> <path d="M18 13h.01" /> <path d="M15 16.5c1 .667 2 .667 3 0" /> <path d="M8.632 15.982a4.037 4.037 0 0 1 -.382 .018h-1.5a4 4 0 0 1 -3.983 -3.635l-.567 -6.182a2 2 0 0 1 1.992 -2.183h6.616a2 2 0 0 1 2 2" /> <path d="M6 8h.01" /> <path d="M9 8h.01" /> <path d="M6 12c.764 -.51 1.528 -.63 2.291 -.36" /></svg>',
    "tree": f'<svg {_SVG_ATTRS}><path d="M12 13l-2 -2" /> <path d="M12 12l2 -2" /> <path d="M12 21v-13" /> <path d="M9.824 16a3 3 0 0 1 -2.743 -3.69a3 3 0 0 1 .304 -4.833a3 3 0 0 1 4.615 -3.707a3 3 0 0 1 4.614 3.707a3 3 0 0 1 .305 4.833a3 3 0 0 1 -2.919 3.695h-4l-.176 -.005" /></svg>',
    "beach": f'<svg {_SVG_ATTRS}><path d="M17.553 16.75a7.5 7.5 0 0 0 -10.606 0" /> <path d="M18 3.804a6 6 0 0 0 -8.196 2.196l10.392 6a6 6 0 0 0 -2.196 -8.196" /> <path d="M16.732 10c1.658 -2.87 2.225 -5.644 1.268 -6.196c-.957 -.552 -3.075 1.326 -4.732 4.196" /> <path d="M15 9l-3 5.196" /> <path d="M3 19.25a2.4 2.4 0 0 1 1 -.25a2.4 2.4 0 0 1 2 1a2.4 2.4 0 0 0 2 1a2.4 2.4 0 0 0 2 -1a2.4 2.4 0 0 1 2 -1a2.4 2.4 0 0 1 2 1a2.4 2.4 0 0 0 2 1a2.4 2.4 0 0 0 2 -1a2.4 2.4 0 0 1 2 -1a2.4 2.4 0 0 1 1 .25" /></svg>',
    "ball-football": f'<svg {_SVG_ATTRS}><path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" /> <path d="M12 7l4.76 3.45l-1.76 5.55h-6l-1.76 -5.55l4.76 -3.45" /> <path d="M12 7v-4m3 13l2.5 3m-.74 -8.55l3.74 -1.45m-11.44 7.05l-2.56 2.95m.74 -8.55l-3.74 -1.45" /></svg>',
    "coffee": f'<svg {_SVG_ATTRS}><path d="M3 14c.83 .642 2.077 1.017 3.5 1c1.423 .017 2.67 -.358 3.5 -1c.83 -.642 2.077 -1.017 3.5 -1c1.423 -.017 2.67 .358 3.5 1" /> <path d="M8 3a2.4 2.4 0 0 0 -1 2a2.4 2.4 0 0 0 1 2" /> <path d="M12 3a2.4 2.4 0 0 0 -1 2a2.4 2.4 0 0 0 1 2" /> <path d="M3 10h14v5a6 6 0 0 1 -6 6h-2a6 6 0 0 1 -6 -6v-5" /> <path d="M16.746 16.726a3 3 0 1 0 .252 -5.555" /></svg>',
    "shopping-bag": f'<svg {_SVG_ATTRS}><path d="M6.331 8h11.339a2 2 0 0 1 1.977 2.304l-1.255 8.152a3 3 0 0 1 -2.966 2.544h-6.852a3 3 0 0 1 -2.965 -2.544l-1.255 -8.152a2 2 0 0 1 1.977 -2.304" /> <path d="M9 11v-5a3 3 0 0 1 6 0v5" /></svg>',
    "music": f'<svg {_SVG_ATTRS}><path d="M3 17a3 3 0 1 0 6 0a3 3 0 0 0 -6 0" /> <path d="M13 17a3 3 0 1 0 6 0a3 3 0 0 0 -6 0" /> <path d="M9 17v-13h10v13" /> <path d="M9 8h10" /></svg>',
    "microphone-2": f'<svg {_SVG_ATTRS}><path d="M15 12.9a5 5 0 1 0 -3.902 -3.9" /> <path d="M15 12.9l-3.902 -3.899l-7.513 8.584a2 2 0 1 0 2.827 2.83l8.588 -7.515" /></svg>',
    "guitar-pick": f'<svg {_SVG_ATTRS}><path d="M16 18.5c2 -2.5 4 -6.5 4 -10.5c0 -2.946 -2.084 -4.157 -4.204 -4.654c-.864 -.23 -2.13 -.346 -3.796 -.346c-1.667 0 -2.932 .115 -3.796 .346c-2.12 .497 -4.204 1.708 -4.204 4.654c0 3.312 2 8 4 10.5c.297 .37 .618 .731 .963 1.081l.354 .347a3.9 3.9 0 0 0 5.364 0a14.05 14.05 0 0 0 1.319 -1.428" /></svg>',
    "chef-hat": f'<svg {_SVG_ATTRS}><path d="M12 3c1.918 0 3.52 1.35 3.91 3.151a4 4 0 0 1 2.09 7.723l0 7.126h-12v-7.126a4 4 0 1 1 2.092 -7.723a4 4 0 0 1 3.908 -3.151" /> <path d="M6.161 17.009l11.839 -.009" /></svg>',
    "book": f'<svg {_SVG_ATTRS}><path d="M3 19a9 9 0 0 1 9 0a9 9 0 0 1 9 0" /> <path d="M3 6a9 9 0 0 1 9 0a9 9 0 0 1 9 0" /> <path d="M3 6l0 13" /> <path d="M12 6l0 13" /> <path d="M21 6l0 13" /></svg>',
    "walk": f'<svg {_SVG_ATTRS}><path d="M12 4a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" /> <path d="M7 21l3 -4" /> <path d="M16 21l-2 -4l-3 -3l1 -6" /> <path d="M6 12l2 -3l4 -1l3 3l3 1" /></svg>',
    "run": f'<svg {_SVG_ATTRS}><path d="M11.007 5a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" /> <path d="M4 17l5 1l.75 -1.5" /> <path d="M15 21v-4l-4 -3l1 -6" /> <path d="M7 12v-3l5 -1l3 3l3 1" /></svg>',
    "barbell": f'<svg {_SVG_ATTRS}><path d="M2 12h1" /> <path d="M6 8h-2a1 1 0 0 0 -1 1v6a1 1 0 0 0 1 1h2" /> <path d="M6 7v10a1 1 0 0 0 1 1h1a1 1 0 0 0 1 -1v-10a1 1 0 0 0 -1 -1h-1a1 1 0 0 0 -1 1" /> <path d="M9 12h6" /> <path d="M15 7v10a1 1 0 0 0 1 1h1a1 1 0 0 0 1 -1v-10a1 1 0 0 0 -1 -1h-1a1 1 0 0 0 -1 1" /> <path d="M18 8h2a1 1 0 0 1 1 1v6a1 1 0 0 1 -1 1h-2" /> <path d="M22 12h-1" /></svg>',
    "plane": f'<svg {_SVG_ATTRS}><path d="M16 10h4a2 2 0 0 1 0 4h-4l-4 7h-3l2 -7h-4l-2 2h-3l2 -4l-2 -4h3l2 2h4l-2 -7h3l4 7" /></svg>',
    "umbrella": f'<svg {_SVG_ATTRS}><path d="M4 12a8 8 0 0 1 16 0l-16 0" /> <path d="M12 12v6a2 2 0 0 0 4 0" /></svg>',
    "map-pin": f'<svg {_SVG_ATTRS}><path d="M9 11a3 3 0 1 0 6 0a3 3 0 0 0 -6 0" /> <path d="M17.657 16.657l-4.243 4.243a2 2 0 0 1 -2.827 0l-4.244 -4.243a8 8 0 1 1 11.314 0" /></svg>',
    "sofa": f'<svg {_SVG_ATTRS}><path d="M4 11a2 2 0 0 1 2 2v1h12v-1a2 2 0 1 1 4 0v5a1 1 0 0 1 -1 1h-18a1 1 0 0 1 -1 -1v-5a2 2 0 0 1 2 -2" /> <path d="M4 11v-3a3 3 0 0 1 3 -3h10a3 3 0 0 1 3 3v3" /> <path d="M12 5v9" /></svg>',
    "gift": f'<svg {_SVG_ATTRS}><path d="M3 9a1 1 0 0 1 1 -1h16a1 1 0 0 1 1 1v2a1 1 0 0 1 -1 1h-16a1 1 0 0 1 -1 -1l0 -2" /> <path d="M12 8l0 13" /> <path d="M19 12v7a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-7" /> <path d="M7.5 8a2.5 2.5 0 0 1 0 -5a4.8 8 0 0 1 4.5 5a4.8 8 0 0 1 4.5 -5a2.5 2.5 0 0 1 0 5" /></svg>',
    "recycle": f'<svg {_SVG_ATTRS}><path d="M12 17l-2 2l2 2" /> <path d="M10 19h9a2 2 0 0 0 1.75 -2.75l-.55 -1" /> <path d="M8.536 11l-.732 -2.732l-2.732 .732" /> <path d="M7.804 8.268l-4.5 7.794a2 2 0 0 0 1.506 2.89l1.141 .024" /> <path d="M15.464 11l2.732 .732l.732 -2.732" /> <path d="M18.196 11.732l-4.5 -7.794a2 2 0 0 0 -3.256 -.14l-.591 .976" /></svg>',
    "world": f'<svg {_SVG_ATTRS}><path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0" /> <path d="M3.6 9h16.8" /> <path d="M3.6 15h16.8" /> <path d="M11.5 3a17 17 0 0 0 0 18" /> <path d="M12.5 3a17 17 0 0 1 0 18" /></svg>',
    "mood-smile": f'<svg {_SVG_ATTRS}><path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" /> <path d="M9 10l.01 0" /> <path d="M15 10l.01 0" /> <path d="M9.5 15a3.5 3.5 0 0 0 5 0" /></svg>',
    "confetti": f'<svg {_SVG_ATTRS}><path d="M4 5h2" /> <path d="M5 4v2" /> <path d="M11.5 4l-.5 2" /> <path d="M18 5h2" /> <path d="M19 4v2" /> <path d="M15 9l-1 1" /> <path d="M18 13l2 -.5" /> <path d="M18 19h2" /> <path d="M19 18v2" /> <path d="M14 16.518l-6.518 -6.518l-4.39 9.58a1 1 0 0 0 1.329 1.329l9.579 -4.39" /></svg>',
    "building-skyscraper": f'<svg {_SVG_ATTRS}><path d="M3 21l18 0" /> <path d="M5 21v-14l8 -4v18" /> <path d="M19 21v-10l-6 -4" /> <path d="M9 9l0 .01" /> <path d="M9 12l0 .01" /> <path d="M9 15l0 .01" /> <path d="M9 18l0 .01" /></svg>',
    "device-laptop": f'<svg {_SVG_ATTRS}><path d="M3 19l18 0" /> <path d="M5 7a1 1 0 0 1 1 -1h12a1 1 0 0 1 1 1v8a1 1 0 0 1 -1 1h-12a1 1 0 0 1 -1 -1l0 -8" /></svg>',
    "device-mobile": f'<svg {_SVG_ATTRS}><path d="M6 5a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v14a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2v-14" /> <path d="M11 4h2" /> <path d="M12 17v.01" /></svg>',
    "wifi": f'<svg {_SVG_ATTRS}><path d="M12 18l.01 0" /> <path d="M9.172 15.172a4 4 0 0 1 5.656 0" /> <path d="M6.343 12.343a8 8 0 0 1 11.314 0" /> <path d="M3.515 9.515c4.686 -4.687 12.284 -4.687 17 0" /></svg>',
    "building-factory": f'<svg {_SVG_ATTRS}><path d="M4 21c1.147 -4.02 1.983 -8.027 2 -12h6c.017 3.973 .853 7.98 2 12" /> <path d="M12.5 13h4.5c.025 2.612 .894 5.296 2 8" /> <path d="M9 5a2.4 2.4 0 0 1 2 -1a2.4 2.4 0 0 1 2 1a2.4 2.4 0 0 0 2 1a2.4 2.4 0 0 0 2 -1a2.4 2.4 0 0 1 2 -1a2.4 2.4 0 0 1 2 1" /> <path d="M3 21l19 0" /></svg>',
    "bus": f'<svg {_SVG_ATTRS}><path d="M4 17a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" /> <path d="M16 17a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" /> <path d="M4 17h-2v-11a1 1 0 0 1 1 -1h14a5 7 0 0 1 5 7v5h-2m-4 0h-8" /> <path d="M16 5l1.5 7l4.5 0" /> <path d="M2 10l15 0" /> <path d="M7 5l0 5" /> <path d="M12 5l0 5" /></svg>',
    "tools-kitchen-2": f'<svg {_SVG_ATTRS}><path d="M19 3v12h-5c-.023 -3.681 .184 -7.406 5 -12m0 12v6h-1v-3m-10 -14v17m-3 -17v3a3 3 0 1 0 6 0v-3" /></svg>',
    "soup": f'<svg {_SVG_ATTRS}><path d="M4 11h16a1 1 0 0 1 1 1v.5c0 1.5 -2.517 5.573 -4 6.5v1a1 1 0 0 1 -1 1h-8a1 1 0 0 1 -1 -1v-1c-1.687 -1.054 -4 -5 -4 -6.5v-.5a1 1 0 0 1 1 -1" /> <path d="M12 4a2.4 2.4 0 0 0 -1 2a2.4 2.4 0 0 0 1 2" /> <path d="M16 4a2.4 2.4 0 0 0 -1 2a2.4 2.4 0 0 0 1 2" /> <path d="M8 4a2.4 2.4 0 0 0 -1 2a2.4 2.4 0 0 0 1 2" /></svg>',
    "heartbeat": f'<svg {_SVG_ATTRS}><path d="M19.5 13.572l-7.5 7.428l-2.896 -2.868m-6.117 -8.104a5 5 0 0 1 9.013 -3.022a5 5 0 1 1 7.5 6.572" /> <path d="M3 13h2l2 3l2 -6l1 3h3" /></svg>',
    "building-bank": f'<svg {_SVG_ATTRS}><path d="M3 21l18 0" /> <path d="M3 10l18 0" /> <path d="M5 6l7 -3l7 3" /> <path d="M4 10l0 11" /> <path d="M20 10l0 11" /> <path d="M8 14l0 3" /> <path d="M12 14l0 3" /> <path d="M16 14l0 3" /></svg>',
    "calendar-event": f'<svg {_SVG_ATTRS}><path d="M4 7a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2l0 -12" /> <path d="M16 3l0 4" /> <path d="M8 3l0 4" /> <path d="M4 11l16 0" /> <path d="M8 15h2v2h-2l0 -2" /></svg>',
    "cloud": f'<svg {_SVG_ATTRS}><path d="M6.657 18c-2.572 0 -4.657 -2.007 -4.657 -4.483c0 -2.475 2.085 -4.482 4.657 -4.482c.393 -1.762 1.794 -3.2 3.675 -3.773c1.88 -.572 3.956 -.193 5.444 1c1.488 1.19 2.162 3.007 1.77 4.769h.99c1.913 0 3.464 1.56 3.464 3.486c0 1.927 -1.551 3.487 -3.465 3.487h-11.878" /></svg>',
    "shirt": f'<svg {_SVG_ATTRS}><path d="M15 4l6 2v5h-3v8a1 1 0 0 1 -1 1h-10a1 1 0 0 1 -1 -1v-8h-3v-5l6 -2a3 3 0 0 0 6 0" /></svg>',
    "circle": f'<svg {_SVG_ATTRS}><path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" /></svg>',
}
