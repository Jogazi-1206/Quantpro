import streamlit as st
import os
import time
import pandas as pd

# --- [사용자 모듈 로드] ---
from modules.data_loader import DataLoader
from modules.valuation import ValuationAnalyzer
from modules.predictor import StockPredictor
from modules.macro import MacroAnalyzer
from modules.reporter import InvestmentReporter
from modules.database import Database
from modules.screener import HiddenGemsScreener
from modules.auth_ui import render_auth_screen # [New] 로그인 UI 모듈

# --- [UI & 차트 자산 로드] ---
from assets.charts import plot_market_trend, plot_candle_chart
from assets.ui_components import (
    macro_card_html, sector_row_html, stock_list_item_html,
    company_header_html, valuation_detail_html, metric_grid_html,
    ai_prediction_card_html, final_verdict_html, 
    macro_status_html, technical_badge_html
)

# [1] 설정 및 디자인 로더
st.set_page_config(page_title="Quant Pro Terminal", layout="wide", initial_sidebar_state="expanded")

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.error(f"⚠️ '{file_name}' 파일이 없습니다.")

load_css(os.path.join("assets", "style.css"))

st.markdown("""
    <style>
        /* 1. 하얀색 기본 헤더를 투명하게 지워버림 */
        [data-testid="stHeader"] {
            background-color: transparent !important;
        }
        /* 2. 화면 맨 위쪽의 쓸데없는 빈 공간(여백)을 확 줄임 */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# [2] 초기화 (DB 연결 및 세션 상태)
if 'active_tab' not in st.session_state: st.session_state.active_tab = 'Macro'
if 'selected_ticker' not in st.session_state: st.session_state.selected_ticker = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'list'

# --- [Auth] 세션 상태에 유저 정보 초기화 ---
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'username' not in st.session_state: st.session_state.username = None

loader = DataLoader()
db = Database()

# ==========================================
# 🛑 [핵심 문지기] 로그인 안 했으면 로그인 화면만 보여주고 멈춤!
# ==========================================
if not st.session_state.user_id:
    render_auth_screen(db)
    st.stop() # 여기서 멈춰서 밑에 있는 데이터 분석 로직들이 실행 안 되게 막음
# ==========================================


# --- [Dialog] 리포트 팝업 함수 ---
@st.dialog("📄 Goldman Sachs AI Report", width="large")
def show_ai_report_dialog(ticker, info, basic, score, status, v_data, ai_prob):
    
    cache_key = f"ai_report_{ticker}"
    
    if cache_key not in st.session_state:
        st.markdown(f"### Analyzing **{ticker}**...")
        with st.spinner("골드만삭스 AI가 10년 치 데이터를 분석 중입니다..."):
            rep = InvestmentReporter()
            payload = {
                "info": info, 
                "basic": basic, 
                "val": {"score": score, "status": status, "data": v_data}, 
                "ai": {"prob": ai_prob}, 
                "macro": {"indicators": MacroAnalyzer().get_macro_data(), "status": "Unknown"}
            }
            report_text = rep.generate_ai_report(ticker, payload)
            st.session_state[cache_key] = report_text 
    else:
        report_text = st.session_state[cache_key]
        st.toast("저장된 리포트를 불러왔습니다!", icon="⚡")

    st.markdown("---")
    st.markdown(report_text)
    st.markdown("---")
    
    st.info("💡 **Tip: PDF로 소장하고 싶으신가요?**\n\n키보드 단축키 **`Ctrl + P`** (Windows) 또는 **`Cmd + P`** (Mac)를 누른 후, 대상을 **'PDF로 저장'**으로 선택하시면 현재 화면의 다크 테마와 예쁜 폰트 그대로 깔끔하게 저장됩니다!")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 텍스트 리포트 다운로드 (.md)",
            data=report_text,
            file_name=f"QuantPro_{ticker}_Report.md",
            mime="text/markdown",
            use_container_width=True
        )
    with col2:
        if st.button("닫기", use_container_width=True):
            st.rerun()

# [3] 사이드바 네비게이션
with st.sidebar:
    st.markdown("""
        <div style="padding:10px 0 20px 0; display:flex; align-items:center; gap:12px;">
            <div style="width:32px; height:32px; background:#3182F6; border-radius:8px; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold;">Q</div>
            <span style="font-size:1.2rem; font-weight:bold; color:white;">QuantPro</span>
        </div>
    """, unsafe_allow_html=True)
    
    # [New] 로그인한 유저 환영 메시지 및 로그아웃 버튼
    st.markdown(f"<div style='color:#10B981; font-weight:bold; margin-bottom:15px;'>👤 {st.session_state.username}님 접속 중</div>", unsafe_allow_html=True)
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()
        
    st.markdown("---")
    
    if st.button("🌍  Macro Insight"): st.session_state.active_tab = 'Macro'
    if st.button("⭐  My Watchlist"): 
        st.session_state.active_tab = 'Watchlist'
        st.session_state.view_mode = 'list'
    if st.button("🔍  Deep Search"): st.session_state.active_tab = 'Search'
    if st.button("💎  Hidden Gems"): st.session_state.active_tab = 'Gems'
    
    st.markdown("---")
    st.caption("AI Engine Status: ✅ Running")


# [4] 메인 컨텐츠 영역

# --- TAB 1: MACRO INSIGHT ---
if st.session_state.active_tab == 'Macro':
    st.markdown("<h1 style='color:white; margin-bottom:30px;'>Market Overview</h1>", unsafe_allow_html=True)
    
    macro = MacroAnalyzer()
    m_data = macro.get_macro_data()
    
    if m_data:
        res = macro.analyze_market_status(m_data)
        ind = res['indicators']
        
        status_color = "text-green" if "Bullish" in res['status'] else "text-red"
        st.markdown(macro_status_html(res, status_color), unsafe_allow_html=True)
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        vix_val = ind.get('VIX', {}).get('value', 0)
        us10y_val = ind.get('US10Y', {}).get('value', 0)
        dxy_val = ind.get('DXY', {}).get('value', 0)

        with c1: st.markdown(macro_card_html("Market Fear (VIX)", f"{vix_val:.2f}", "Caution" if vix_val > 20 else "Stable", "text-yellow" if vix_val > 20 else "text-green", 65), unsafe_allow_html=True)
        with c2: st.markdown(macro_card_html("US 10Y Yield", f"{us10y_val:.2f}%", "High", "text-red", 85), unsafe_allow_html=True)
        with c3: st.markdown(macro_card_html("Dollar Index", f"{dxy_val:.2f}", "Strong", "text-blue", 70), unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:white; font-size:1.1rem; margin-bottom:10px;'>Global Indices</h3>", unsafe_allow_html=True)
        
        assets = loader.get_dashboard_assets()
        if assets:
            ac1, ac2, ac3, ac4, ac5, ac6 = st.columns(6)
            asset_order = ["Nasdaq", "Dow Jones", "Russell 2000", "Bitcoin", "Gold", "WTI Oil"]
            cols = [ac1, ac2, ac3, ac4, ac5, ac6]
            
            for i, name in enumerate(asset_order):
                if name in assets:
                    data = assets[name]
                    price = data['price']
                    change = data['change']
                    with cols[i]:
                        st.metric(
                            label=name,
                            value=f"{price:,.0f}" if name != "WTI Oil" else f"{price:,.2f}",
                            delta=f"{change:+.2f}%"
                        )
        else:
            st.info("글로벌 자산 데이터를 불러오는 중입니다...")

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        col_chart, col_sector = st.columns([2, 1])
        
        with col_chart:
            snp_data = loader.get_market_index_data() 
            if not snp_data.empty:
                last_p = snp_data.iloc[-1]
                prev_p = snp_data.iloc[-2]
                chg = last_p - prev_p
                pct = (chg / prev_p) * 100
                color = "#F43F5E" if chg >= 0 else "#3182F6"
                arrow = "▲" if chg >= 0 else "▼"
                
                st.markdown(f"""
                <div style="margin-bottom: 10px;">
                    <span style="font-size:1rem; font-weight:bold; color:white;">S&P 500 Trend</span>
                    <div style="display:flex; align-items:end; gap:10px; margin-top:5px;">
                        <span style="font-size:2.2rem; font-weight:900; color:{color}; line-height:1;">{last_p:,.2f}</span>
                        <span style="font-size:1rem; font-weight:bold; color:{color}; margin-bottom:4px;">{arrow} {abs(chg):.2f} ({pct:+.2f}%)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                fig = plot_market_trend(snp_data)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("차트 데이터 로딩 중...")
            
        with col_sector:
            sector_html = "<div class='glass-card' style='height:450px; padding:20px; overflow-y:auto;'>"
            sector_html += "<h3 style='color:white; font-size:1.1rem; margin-bottom:15px;'>Sector Performance</h3>"
            sectors = loader.get_sector_performance()
            if sectors:
                for s in sectors: sector_html += sector_row_html(s['name'], s['change'])
            else: sector_html += "<p style='color:gray;'>데이터 로딩 중...</p>"
            sector_html += "</div>"
            st.markdown(sector_html, unsafe_allow_html=True)

# --- TAB 2: WATCHLIST ---
elif st.session_state.active_tab == 'Watchlist':
    if st.session_state.view_mode == 'details' and st.session_state.selected_ticker:
        t = st.session_state.selected_ticker
        
        col_back, col_title, col_heart = st.columns([1.5, 9, 1.5])
        with col_back:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.view_mode = 'list'
                st.rerun()
                
        with col_title:
             st.markdown(f"<h2 style='margin:0; color:white; padding-top:5px;'>Analysis: {t}</h2>", unsafe_allow_html=True)
        
        with col_heart:
            # [DB 변경 반영] user_id 추가
            is_saved = db.is_in_watchlist(st.session_state.user_id, t)
            btn_label = "❤️" if is_saved else "🤍"
            if st.button(btn_label, key=f"fav_{t}", use_container_width=True):
                # [DB 변경 반영] user_id 추가
                is_added = db.toggle_watchlist(st.session_state.user_id, t)
                if is_added: st.toast(f"{t} 찜 목록에 추가됨!", icon="❤️")
                else: st.toast(f"{t} 찜 목록에서 삭제됨!", icon="🗑️")
                time.sleep(0.5)
                st.rerun()

        st.markdown("---")

        with st.spinner(f"{t} 심층 분석 중..."):
            info = loader.get_realtime_info(t)
            basic = loader.get_company_basic_info(t)
            hist_df = loader.get_historical_prices(t)
            
            val = ValuationAnalyzer(t)
            v_data = val.get_financial_data()
            score, status, reasons = val.calculate_valuation_score(v_data)
            comp = val.get_sector_comparison(v_data)
            
            pred = StockPredictor()
            tech_signals = pred.get_technical_signals(t)
            ai_prob = pred.predict_next_move(t) or 50.0

            final_verdict_score = (score + ai_prob) / 2
            verdict_text = "STRONG BUY" if final_verdict_score > 75 else "BUY" if final_verdict_score > 60 else "HOLD" if final_verdict_score > 40 else "SELL"
            verdict_color = "text-blue" if final_verdict_score > 60 else "text-yellow-500" if final_verdict_score > 40 else "text-red"

            row1_c1, row1_c2 = st.columns([2, 1])
            with row1_c1:
                st.markdown(company_header_html(info, basic), unsafe_allow_html=True)
                if not hist_df.empty:
                    fig = plot_candle_chart(hist_df)
                    st.plotly_chart(fig, use_container_width=True)
                if tech_signals: st.markdown(technical_badge_html(tech_signals), unsafe_allow_html=True)

            with row1_c2:
                st.markdown(final_verdict_html(verdict_text, final_verdict_score, verdict_color), unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
                
                if st.button("✨ Gemini 심층 리포트 생성", key="gen_report_full", use_container_width=True):
                    show_ai_report_dialog(t, info, basic, score, status, v_data, ai_prob)

            st.markdown("<h3 style='color:white; margin-top:30px;'>Fundamental Analysis</h3>", unsafe_allow_html=True)
            metrics = {
                "Revenue": f"${basic.get('total_revenue', 0)/1e9:.1f}B",
                "Op. Margin": f"{basic.get('operating_margins', 0)*100:.1f}%",
                "Market Cap": f"${basic.get('market_cap', 0)/1e9:.1f}B"
            }
            st.markdown(metric_grid_html(metrics), unsafe_allow_html=True)

            with st.expander("🔍 주요 지표 계산 근거 보기 (Data Lineage)"):
                formulas = v_data.get('formulas', {})
                if formulas:
                    for name, formula in formulas.items():
                        st.markdown(f"- **{name}**: `{formula}`")
                else:
                    st.write("계산 근거 데이터를 불러올 수 없습니다.")

            d_c1, d_c2, d_c3 = st.columns(3)
            with d_c1: st.markdown(valuation_detail_html(score, reasons, comp), unsafe_allow_html=True)
            with d_c2: st.markdown(ai_prediction_card_html(ai_prob), unsafe_allow_html=True)
            with d_c3: pass

    else:
        st.markdown("<h1 style='color:white; margin-bottom:30px;'>My Watchlist</h1>", unsafe_allow_html=True)
        
        # [DB 변경 반영] 로그인한 유저의 찜 목록만 가져옴
        watchlist = db.get_watchlist(st.session_state.user_id)
        
        if not watchlist:
            st.info("찜한 종목이 없습니다. Search 탭에서 종목을 검색하고 하트(❤️)를 눌러보세요!")
        
        for ticker in watchlist:
            info = loader.get_realtime_info(ticker)
            if info:
                spark = loader.get_sparkline_data(ticker)
                val = ValuationAnalyzer(ticker)
                score, _, _ = val.calculate_valuation_score(val.get_financial_data())
                
                st.markdown(stock_list_item_html(info, score, 0, spark), unsafe_allow_html=True)
                
                c1, c2 = st.columns([8, 1])
                with c2:
                    if st.button("❌", key=f"del_{ticker}"):
                        # [DB 변경 반영]
                        db.remove_from_watchlist(st.session_state.user_id, ticker)
                        st.rerun()
                
                if st.button(f"👉 {ticker} 상세 분석", key=f"btn_{ticker}", use_container_width=True):
                    st.session_state.selected_ticker = ticker
                    st.session_state.view_mode = 'details'
                    st.rerun()

# --- TAB 3: SEARCH ---
elif st.session_state.active_tab == 'Search':
    st.markdown("<div style='height:15vh'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align:center; color:white; font-size:3rem;'>Deep Search</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#9CA3AF; margin-bottom:30px;'>AI가 10년 치 데이터와 거시경제를 분석합니다.</p>", unsafe_allow_html=True)
        
        ticker_input = st.text_input("Ticker", placeholder="종목코드 입력 (예: PLTR)", label_visibility="collapsed").upper()
        
        if ticker_input:
            st.session_state.selected_ticker = ticker_input
            st.session_state.view_mode = 'details'
            st.session_state.active_tab = 'Watchlist'
            st.rerun()

# --- TAB 4: HIDDEN GEMS ---
elif st.session_state.active_tab == 'Gems':

    st.markdown("<h1 style='color:white; margin-bottom:10px;'>💎 Hidden Gems Screener</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#9CA3AF; margin-bottom:30px;'>AI 모델과 가치평가(Valuation) 알고리즘을 결합하여 시장에 숨겨진 저평가 급등 유망주를 발굴합니다.</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        min_ai_prob = st.slider("최소 AI 상승 확률 (%)", 0, 100, 60, 5, help="단기(5일) 내 급등할 확률의 최소 기준")
    with col2:
        min_val_score = st.slider("최소 펀더멘털 점수 (100점 만점)", 0, 100, 65, 5, help="기업의 재무 건전성 및 저평가 매력도 기준")
    with col3:
        scan_limit = st.selectbox("스캔 대상 종목 수 (속도 조절)", ["Top 100 (약 5초)", "Top 300 (약 15초)", "S&P 500 전체 (약 30초)"])

    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

    if st.button("🚀 AI 스크리너 가동 (Start Scanning)", use_container_width=True):
        limit_map = {"Top 100 (약 5초)": 100, "Top 300 (약 15초)": 300, "S&P 500 전체 (약 30초)": 500}
        limit = limit_map[scan_limit]

        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total, ticker):
            progress_bar.progress((current + 1) / total)
            status_text.text(f"🔍 스캔 중: {ticker} ({current+1}/{total})...")

        screener = HiddenGemsScreener()
        results = screener.run_scan(min_ai_prob, min_val_score, limit, progress_callback=update_progress)
        
        progress_bar.empty()
        status_text.empty()

        if results is None:
            st.error("데이터 폴더가 없습니다. 데이터를 먼저 수집해주세요.")
        elif len(results) == 0:
             st.warning("🥲 조건에 맞는 종목이 없거나 학습 데이터가 부족합니다. 슬라이더를 조절하여 필터 기준을 낮춰보세요.")
        else:
            st.success(f"🎉 총 {len(results)}개의 Hidden Gem을 발굴했습니다!")
            st.balloons() 
            
            for res in results:
                t = res['Ticker']
                with st.container():
                    st.markdown(f"""
                    <div class="glass-card" style="padding: 20px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; border-left: 5px solid #3182F6;">
                        <div>
                            <h3 style="margin:0; color:white; font-size:1.5rem;">{t} <span style="font-size:1rem; color:#9CA3AF; font-weight:normal;">{res['Name']}</span></h3>
                            <p style="margin:5px 0 0 0; color:#D1D5DB; font-size:0.9rem;">Sector: {res['Sector']} | Current Price: ${res['Price']}</p>
                        </div>
                        <div style="display: flex; gap: 30px; text-align: right;">
                            <div>
                                <p style="margin:0; color:#9CA3AF; font-size:0.8rem;">Valuation Score</p>
                                <h4 style="margin:0; color:#10B981; font-size:1.3rem;">{res['Val Score']} / 100</h4>
                            </div>
                            <div>
                                <p style="margin:0; color:#9CA3AF; font-size:0.8rem;">AI Momentum</p>
                                <h4 style="margin:0; color:#F43F5E; font-size:1.3rem;">{res['AI Prob']:.1f}%</h4>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"👉 {t} 심층 분석으로 이동", key=f"gem_btn_{t}", use_container_width=True):
                        st.session_state.selected_ticker = t
                        st.session_state.view_mode = 'details'
                        st.session_state.active_tab = 'Watchlist'
                        st.rerun()
                    st.markdown("<div style='margin-bottom:30px;'></div>", unsafe_allow_html=True)