"""Curriculum + player layout — learning dashboard style."""

from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components


def render_lectures() -> None:
    st.markdown(
        """
        <div class="glass-card-quiet">
          <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#64748b;">Curriculum</div>
          <div class="ds-h2" style="margin-top:8px;">오픽 치료사 커리큘럼</div>
          <p class="ds-muted">플레이리스트 순서대로 수강하면 학습 효율이 가장 높습니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    playlist_a = "https://www.youtube.com/playlist?list=PLiltzGCdKy3a_285OwiM1g6ZWH-rVMIU8"
    playlist_b = "https://www.youtube.com/playlist?list=PLiltzGCdKy3ZwXzkUcXxkTj4cSA82su6-"
    playlist_a_id = "PLiltzGCdKy3a_285OwiM1g6ZWH-rVMIU8"
    playlist_b_id = "PLiltzGCdKy3ZwXzkUcXxkTj4cSA82su6-"

    tab_expr, tab_im, tab_c, tab_d, tab_e = st.tabs(
        ["표현 강의", "IM2–IH 강의", "추가 C", "추가 D", "추가 E"]
    )

    expr_titles = [
        "오픽 치료의 시작",
        "6글자로 끝내는 자기소개",
        "장소 묘사 핵심 프레임",
        "인물 묘사 자연스럽게 확장하기",
        "취미/여가 답변의 밀도 올리기",
        "루틴 질문 고득점 구조",
        "과거 경험 스토리텔링 1",
        "과거 경험 스토리텔링 2",
        "비교 질문 정복 루틴",
        "롤플레이 생존 표현",
        "돌발 질문 완급 조절",
        "시제 전환 실수 방지",
        "연결어 최소로 고급스럽게 말하기",
        "IM2에서 IM3로 가는 표현 차이",
        "IH 표현 밀도 트레이닝",
        "답변 길이 확장 리허설",
        "암기톤 제거 실전법",
        "피드백 기반 자가 진단",
        "시험 당일 운영 전략",
        "최종 모의 답변 점검",
    ]
    im_titles = [
        "IM2-IH 진단 기준 이해",
        "IH 채점관 시점으로 답변 만들기",
        "스토리형 답변 고급화",
        "고난도 루틴 질문 대응",
        "경험 질문 디테일 강화",
        "돌발 질문 즉답 트레이닝",
        "롤플레이 고득점 스크립트",
        "시제 일관성 실전 교정",
        "논리 전개 속도 조절",
        "어휘 정확도 업그레이드",
        "문장 길이와 정보 밀도 균형",
        "리스크 문장 회피 전략",
        "시간 압박 대비 말하기",
        "실전형 리커버리 표현",
        "IH 안정권 답변 패턴",
        "AL 도전형 답변 패턴",
        "자주 무너지는 구간 분석",
        "문항별 최적 길이 설계",
        "실전 시뮬레이션 1세트",
        "실전 시뮬레이션 2세트",
    ]

    with tab_expr:
        _render_playlist_tab("오픽 표현 강의", playlist_a, playlist_a_id, expr_titles)

    with tab_im:
        _render_playlist_tab("오픽 IM2–IH 강의", playlist_b, playlist_b_id, im_titles)

    def _render_coming_soon() -> None:
        st.markdown(
            '<div class="glass-card-quiet"><p class="ds-h2" style="margin:0;">준비 중</p>'
            '<p class="ds-muted">심화 진단 강의가 순차적으로 공개됩니다.</p></div>',
            unsafe_allow_html=True,
        )

    with tab_c:
        _render_coming_soon()
        st.link_button("YouTube에서 열기", playlist_a, use_container_width=True)
    with tab_d:
        _render_coming_soon()
        st.link_button("YouTube에서 열기", playlist_b, use_container_width=True)
    with tab_e:
        _render_coming_soon()
        st.link_button("YouTube에서 열기", playlist_b, use_container_width=True)


def _render_playlist_tab(title: str, playlist_url: str, playlist_id: str, lecture_titles: list) -> None:
    st.link_button("플레이리스트 전체 재생", playlist_url, use_container_width=True)

    left, right = st.columns([1, 1.15], vertical_alignment="top")

    with left:
        st.markdown(
            '<div class="lecture-layout"><div class="lecture-curriculum-head">전체 목차 · 1–20</div></div>',
            unsafe_allow_html=True,
        )
        rows_html = []
        for idx, lecture_title in enumerate(lecture_titles, start=1):
            safe_title = html.escape(lecture_title)
            rows_html.append(
                f'<div class="lecture-row"><span class="lecture-idx">{idx:02d}</span>'
                f'<span class="lecture-title">{safe_title}</span></div>'
            )
        st.markdown(
            f'<div class="lecture-scroll">{"".join(rows_html)}</div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(f'<div class="ds-h2">{html.escape(title)}</div>', unsafe_allow_html=True)
        embed_url = (
            f"https://www.youtube.com/embed/videoseries?list={playlist_id}"
            f"&rel=0&showsearch=0&modestbranding=1&playsinline=1"
        )
        components.html(
            f"""
            <iframe
              width="100%"
              height="420"
              src="{embed_url}"
              title="YouTube playlist"
              style="border:none;border-radius:14px;overflow:hidden;"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowfullscreen>
            </iframe>
            """,
            height=440,
        )
        st.markdown(
            '<p class="lecture-aside">플레이어 메뉴에서 목록을 열면 세부 영상을 선택할 수 있습니다.</p>',
            unsafe_allow_html=True,
        )

    st.link_button("YouTube에서 목록 보기", playlist_url, use_container_width=True)
