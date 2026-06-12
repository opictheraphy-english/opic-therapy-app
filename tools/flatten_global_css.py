#!/usr/bin/env python3
"""Conservative single-line CSS flattener for ui/styles.py."""

from __future__ import annotations

import re
from pathlib import Path

FLAT = "0 1px 2px rgba(15, 23, 42, 0.04)"
PAGE = "#FAFAF9"
CARD = "#ffffff"
PRIMARY = "#0F6E56"
PRIMARY_HOVER = "#0b5c47"
PROGRESS = "#1D9E75"
START = "/* --- Onboarding (first entry, scoped)"
END = "/* Hero */"


def in_zone(line: str, protected: bool) -> bool:
    if protected:
        return True
    return bool(re.search(r"\.onb-|\.splash-|:has\(\.onb-marker\)|:has\(\.splash-marker\)", line))


def map_radius(val: str) -> str:
    if "999" in val or "50%" in val:
        return val
    m = re.search(r"(\d+(?:\.\d+)?)(px|rem)", val)
    if not m:
        return val
    n = float(m.group(1)) * (16 if m.group(2) == "rem" else 1)
    if n >= 15:
        tgt = 16
    elif n >= 11:
        tgt = 10
    else:
        return val
    imp = " !important" if "!important" in val else ""
    return re.sub(r"(\d+(?:\.\d+)?)(px|rem)", f"{tgt}px{imp}", val, count=1)


