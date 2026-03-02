import pandas as pd
import os
import yfinance as yf
import requests
import random
import streamlit as st  # 캐싱을 위해 추가
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# 🛡️ 야후 차단 방지용 세션 로직
# ==========================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def get_yf_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[403, 429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session

IS_CLOUD = "STREAMLIT_RUNTIME" in os.environ

# ==========================================
# ⚡ [핵심] 실시간 데이터 패칭 & 캐싱 함수
# ==========================================
# 클래스 외부에 두어야 Streamlit 인스턴스 재생성 시에도 캐시가 완벽하게 유지됩니다.
@st.cache_data(ttl=3600)  # 1시간 동안 데이터를 메모리에 박아두고 재사용합니다.
def fetch_macro_api_data():
    symbols = {
        'VIX': '^VIX',
        'US10Y': '^TNX',
        'DXY': 'DX-Y.NYB',
        'SP500': '^GSPC'
    }
    
    data = {}
    session = get_yf_session()
    
    try:
        for key, sym in symbols.items():
            # 클라우드면 세션 사용, 로컬이면 순정 사용
            t = yf.Ticker(sym, session=session) if IS_CLOUD else yf.Ticker(sym)
            hist = t.history(period="5d")
            
            if not hist.empty and len(hist) >= 2:
                val = float(hist['Close'].iloc[-1])
                prev_val = float(hist['Close'].iloc[-2])
                change = ((val - prev_val) / prev_val) * 100 if prev_val != 0 else 0
                
                data[key] = {
                    "value": val,
                    "change": change
                }
            else:
                data[key] = {"value": 0, "change": 0}
        return data if data else None
    except Exception as e:
        print(f"❌ [Macro] 실시간 데이터 호출 실패: {e}")
        return None

# ==========================================

class MacroAnalyzer:
    def __init__(self):
        pass

    def get_macro_data(self):
        """
        캐싱된 외부 함수를 호출하여 데이터를 가져옵니다.
        """
        return fetch_macro_api_data()

    def analyze_market_status(self, data):
        """
        거시경제 데이터를 바탕으로 '시장 신호등' 판정 (원본 로직 유지)
        """
        if not data:
            return {
                "status": "Unknown",
                "risk_level": "알 수 없음",
                "reasons": ["데이터를 가져올 수 없습니다."]
            }

        score = 0
        reasons = []
        
        # 1. VIX (공포 지수) 평가
        vix = data.get('VIX', {}).get('value', 0)
        if vix > 30:
            score -= 2
            reasons.append(f"😱 시장 공포 극에 달함 (VIX {vix:.1f})")
        elif vix > 20:
            score -= 1
            reasons.append(f"⚠️ 변동성 확대 구간 (VIX {vix:.1f})")
        else:
            score += 1
            reasons.append(f"✅ 시장 심리 안정적 (VIX {vix:.1f})")

        # 2. 국채 금리 (10년물) 평가
        us10y = data.get('US10Y', {}).get('value', 0)
        us10y_change = data.get('US10Y', {}).get('change', 0)
        
        if us10y > 4.5:
            if us10y_change > 1.0:
                score -= 1
                reasons.append(f"📉 금리 발작 주의 (10년물 {us10y:.2f}% 급등)")
            else:
                reasons.append(f"⚠️ 고금리 부담 지속 (10년물 {us10y:.2f}%)")
        elif us10y < 3.5:
            score += 1
            reasons.append("💰 유동성 환경 양호 (저금리)")

        # 3. 달러 인덱스 (강달러 여부)
        dxy = data.get('DXY', {}).get('value', 0)
        if dxy > 105:
            score -= 1
            reasons.append(f"💵 강달러로 인한 실적 부담 (DXY {dxy:.1f})")
        elif dxy < 100:
            reasons.append("✅ 달러 약세 (위험자산 선호)")
        
        # 종합 판정 (신호등)
        if score >= 1:
            status = "🟢 상승장 (Bullish)"
            risk_level = "낮음"
        elif score == 0:
            status = "🟡 중립/혼조세 (Neutral)"
            risk_level = "보통"
        else:
            status = "🔴 하락장/위험 (Bearish)"
            risk_level = "높음"
            
        return {
            "status": status,
            "risk_level": risk_level,
            "reasons": reasons,
            "indicators": data
        }

if __name__ == "__main__":
    macro = MacroAnalyzer()
    raw_data = macro.get_macro_data()
    if raw_data:
        res = macro.analyze_market_status(raw_data)
        print(f"상태: {res['status']}")