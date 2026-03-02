import yfinance as yf
import pandas as pd
import numpy as np
import os
import json

class ValuationAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker
        try:
            # 🚨 가짜 신분증 빼고 순정으로 롤백!
            self.stock = yf.Ticker(ticker)
        except Exception:
            self.stock = None
        self.info = {}
        
        # [New] 동적 벤치마크 로드
        self.benchmarks = self.load_sector_benchmarks()

    def load_sector_benchmarks(self):
        """저장된 섹터별 벤치마크(JSON)를 로드하거나 기본값을 사용"""
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
            except:
                pass
        return defaults
        
    def get_financial_data(self):
        try:
            if not self.stock: return None
            self.info = self.stock.info
            
            current_price = self.info.get("currentPrice", self.info.get("regularMarketPreviousClose", 0))
            per = self.info.get("trailingPE", 0)
            fwd_per = self.info.get("forwardPE", 0)
            eps = self.info.get("trailingEps", 0)         
            book_value = self.info.get("bookValue", 0)    
            
            earnings_growth = self.info.get("earningsGrowth", 0) 
            peg = self.info.get("pegRatio", None)
            peg_source = "API"
            
            if (peg is None or peg <= 0) and fwd_per > 0 and earnings_growth > 0:
                try:
                    peg = round(fwd_per / (earnings_growth * 100), 2)
                    peg_source = "Manual Calc"
                except: peg = 0
            if peg is None: peg = 0

            debt_to_equity = self.info.get("debtToEquity", 0)
            free_cashflow = self.info.get("freeCashflow", 0)
            operating_margins = self.info.get("operatingMargins", 0)
            pbr = self.info.get("priceToBook", 0)
            roe = self.info.get("returnOnEquity", 0)

            formulas = {
                "PER (주가수익비율)": f"주가(${current_price}) ÷ EPS(${eps}) = {per:.2f}배",
                "PEG (주가수익성장비율)": f"PER({per:.2f}) ÷ 이익성장률({(earnings_growth*100):.1f}%) = {peg}배",
                "PBR (주가순자산비율)": f"주가(${current_price}) ÷ BPS(${book_value}) = {pbr:.2f}배",
                "ROE (자기자본이익률)": f"최근 12개월 순이익 기준 = {(roe*100):.1f}%",
                "부채비율 (Debt/Equity)": f"총부채 ÷ 자본총계 = {debt_to_equity:.1f}%",
                "영업이익률 (Op. Margin)": f"영업이익 ÷ 총매출 = {(operating_margins*100):.1f}%"
            }

            data = {
                "name": self.info.get("shortName", self.ticker),
                "sector": self.info.get("sector", "Default"),
                "current_price": current_price,
                "target_price": self.info.get("targetMeanPrice", 0),
                "market_cap": self.info.get("marketCap", 0),
                "per": per,
                "fwd_per": fwd_per,
                "eps": eps, 
                "pbr": pbr,
                "roe": roe,
                "peg": peg,
                "peg_source": peg_source,
                "revenue_growth": self.info.get("revenueGrowth", 0),
                "earnings_growth": earnings_growth,
                "ps_ratio": self.info.get("priceToSalesTrailing12Months", 0),
                "ev_ebitda": self.info.get("enterpriseToEbitda", 0),
                "52w_high": self.info.get("fiftyTwoWeekHigh", 0),
                "52w_low": self.info.get("fiftyTwoWeekLow", 0),
                "debt_to_equity": debt_to_equity,
                "free_cashflow": free_cashflow,
                "op_margin": operating_margins,
                "formulas": formulas 
            }
            return data
        except Exception:
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
                reasons.append(f"💎 초저평가 성장주 (PEG {peg})")
            elif peg < 1.2:
                score += 10
                reasons.append(f"✅ 합리적 가격 (PEG {peg})")
            elif peg > 2.5:
                score -= 10
                reasons.append(f"⚠️ 고평가 구간 (PEG {peg})")

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
            reasons.append(f"💸 부채 리스크 높음 ({de_ratio}%)")
        
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