import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
import requests
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# 🛡️ 야후 차단 방지용 강력한 세션 및 위장 로직
# ==========================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0"
]

def get_yf_session():
    """야후 접속을 위한 신분증 세션 생성"""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[403, 429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session

# 현재 서버가 클라우드 배포 환경인지 확인
IS_CLOUD = "STREAMLIT_RUNTIME" in os.environ
# ==========================================

class ValuationAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker
        try:
            # 🚨 클라우드면 신분증 세션 사용, 로컬이면 순정 yfinance 사용
            if IS_CLOUD:
                self.session = get_yf_session()
                self.stock = yf.Ticker(ticker, session=self.session)
            else:
                self.stock = yf.Ticker(ticker)
        except Exception:
            self.stock = None
            
        self.benchmarks = self.load_sector_benchmarks()

    def load_sector_benchmarks(self):
        """섹터별 벤치마크 로드 (원본 로직 유지)"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "data", "sector_benchmarks.json")
        
        defaults = {
            "Technology": {"per": 35.0, "peg": 1.5, "name": "기술주"},
            "Financial Services": {"per": 14.5, "peg": 1.0, "name": "금융"},
            "Healthcare": {"per": 22.0, "peg": 1.8, "name": "헬스케어"},
            "Consumer Cyclical": {"per": 25.0, "peg": 1.3, "name": "임의소비재"},
            "Energy": {"per": 11.0, "peg": 0.8, "name": "에너지"},
            "Industrials": {"per": 20.0, "peg": 1.4, "name": "산업재"},
            "Default": {"per": 20.0, "peg": 1.5, "name": "시장평균"}
        }

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return defaults
        
    def get_financial_data(self):
        """야후 파이낸스 info 기반 재무 데이터 분석 (복구 버전)"""
        try:
            if not self.stock: return None
            
            # 🚨 야후 info 데이터 호출 (가장 많은 정보를 담고 있음)
            info = self.stock.info
            if not info: return None
            
            # 지표 추출 및 0 처리 방어
            current_price = info.get("currentPrice", info.get("regularMarketPreviousClose", 0))
            per = info.get("trailingPE", 0)
            fwd_per = info.get("forwardPE", 0)
            eps = info.get("trailingEps", 0)
            book_value = info.get("bookValue", 0)
            pbr = info.get("priceToBook", 0)
            roe = info.get("returnOnEquity", 0)
            peg = info.get("pegRatio", 0)
            debt_to_equity = info.get("debtToEquity", 0)
            operating_margins = info.get("operatingMargins", 0)
            
            # [복원] 원종님 핵심 로직 - 계산 근거(Lineage) 생성
            formulas = {
                "PER (주가수익비율)": f"주가(${current_price:.2f}) ÷ EPS(${eps:.2f}) = {per:.2f}배",
                "PEG (주가수익성장비율)": f"야후 제공 (이익성장성 대비 멀티플) = {peg:.2f}배",
                "PBR (주가순자산비율)": f"주가(${current_price:.2f}) ÷ BPS(${book_value:.2f}) = {pbr:.2f}배",
                "ROE (자기자본이익률)": f"최근 12개월(TTM) 기준 = {(roe*100):.1f}%",
                "부채비율 (Debt/Equity)": f"총부채 ÷ 자본총계 = {debt_to_equity:.1f}%",
                "영업이익률 (Op. Margin)": f"영업이익 ÷ 총매출 = {(operating_margins*100):.1f}%"
            }

            data = {
                "name": info.get("shortName", self.ticker),
                "sector": info.get("sector", "Default"),
                "current_price": current_price,
                "target_price": info.get("targetMeanPrice", 0),
                "market_cap": info.get("marketCap", 0),
                "per": per,
                "fwd_per": fwd_per,
                "eps": eps,
                "pbr": pbr,
                "roe": roe,
                "peg": peg,
                "peg_source": "Yahoo Finance Info",
                "revenue_growth": info.get("revenueGrowth", 0),
                "earnings_growth": info.get("earningsGrowth", 0),
                "ps_ratio": info.get("priceToSalesTrailing12Months", 0),
                "ev_ebitda": info.get("enterpriseToEbitda", 0),
                "52w_high": info.get("fiftyTwoWeekHigh", 0),
                "52w_low": info.get("fiftyTwoWeekLow", 0),
                "debt_to_equity": debt_to_equity,
                "free_cashflow": info.get("freeCashflow", 0),
                "op_margin": operating_margins,
                "formulas": formulas 
            }
            return data
        except Exception as e:
            print(f"❌ [Valuation] 야후 데이터 가공 중 에러: {e}")
            return None

    def calculate_valuation_score(self, data):
        """[원본 복원] 점수 계산 및 투자 의견 산출 로직"""
        if not data or data['current_price'] == 0:
            return 0, "데이터 부족", []

        score = 50 
        reasons = []

        # 1. PEG Ratio 평가
        peg = data['peg']
        if peg > 0:
            if peg < 0.8:
                score += 20
                reasons.append(f"💎 초저평가 성장주 (PEG {peg:.2f})")
            elif peg < 1.2:
                score += 10
                reasons.append(f"✅ 합리적 가격 (PEG {peg:.2f})")
            elif peg > 2.5:
                score -= 10
                reasons.append(f"⚠️ 고평가 구간 (PEG {peg:.2f})")

        # 2. ROE 평가
        roe = data['roe']
        if roe > 0.20:
            score += 10
            reasons.append(f"👑 높은 자본효율 (ROE {roe*100:.1f}%)")
        elif roe < 0.05:
            score -= 5

        # 3. 부채비율 및 수익성 평가
        de_ratio = data['debt_to_equity']
        is_financial = "Financial" in data['sector']
        if not is_financial and de_ratio > 200:
            score -= 10
            reasons.append(f"💸 부채 리스크 높음 ({de_ratio:.1f}%)")
        
        opm = data['op_margin']
        if opm > 0.20:
            score += 10
            reasons.append(f"💰 고마진 사업구조 (OPM {opm*100:.1f}%)")

        # 4. 섹터 비교 평가
        sector_key = data.get('sector', 'Default')
        benchmark = self.benchmarks.get(sector_key, self.benchmarks.get('Default'))
        
        my_per = data.get('per', 0)
        avg_per = benchmark.get('per', 20)
        
        if my_per > 0 and avg_per > 0:
            if my_per < avg_per * 0.8:
                score += 10
                reasons.append(f"🏢 업종 평균({avg_per:.1f}) 대비 저렴 (PER {my_per:.1f})")
            elif my_per > avg_per * 1.5:
                score -= 10
                reasons.append(f"⚠️ 업종 평균({avg_per:.1f}) 대비 고평가")

        final_score = max(0, min(100, score))
        
        if final_score >= 80: status = "Strong Buy"
        elif final_score >= 60: status = "Buy"
        elif final_score >= 40: status = "Hold"
        else: status = "Sell"

        return final_score, status, reasons

    def get_sector_comparison(self, data):
        """섹터 벤치마크 데이터 반환"""
        if not data: return None
        sector_key = data.get('sector', 'Default')
        benchmark = self.benchmarks.get(sector_key, self.benchmarks.get('Default'))
        return {
            "sector_name": benchmark.get('name', sector_key),
            "avg_per": benchmark.get('per', 0),
            "avg_peg": benchmark.get('peg', 0)
        }