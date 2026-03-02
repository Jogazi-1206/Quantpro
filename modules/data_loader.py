import pandas as pd
import os
import ssl
import streamlit as st
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
BASE_URL = "https://financialmodelingprep.com/api/v3"

def fetch_fmp(endpoint, **kwargs):
    """FMP API 공통 호출 함수"""
    if not FMP_API_KEY:
        return None
        
    url = f"{BASE_URL}/{endpoint}"
    params = {"apikey": FMP_API_KEY}
    params.update(kwargs)
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"⚠️ FMP API 에러 ({endpoint}): {e}")
        return None

# ==========================================
# 💡 [New] FMP 기반 글로벌 지수 캐싱 함수 (10분 유지)
# ==========================================
@st.cache_data(ttl=600) 
def fetch_global_assets_cached():
    # 지수 및 주요 자산 (FMP 심볼 형식)
    tickers = "^IXIC,^DJI,^RUT,BTCUSD,GCUSD,CLUSD" 
    data = fetch_fmp(f"quote/{tickers}")
    if not data: return None

    name_map = {
        "^IXIC": "Nasdaq", "^DJI": "Dow Jones", "^RUT": "Russell 2000",
        "BTCUSD": "Bitcoin", "GCUSD": "Gold", "CLUSD": "WTI Oil"
    }
    
    results = {}
    for item in data:
        symbol = item.get("symbol")
        if symbol in name_map:
            results[name_map[symbol]] = {
                'price': item.get("price", 0),
                'change': item.get("changesPercentage", 0)
            }
    return results
# ==========================================

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
        
        # 데이터 저장소 생성
        os.makedirs(self.data_dir, exist_ok=True)

    def _validate_data(self, df):
        """
        [내부 함수] 데이터가 정상인지 검증합니다. (원종님 원본 로직 100% 복원)
        1. 비어있는지 확인
        2. 필수 컬럼('Close')이 있는지 확인
        """
        if df.empty:
            return False
        
        # 컬럼명 대소문자 문제 방지
        df.columns = [str(c).capitalize() for c in df.columns]
        
        if 'Close' not in df.columns:
            return False
            
        # 모든 데이터가 NaN인 경우도 불량
        if df['Close'].isnull().all():
            return False
            
        return True

    def get_sp500_tickers(self):
        """FMP API를 통한 S&P 500 종목 리스트 획득"""
        try:
            data = fetch_fmp("sp500_constituent")
            if data:
                return [item['symbol'] for item in data]
            raise Exception("API 반환 데이터 없음")
        except Exception as e:
            print(f"⚠️ S&P 500 리스트 로드 실패: {e}")
            # 폴백(Fallback) 리스트
            return ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO"]

    def get_historical_prices(self, ticker, period="10y"):
        """
        [원본 복원] 데이터 로드 및 '자가 치유(Self-Healing)' 로직 포함
        """
        file_path = os.path.join(self.data_dir, f"{ticker}.parquet")
        
        # 1. 로컬 파일 확인 (자가 치유 로직 포함)
        if os.path.exists(file_path):
            try:
                df = pd.read_parquet(file_path)
                
                # [검증] 파일이 있지만 내용이 불량하다면? -> 삭제!
                if not self._validate_data(df):
                    print(f"⚠️ 손상된 파일 발견 및 삭제: {ticker}")
                    os.remove(file_path)
                else:
                    # 정상 파일이면 날짜 확인 (최근 3일 이내 데이터인지)
                    last_date = df.index[-1].date()
                    if last_date >= (datetime.now() - timedelta(days=3)).date():
                        return df
            except Exception:
                if os.path.exists(file_path): os.remove(file_path)

        # 2. FMP API를 통한 다운로드 (파일이 없거나 삭제된 경우)
        try:
            data = fetch_fmp(f"historical-price-full/{ticker}")
            if data and 'historical' in data:
                new_df = pd.DataFrame(data['historical'])
                if not new_df.empty:
                    new_df['Date'] = pd.to_datetime(new_df['date'])
                    new_df.set_index('Date', inplace=True)
                    new_df.sort_index(inplace=True)
                    
                    # 컬럼명 표준화 (원종님 형식)
                    new_df.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low', 
                        'close': 'Close', 'volume': 'Volume'
                    }, inplace=True)
                    
                    if self._validate_data(new_df):
                        # Timezone 제거 및 저장
                        if new_df.index.tz is not None:
                            new_df.index = new_df.index.tz_localize(None)
                        new_df.to_parquet(file_path)
                        return new_df
            
            return pd.DataFrame() # 실패 시 빈 데이터프레임
                
        except Exception as e:
            print(f"❌ 데이터 다운로드 실패 ({ticker}): {e}")
            return pd.DataFrame()

    def get_realtime_info(self, ticker):
        """FMP Quote API를 이용한 실시간 정보 획득"""
        try:
            data = fetch_fmp(f"quote/{ticker}")
            if data and len(data) > 0:
                info = data[0]
                return {
                    "name": info.get("name", ticker),
                    "ticker": ticker,
                    "current_price": round(info.get("price", 0), 2),
                    "change_percent": round(info.get("changesPercentage", 0), 2)
                }
            return None
        except:
            return None

    def get_company_basic_info(self, ticker):
        """기업 개요 (FMP Profile API)"""
        try:
            data = fetch_fmp(f"profile/{ticker}")
            if data and len(data) > 0:
                info = data[0]
                return {
                    "summary": info.get("description", "정보 없음"),
                    "sector": info.get("sector", "N/A"),
                    "market_cap": info.get("mktCap", 0),
                    "total_revenue": 0, # Valuation 모듈에서 상세 처리
                    "operating_margins": 0 
                }
            return {}
        except:
            return {}

    def get_sparkline_data(self, ticker, period="1mo"):
        """스파크라인용 최근 주가 리스트"""
        try:
            data = fetch_fmp(f"historical-price-full/{ticker}", timeseries=30)
            if data and 'historical' in data:
                df = pd.DataFrame(data['historical'])
                df.sort_values('date', inplace=True)
                return df['close'].tolist()
            return []
        except:
            return []

    def get_market_index_data(self, period="2y"):
        """S&P 500 지수 데이터"""
        try:
            data = fetch_fmp("historical-price-full/^GSPC")
            if data and 'historical' in data:
                df = pd.DataFrame(data['historical'])
                df['Date'] = pd.to_datetime(df['date'])
                df.set_index('Date', inplace=True)
                df.sort_index(inplace=True)
                return df['close']
            return pd.Series()
        except:
            return pd.Series()

    def get_sector_performance(self):
        """섹터별 성과 데이터 (FMP 전용 엔드포인트)"""
        try:
            data = fetch_fmp("sectors-performance")
            results = []
            if data:
                for item in data:
                    pct_str = str(item.get("changesPercentage", "0")).replace('%', '')
                    try: pct = float(pct_str)
                    except: pct = 0.0
                    results.append({
                        "name": item.get("sector", "Unknown"),
                        "change": pct
                    })
                results.sort(key=lambda x: x['change'], reverse=True)
            return results
        except:
            return []

    def get_dashboard_assets(self):
        return fetch_global_assets_cached()