def transform_line(line: str, ctx: str) -> str | None:
    """Return new line, None to drop, or line unchanged sentinel."""
    stripped = line.strip()
    if not stripped or stripped.startswith(("/*", "*", "@", "}")) or "{" in stripped:
        return line
    if ":" not in stripped or ";" not in stripped:
        return line

    prop, _, val = stripped.partition(":")
    val = val.strip().rstrip(";")
    p = prop.strip().lower()
    indent = line[: len(line) - len(line.lstrip())]
    hover = ":hover" in ctx
    keep_shadow = ".topbar" in ctx or ".opic-bottom-nav" in ctx

    if p in ("backdrop-filter", "-webkit-backdrop-filter"):
        return None

    if p == "box-shadow":
        if keep_shadow:
            return line
        if hover:
            return None
        if val.lower() in ("none", "none !important"):
            return f"{indent}box-shadow: none;"
        return f"{indent}box-shadow: {FLAT};"

    if p == "transform" and hover and "translatey" in val.lower():
        return None

    if p == "font-weight" and re.match(r"^(600|700|800)(\s*!important)?$", val):
        imp = " !important" if "!important" in val else ""
        return f"{indent}font-weight: 500{imp};"

    if p == "border-radius":
        return f"{indent}border-radius: {map_radius(val)};"

    if p == "background" and "gradient" in val.lower():
        if ".mx-record-stage::before" in ctx.replace(" ", ""):
            return f"{indent}background: none;"
        if "progress-fill" in ctx or "progress" in ctx and "fill" in ctx:
            return f"{indent}background: {PROGRESS};"
        if "primary" in ctx or "baseButton-primary" in ctx:
            if ":hover" in ctx:
                return f"{indent}background: {PRIMARY_HOVER} !important;"
            if "tq-accent-scope--blue" in ctx:
                return f"{indent}background: #2c6fb8 !important;"
            if "tq-accent-scope--purple" in ctx:
                return f"{indent}background: #534ab7 !important;"
            if "tq-accent-scope--pink" in ctx:
                return f"{indent}background: #b83f66 !important;"
            if "tq-accent-scope--amber" in ctx:
                return f"{indent}background: #8a560f !important;"
            if "tq-accent-scope--coral" in ctx:
                return f"{indent}background: #b23f1c !important;"
            return f"{indent}background: {PRIMARY} !important;"
        if ".mx-record-stage" in ctx and "::before" not in ctx:
            # timer sub-panel should stay light — only main stage selector
            if ".mx-rec-timer" in ctx or ".mx-record-stage ." in ctx:
                return f"{indent}background: #ffffff;"
            return f"{indent}background: #0f172a;"
        if ".opic-bottom-nav" in ctx:
            return f"{indent}background: {CARD};"
        return f"{indent}background: {CARD};"

    if p == "background" and p == "background" and "rgba(255" in val and ".glass-card" in ctx:
        return f"{indent}background: {CARD};"

    if p == "filter" and hover and "brightness" in val.lower():
        return None

    if p == "opacity" and ".mx-record-stage::before" in ctx.replace(" ", ""):
        return f"{indent}opacity: 0;"

    return line


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "ui" / "styles.py"
    text = path.read_text(encoding="utf-8")
    head = 'GLOBAL_CSS = """\n'
    s = text.index(head) + len(head)
    e = text.rindex('\n"""')
    lines = text[s:e].split("\n")

    protected = False
    ctx = ""
    out: list[str] = []
    for line in lines:
        if START in line:
            protected = True
        if END in line and protected:
            protected = False

        if "{" in line and not line.strip().startswith("@"):
            ctx = (ctx + " " + line.split("{", 1)[0]).strip()
            out.append(line)
            if "}" in line.split("{", 1)[1]:
                ctx = ""
            continue
        if line.strip() == "}" or (line.strip().endswith("}") and "{" not in line):
            out.append(line)
            ctx = ""
            continue

        if in_zone(line, protected):
            out.append(line)
            continue

        new = transform_line(line, ctx)
        if new is None:
            continue
        out.append(new)

    merged = "\n".join(out)
    repls = [
        ("--bg-page: linear-gradient(180deg, #fafaf9 0%, #f4f4f5 48%, #f1f5f9 100%);", f"--bg-page: {PAGE};"),
        ("--surface: rgba(255, 255, 255, 0.72);", f"--surface: {CARD};"),
        ("--radius-lg: 20px;", "--radius-lg: 16px;"),
        ("--radius-md: 14px;", "--radius-md: 10px;"),
        (
            "--shadow-float: 0 8px 32px rgba(15, 23, 42, 0.08), 0 2px 8px rgba(15, 23, 42, 0.04);",
            f"--shadow-float: {FLAT};",
        ),
        (
            "--shadow-card: 0 1px 0 rgba(15, 23, 42, 0.04), 0 12px 40px rgba(15, 23, 42, 0.06);",
            f"--shadow-card: {FLAT};",
        ),
        ("--space-3: 24px;", "--space-3: 20px;"),
        ("background: #f8faf9 !important;", f"background: {PAGE} !important;"),
        ("background-color: #f8faf9 !important;", f"background-color: {PAGE} !important;"),
        (
            "transition: transform 0.22s var(--ease-out), box-shadow 0.22s var(--ease-out), border-color 0.2s ease;",
            "transition: border-color 0.2s ease;",
        ),
        ("background: rgba(255, 255, 255, 0.78);", f"background: {CARD};"),
        ("background: rgba(255, 255, 255, 0.55);", f"background: {CARD};"),
        (
            "      background:\n        radial-gradient(ellipse 120% 80% at 100% 0%, rgba(13, 148, 136, 0.14) 0%, transparent 55%),\n        radial-gradient(ellipse 90% 70% at 0% 100%, rgba(15, 23, 42, 0.06) 0%, transparent 50%),\n        linear-gradient(180deg, #ffffff 0%, #fafaf9 100%);",
            f"      background: {CARD};",
        ),
        (
            "      background:\n        linear-gradient(135deg, rgba(13, 148, 136, 0.15) 0%, #ffffff 100%) !important;",
            f"      background: {CARD} !important;",
        ),
        (
            "      background: linear-gradient(180deg,\n        rgba(255, 255, 255, 0.95) 0%,\n        rgba(255, 255, 255, 0.86) 100%);",
            f"      background: {CARD};",
        ),
    ]
    for old, new in repls:
        merged = merged.replace(old, new)

    # Flatten common multi-line hero/card backgrounds (non-onboarding)
    merged = re.sub(
        r"background:\s*linear-gradient\([^\)]+\)[^;]*;",
        f"background: {CARD};",
        merged,
    )
    merged = re.sub(
        r"background:\s*radial-gradient\([^\)]+\)[^;]*;",
        f"background: {CARD};",
        merged,
        count=0,
    )
    # Restore onboarding gradients broken by broad regex — re-checkout protected section from git? 
    # Instead: run broad regex only on post section
    p0 = merged.index(START)
    p1 = merged.index(END)
    pre = merged[:p0]
    prot = merged[p0:p1]
    post = merged[p1:]
    for old, new in repls:
        pre = pre.replace(old, new)
        post = post.replace(old, new)
    post = re.sub(
        r"background:\s*linear-gradient\([^\)]+\)[^;]*;",
        f"background: {CARD};",
        post,
    )
    merged = pre + prot + post

    path.write_text(text[:s] + merged + text[e:], encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
