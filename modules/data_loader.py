import yfinance as yf
import pandas as pd
import os
import ssl
import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta

# ==========================================
# 🛡️ 야후 차단 우회용 강력한 신분증 & 재시도 로직
# ==========================================
yf_session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[403, 404, 429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
yf_session.mount("http://", adapter)
yf_session.mount("https://", adapter)
yf_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
})

# ☁️ 현재 코드가 Streamlit Cloud(배포 서버)에서 도는지 확인하는 변수
IS_CLOUD = "STREAMLIT_RUNTIME" in os.environ
# ==========================================

# ==========================================
# 💡 [New] 야후 차단 방지용 초고속 캐싱 함수 (10분 유지)
# ==========================================
@st.cache_data(ttl=600) 
def fetch_global_assets_cached():
    assets_map = {
        "Nasdaq": "^IXIC",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
        "Bitcoin": "BTC-USD",
        "Gold": "GC=F",
        "WTI Oil": "CL=F"
    }
    results = {}
    for name, ticker in assets_map.items():
        try:
            # 클라우드면 신분증 제시, 로컬이면 순정 사용!
            if IS_CLOUD:
                t = yf.Ticker(ticker, session=yf_session)
            else:
                t = yf.Ticker(ticker)
                
            hist = t.history(period="5d")
            if len(hist) >= 2:
                curr = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                pct = ((curr - prev) / prev) * 100
                results[name] = {'price': curr, 'change': pct}
        except Exception:
            continue # 에러 나면 앱 멈추지 말고 그냥 패스!
            
    return results if results else None
# ==========================================

class DataLoader:
    def __init__(self):
        # SSL 인증 오류 방지
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context

        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data", "daily_price")
        
        # 데이터 저장소 생성
        os.makedirs(self.data_dir, exist_ok=True)

    def _validate_data(self, df):
        """
        [내부 함수] 데이터가 정상인지 검증합니다.
        1. 비어있는지 확인
        2. 필수 컬럼('Close')이 있는지 확인
        """
        if df.empty:
            return False
        
        # 컬럼명 대소문자 문제 방지 (첫 글자 대문자로 통일)
        df.columns = [str(c).capitalize() for c in df.columns]
        
        # 'Adj Close'가 있으면 'Close'로 우선 사용
        if 'Adj close' in df.columns:
            df['Close'] = df['Adj close']
            
        if 'Close' not in df.columns:
            return False
            
        # 모든 데이터가 NaN인 경우도 불량
        if df['Close'].isnull().all():
            return False
            
        return True

    def get_sp500_tickers(self):
        """위키피디아에서 S&P 500 종목 리스트 크롤링"""
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            tables = pd.read_html(response.text)
            df = tables[0]
            tickers = df['Symbol'].tolist()
            tickers = [t.replace('.', '-') for t in tickers]
            return tickers
        except Exception as e:
            print(f"⚠️ S&P 500 리스트 로드 실패: {e}")
            return ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO"]

    def get_historical_prices(self, ticker, period="10y"):
        """
        [핵심 수정] 데이터 로드 및 '자가 치유(Self-Healing)' 로직
        """
        file_path = os.path.join(self.data_dir, f"{ticker}.parquet")
        
        # 1. 로컬 파일 확인
        if os.path.exists(file_path):
            try:
                df = pd.read_parquet(file_path)
                
                # [검증] 파일이 있지만 내용이 쓰레기라면? -> 삭제!
                if not self._validate_data(df):
                    print(f"⚠️ 손상된 파일 발견 및 삭제: {ticker}")
                    os.remove(file_path) # 파일 삭제
                else:
                    # 정상 파일이면 날짜 확인 (최신화)
                    last_date = df.index[-1].date()
                    if last_date >= (datetime.now() - timedelta(days=3)).date():
                        return df
            except Exception:
                # 읽기 에러나면 그냥 삭제
                if os.path.exists(file_path): os.remove(file_path)

        # 2. 웹 다운로드 (파일이 없거나 삭제된 경우 실행됨)
        try:
            if IS_CLOUD:
                stock = yf.Ticker(ticker, session=yf_session)
            else:
                stock = yf.Ticker(ticker)
                
            df = stock.history(period=period)
            
            # [검증] 다운로드 받은 데이터도 검증
            if self._validate_data(df):
                # Timezone 제거 (Parquet 호환성)
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                
                # 저장
                df.to_parquet(file_path)
                return df
            else:
                # 다운로드 했는데도 이상하면 빈 데이터프레임 반환
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 데이터 다운로드 실패 ({ticker}): {e}")
            return pd.DataFrame()

    def get_realtime_info(self, ticker):
        """실시간 정보"""
        try:
            if IS_CLOUD:
                stock = yf.Ticker(ticker, session=yf_session)
            else:
                stock = yf.Ticker(ticker)
                
            # fast_info가 가끔 실패하면 info로 대체 시도
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
        """기업 개요"""
        try:
            if IS_CLOUD:
                stock = yf.Ticker(ticker, session=yf_session)
            else:
                stock = yf.Ticker(ticker)
                
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
        try:
            if IS_CLOUD:
                stock = yf.Ticker(ticker, session=yf_session)
            else:
                stock = yf.Ticker(ticker)
                
            hist = stock.history(period=period)
            if hist.empty: return []
            return hist['Close'].tolist()
        except:
            return []

    def get_market_index_data(self, period="2y"):
        try:
            if IS_CLOUD:
                index = yf.Ticker("^GSPC", session=yf_session)
            else:
                index = yf.Ticker("^GSPC")
                
            hist = index.history(period=period)
            if hist.empty: return pd.Series()
            return hist['Close']
        except:
            return pd.Series()

    def get_sector_performance(self):
        """섹터 ETF 현황 (11개)"""
        sectors = {
            "Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF", 
            "Energy": "XLE", "Discretionary": "XLY", "Staples": "XLP",       
            "Industrials": "XLI", "Utilities": "XLU", "Materials": "XLB", 
            "Real Estate": "XLRE", "Communication": "XLC"
        }
        data = []
        try:
            for name, ticker in sectors.items():
                if IS_CLOUD:
                    stock = yf.Ticker(ticker, session=yf_session)
                else:
                    stock = yf.Ticker(ticker)
                    
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