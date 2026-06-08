"""Scripts tab — Smart Store purchase link."""

from __future__ import annotations

import html

import streamlit as st

from config.store_links import smart_store_url


def render_scripts() -> None:
    store_url = smart_store_url()

    st.markdown('<div class="scripts-store-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="glass-card-quiet">
          <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#64748b;">
            Scripts
          </div>
          <div class="ds-h2" style="margin-top:8px;">처방 스크립트</div>
          <p class="ds-muted" style="margin-bottom:0;">
            등급별 OPIc 처방 스크립트는 네이버 스마트스토어에서 구매할 수 있어요.
            아래 버튼을 누르면 브라우저 새 탭에서 스토어가 열립니다.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    if store_url:
        safe_url = html.escape(store_url, quote=True)
        st.markdown(
            f'<a class="scripts-store-cta" href="{safe_url}" target="_blank" '
            f'rel="noopener noreferrer" referrerpolicy="no-referrer-when-downgrade">'
            "스마트스토어에서 구매하기</a>",
            unsafe_allow_html=True,
        )
        st.caption(
            "로그인 없이 상품을 둘러볼 수 있어요. 결제할 때만 네이버 로그인이 필요할 수 있습니다."
        )
    else:
        st.warning(
            "스마트스토어 링크가 아직 설정되지 않았어요. "
            "SMART_STORE_URL 환경변수에 스토어 주소를 넣어 주세요."
        )
