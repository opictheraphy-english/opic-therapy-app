"""
런타임 의존성 확인: google-generativeai 설치 버전 vs PyPI 최신.
"""

from __future__ import annotations

import importlib.metadata
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PYPI_JSON = "https://pypi.org/pypi/google-generativeai/json"


def _version_tuple(version_string: str) -> List[int]:
    """숫자 세그먼트만 모아 비교용 튜플로 (예: 0.8.5 -> [0,8,5])."""
    parts = []
    for chunk in re.split(r"[^\d]+", version_string):
        if chunk.isdigit():
            parts.append(int(chunk))
    return parts


def google_generativeai_version_info(timeout_sec: float = 6.0) -> Dict[str, Any]:
    """
    설치된 google-generativeai 버전과 PyPI 공개 최신 버전을 비교한다.
    네트워크 실패 시 pypi_latest 는 None.
    """
    installed: Optional[str] = None
    try:
        installed = importlib.metadata.version("google-generativeai")
    except importlib.metadata.PackageNotFoundError:
        pass

    pypi_latest: Optional[str] = None
    try:
        import urllib.request

        req = urllib.request.Request(
            PYPI_JSON,
            headers={"User-Agent": "opic-therapy-app/deps_check"},
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.load(resp)
            pypi_latest = (data.get("info") or {}).get("version")
    except Exception as e:
        logger.debug("PyPI version check skipped: %s", e)

    is_latest_or_newer: Optional[bool] = None
    if installed and pypi_latest:
        try:
            a, b = _version_tuple(installed), _version_tuple(pypi_latest)
            # 짧은 쪽을 0으로 패딩
            n = max(len(a), len(b))
            a += [0] * (n - len(a))
            b += [0] * (n - len(b))
            is_latest_or_newer = a >= b
        except Exception:
            is_latest_or_newer = installed == pypi_latest

    return {
        "installed": installed,
        "pypi_latest": pypi_latest,
        "is_latest_or_newer": is_latest_or_newer,
    }
