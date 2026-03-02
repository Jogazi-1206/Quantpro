import yfinance as yf
import pandas as pd
import os
import ssl
import streamlit as st
import requests
import random
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# 🛡️ 야후 차단 방지용 강력한 세션 및 위장 로직
# ==========================================
# 여러 개의 브라우저 신분증을 준비해서 야후의 감시를 피합니다.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0"
]

def get_yf_session():
    """야후 접속을 위한 신분증 세션 생성"""
    session = requests.Session()
    # 통신 실패 시 최대 3번까지 재시도하는 로직 추가
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[403, 429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    # 랜덤으로 브라우저 신분증 선택
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session

# 현재 서버가 클라우드 배포 환경인지 확인
IS_CLOUD = "STREAMLIT_RUNTIME" in os.environ
# ==========================================

@st.cache_data(ttl=600) 
def fetch_global_assets_cached():
    """[복구] 글로벌 지수 및 자산 실시간 시세 (야후 버전)"""
    assets_map = {
        "Nasdaq": "^IXIC",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
        "Bitcoin": "BTC-USD",
        "Gold": "GC=F",
        "WTI Oil": "CL=F"
    }
    results = {}
    session = get_yf_session()
    
    for name, ticker in assets_map.items():
        try:
            # 클라우드 배포 시에만 세션(신분증)을 사용하고 로컬은 순정 사용
            t = yf.Ticker(ticker, session=session) if IS_CLOUD else yf.Ticker(ticker)
            hist = t.history(period="5d")
            if not hist.empty and len(hist) >= 2:
                curr = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                pct = ((curr - prev) / prev) * 100
                results[name] = {'price': curr, 'change': pct}
        except Exception:
            continue 
            
    return results if results else None

class DataLoader:
    def __init__(self):
        # SSL 인증 오류 방지 (원종님 원본 로직)
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context

        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data", "daily_price")
        
        os.makedirs(self.data_dir, exist_ok=True)

    def _validate_data(self, df):
        """[원본 로직 100%] 데이터 정상 여부 검증"""
        if df is None or df.empty:
            return False
        df.columns = [str(c).capitalize() for c in df.columns]
        if 'Adj close' in df.columns:
            df['Close'] = df['Adj close']
        if 'Close' not in df.columns:
            return False
        if df['Close'].isnull().all():
            return False
        return True

    def get_sp500_tickers(self):
        """[복구] 위키피디아에서 S&P 500 종목 리스트 획득"""
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = requests.get(url, headers=headers, timeout=10)
            tables = pd.read_html(response.text)
            df = tables[0]
            tickers = df['Symbol'].tolist()
            return [t.replace('.', '-') for t in tickers]
        except Exception as e:
            print(f"⚠️ S&P 500 리스트 로드 실패: {e}")
            return ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO"]

    def get_historical_prices(self, ticker, period="10y"):
        """[원본 복원] 자가 치유(Self-Healing) 로직이 포함된 야후 데이터 로더"""
        file_path = os.path.join(self.data_dir, f"{ticker}.parquet")
        
        # 1. 로컬 파일 확인 (자가 치유)
        if os.path.exists(file_path):
            try:
                df = pd.read_parquet(file_path)
                if not self._validate_data(df):
                    os.remove(file_path)
                else:
                    last_date = df.index[-1].date()
                    if last_date >= (datetime.now() - timedelta(days=3)).date():
                        return df
            except Exception:
                if os.path.exists(file_path): os.remove(file_path)

        # 2. 야후 파이낸스 다운로드
        try:
            session = get_yf_session()
            stock = yf.Ticker(ticker, session=session) if IS_CLOUD else yf.Ticker(ticker)
            df = stock.history(period=period)
            
            if self._validate_data(df):
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                df.to_parquet(file_path)
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ {ticker} 데이터 다운로드 실패: {e}")
            return pd.DataFrame()

    def get_realtime_info(self, ticker):
        """[복구] 야후 기반 실시간 정보 획득"""
        try:
            session = get_yf_session()
            stock = yf.Ticker(ticker, session=session) if IS_CLOUD else yf.Ticker(ticker)
            
            # 가벼운 fast_info 우선 시도
            try:
                current = stock.fast_info.last_price
                prev = stock.fast_info.previous_close
            except:
                info = stock.info
                current = info.get('currentPrice') or info.get('regularMarketPrice')
                prev = info.get('previousClose') or info.get('regularMarketPreviousClose')

            if current is None: return None
            
            try: name = stock.info.get('longName', ticker)
            except: name = ticker

            change_pct = ((current - prev) / prev) * 100 if prev else 0

            return {
                "name": name,
                "ticker": ticker,
                "current_price": round(current, 2),
                "change_percent": round(change_pct, 2)
            }
        except:
            return None

    def get_company_basic_info(self, ticker):
        """[복구] 기업 개요 (야후 버전)"""
        try:
            session = get_yf_session()
            stock = yf.Ticker(ticker, session=session) if IS_CLOUD else yf.Ticker(ticker)
            info = stock.info
            return {
                "summary": info.get("longBusinessSummary", "정보 없음"),
                "sector": info.get("sector", "N/A"),
                "market_cap": info.get("marketCap", 0),
                "total_revenue": info.get("totalRevenue", 0),
                "operating_margins": info.get("operatingMargins", 0)
            }
        except:
            return {}

    def get_sparkline_data(self, ticker, period="1mo"):
        """[복구] 스파크라인 데이터"""
        try:
            session = get_yf_session()
            stock = yf.Ticker(ticker, session=session) if IS_CLOUD else yf.Ticker(ticker)
            hist = stock.history(period=period)
            return hist['Close'].tolist() if not hist.empty else []
        except:
            return []

    def get_market_index_data(self, period="2y"):
        """[복구] S&P 500 지수 데이터"""
        try:
            session = get_yf_session()
            index = yf.Ticker("^GSPC", session=session) if IS_CLOUD else yf.Ticker("^GSPC")
            hist = index.history(period=period)
            return hist['Close'] if not hist.empty else pd.Series()
        except:
            return pd.Series()

    def get_sector_performance(self):
        """[복구] 야후 ETF 기반 섹터 성과"""
        sectors = {
            "Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF", 
            "Energy": "XLE", "Discretionary": "XLY", "Staples": "XLP",       
            "Industrials": "XLI", "Utilities": "XLU", "Materials": "XLB", 
            "Real Estate": "XLRE", "Communication": "XLC"
        }
        data = []
        session = get_yf_session()
        for name, ticker in sectors.items():
            try:
                stock = yf.Ticker(ticker, session=session) if IS_CLOUD else yf.Ticker(ticker)
                curr = stock.fast_info.last_price
                prev = stock.fast_info.previous_close
                if curr and prev:
                    change = ((curr - prev) / prev) * 100
                    data.append({"name": name, "change": change})
            except: pass
        data.sort(key=lambda x: x['change'], reverse=True)
        return data

    def get_dashboard_assets(self):
        return fetch_global_assets_cached()