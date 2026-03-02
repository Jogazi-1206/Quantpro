import pandas as pd
import numpy as np
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
BASE_URL = "https://financialmodelingprep.com/api/v3"

def fetch_fmp(endpoint):
    if not FMP_API_KEY: return None
    url = f"{BASE_URL}/{endpoint}?apikey={FMP_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json()
    except:
        return None

class ValuationAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker
        self.benchmarks = self.load_sector_benchmarks()

    def load_sector_benchmarks(self):
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
        try:
            # FMP API의 핵심 재무 지표 엔드포인트 3개 호출 (초고속 병렬 호출도 가능하지만 일단 순차적 안정성 확보)
            quote = fetch_fmp(f"quote/{self.ticker}")
            metrics = fetch_fmp(f"key-metrics-ttm/{self.ticker}")
            ratios = fetch_fmp(f"ratios-ttm/{self.ticker}")
            profile = fetch_fmp(f"profile/{self.ticker}")

            if not quote or len(quote) == 0: return None
            
            q_data = quote[0]
            m_data = metrics[0] if metrics else {}
            r_data = ratios[0] if ratios else {}
            p_data = profile[0] if profile else {}

            # 지표 추출 및 0 처리 방어
            current_price = q_data.get("price", 0)
            eps = q_data.get("eps", 0)
            per = q_data.get("pe", 0)
            if per == 0 and eps > 0: per = current_price / eps
            
            pbr = m_data.get("pbRatioTTM", 0)
            roe = m_data.get("roeTTM", 0)
            peg = r_data.get("pegRatioTTM", 0)
            debt_to_equity = m_data.get("debtToEquityTTM", 0) * 100 # %로 변환
            operating_margins = r_data.get("operatingProfitMarginTTM", 0)
            free_cashflow = m_data.get("freeCashFlowPerShareTTM", 0) * p_data.get("mktCap", 1) # 근사치

            book_value = current_price / pbr if pbr > 0 else 0
            
            formulas = {
                "PER (주가수익비율)": f"주가(${current_price:.2f}) ÷ EPS(${eps:.2f}) = {per:.2f}배",
                "PEG (주가수익성장비율)": f"FMP 공식 API TTM(Trailing 12 Months) 산출 = {peg:.2f}배",
                "PBR (주가순자산비율)": f"주가(${current_price:.2f}) ÷ BPS(${book_value:.2f}) = {pbr:.2f}배",
                "ROE (자기자본이익률)": f"최근 12개월 순이익 기준 = {(roe*100):.1f}%",
                "부채비율 (Debt/Equity)": f"총부채 ÷ 자본총계 = {debt_to_equity:.1f}%",
                "영업이익률 (Op. Margin)": f"영업이익 ÷ 총매출 = {(operating_margins*100):.1f}%"
            }

            data = {
                "name": q_data.get("name", self.ticker),
                "sector": p_data.get("sector", "Default"),
                "current_price": current_price,
                "target_price": q_data.get("priceAvg200", 0), # 200일선 대체
                "market_cap": q_data.get("marketCap", 0),
                "per": per,
                "fwd_per": per, # 무료 티어 방어
                "eps": eps,
                "pbr": pbr,
                "roe": roe,
                "peg": peg,
                "peg_source": "FMP API",
                "revenue_growth": 0,
                "earnings_growth": 0,
                "ps_ratio": m_data.get("ptbRatioTTM", 0),
                "ev_ebitda": m_data.get("enterpriseValueOverEBITDATTM", 0),
                "52w_high": q_data.get("yearHigh", 0),
                "52w_low": q_data.get("yearLow", 0),
                "debt_to_equity": debt_to_equity,
                "free_cashflow": free_cashflow,
                "op_margin": operating_margins,
                "formulas": formulas 
            }
            return data
        except Exception as e:
            print(f"Valuation API 에러: {e}")
            return None

    def calculate_valuation_score(self, data):
        if not data or data['current_price'] == 0:
            return 0, "데이터 부족", []

        score = 50 
        reasons = []

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

        roe = data['roe']
        if roe > 0.20:
            score += 10
            reasons.append(f"👑 높은 자본효율 (ROE {roe*100:.1f}%)")
        elif roe < 0.05:
            score -= 5

        de_ratio = data['debt_to_equity']
        is_financial = "Financial" in data['sector']
        if not is_financial and de_ratio > 200:
            score -= 10
            reasons.append(f"💸 부채 리스크 높음 ({de_ratio:.1f}%)")
        
        opm = data['op_margin']
        if opm > 0.20:
            score += 10
            reasons.append(f"💰 고마진 사업구조 (OPM {opm*100:.1f}%)")

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
        if not data: return None
        sector_key = data.get('sector', 'Default')
        benchmark = self.benchmarks.get(sector_key, self.benchmarks.get('Default'))
        return {
            "sector_name": benchmark.get('name', sector_key),
            "avg_per": benchmark.get('per', 0),
            "avg_peg": benchmark.get('peg', 0)
        }