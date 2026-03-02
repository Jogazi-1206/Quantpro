import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
import warnings
import yfinance as yf
import json
from collections import Counter

# modules 폴더에 있는 data_loader 호출을 위해 경로 추가 필요시 처리
from modules.data_loader import DataLoader 

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")
DATA_DIR = os.path.join(BASE_DIR, "data", "daily_price")
MACRO_FILE = os.path.join(BASE_DIR, "data", "macro_data.csv")
BENCHMARK_FILE = os.path.join(BASE_DIR, "data", "sector_benchmarks.json")

os.makedirs(MODEL_DIR, exist_ok=True)

class StockPredictor:
    def __init__(self):
        self.model_path = os.path.join(MODEL_DIR, "xgboost_price_model.pkl")
        self.model = None
        self.macro_df = None
        self.features = [
            'MA5_Ratio', 'MA20_Ratio', 'MA60_Ratio', 'MA120_Ratio',
            'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
            'BB_Width', 'BB_Pos', 'Stoch_K', 
            'CCI', 'WillR', 'OBV_Ratio', 'MFI',
            'ROC', 'Vol_Change', 'ATR_Ratio', 'Disparity',
            'VIX', 'US10Y', 'DXY'
        ]
        if os.path.exists(self.model_path):
            try: self.model = joblib.load(self.model_path)
            except: self.model = None

    def load_macro_data(self):
        if not os.path.exists(MACRO_FILE): return
        try:
            df = pd.read_csv(MACRO_FILE, index_col=0, parse_dates=True)
            if df.index.tz is not None: df.index = df.index.tz_localize(None)
            self.macro_df = df
        except: pass

    def add_features(self, df, ticker=None):
        if df.empty: return df
        df = df.copy()
        df.columns = [str(c).capitalize() for c in df.columns]
        if 'Adj close' in df.columns: df['Close'] = df['Adj close']
        
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                if isinstance(df[col], pd.DataFrame): df[col] = df[col].iloc[:, 0]
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if df['Close'].isnull().all(): return pd.DataFrame()
        
        try:
            # 1. 이동평균 및 이격도
            for window in [5, 20, 60, 120]:
                df[f'MA{window}'] = df['Close'].rolling(window).mean()
                df[f'MA{window}_Ratio'] = df['Close'] / df[f'MA{window}']
            
            # 2. RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))
            
            # 3. MACD
            ema12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema26 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = ema12 - ema26
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
            
            # 4. 볼린저 밴드
            sma20 = df['Close'].rolling(20).mean()
            std20 = df['Close'].rolling(20).std()
            upper = sma20 + (std20 * 2)
            lower = sma20 - (std20 * 2)
            df['BB_Width'] = (upper - lower) / sma20
            df['BB_Pos'] = (df['Close'] - lower) / (upper - lower)

            # 5. 거래량 지표
            vol = df['Volume'].replace(0, np.nan).ffill()
            df['Vol_Change'] = vol / vol.rolling(20).mean()
            df['OBV_Ratio'] = (vol * np.sign(df['Close'].diff()).fillna(0)).cumsum() / vol.rolling(20).mean()

            # 6. 변동성 및 모멘텀
            tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            df['ATR_Ratio'] = df['ATR'] / df['Close']
            
            low_min = df['Low'].rolling(14).min()
            high_max = df['High'].rolling(14).max()
            df['Stoch_K'] = ((df['Close'] - low_min) / (high_max - low_min)) * 100
            
            tp = (df['High'] + df['Low'] + df['Close']) / 3
            df['CCI'] = (tp - tp.rolling(20).mean()) / (0.015 * (tp - tp.rolling(20).mean()).abs().rolling(20).mean())
            df['WillR'] = (high_max - df['Close']) / (high_max - low_min) * -100
            
            pos_mf = (tp * vol).where(df['Close'].diff() > 0, 0).rolling(14).sum()
            neg_mf = (tp * vol).where(df['Close'].diff() < 0, 0).rolling(14).sum()
            df['MFI'] = 100 - (100 / (1 + (pos_mf / neg_mf)))
            
            df['ROC'] = df['Close'].pct_change(periods=10) * 100
            df['Disparity'] = (df['Close'] / sma20) * 100

            # 7. 매크로 데이터 병합
            if self.macro_df is None: self.load_macro_data()
            if self.macro_df is not None and not self.macro_df.empty:
                df = df.join(self.macro_df, how='left')
                df[['VIX', 'US10Y', 'DXY']] = df[['VIX', 'US10Y', 'DXY']].ffill()
            
            return df
        except: return pd.DataFrame()

    def build_sector_benchmarks(self):
        """S&P 500 종목들을 스캔하여 실시간 섹터 평균 계산"""
        print("\n🏭 [섹터 분석] S&P 500 종목의 최신 펀더멘털 데이터를 스캔합니다...")
        loader = DataLoader()
        tickers = loader.get_sp500_tickers()
        
        sector_data = {}
        count = 0
        total = len(tickers)
        
        for t in tickers:
            try:
                stock = yf.Ticker(t)
                info = stock.info
                
                sector = info.get('sector', 'Unknown')
                if sector == 'Unknown': continue
                
                per = info.get('trailingPE')
                fwd_per = info.get('forwardPE')
                valid_per = per if (per and 0 < per < 200) else fwd_per if (fwd_per and 0 < fwd_per < 200) else None
                
                if valid_per:
                    if sector not in sector_data: sector_data[sector] = []
                    sector_data[sector].append(valid_per)
                
                count += 1
                if count % 50 == 0: print(f"   -> {count}/{total} 종목 스캔 중...", end="\r")
                
            except: continue
            
        benchmarks = {"Default": {"per": 20.0, "peg": 1.5, "name": "시장평균"}}
        
        print("\n📊 [분석 결과] 섹터별 적정 PER 산출:")
        for sec, pers in sector_data.items():
            avg_per = np.median(pers)
            benchmarks[sec] = {
                "per": round(avg_per, 1),
                "peg": 1.5,
                "name": sec
            }
            print(f"   - {sec}: PER {avg_per:.1f}")
            
        with open(BENCHMARK_FILE, 'w', encoding='utf-8') as f:
            json.dump(benchmarks, f, ensure_ascii=False, indent=4)
        print(f"✅ 벤치마크 저장 완료: {BENCHMARK_FILE}")

    def train_model(self):
        self.load_macro_data()
        print(f"\n🚀 [AI 학습] 저장된 모든 주식 데이터로 학습을 시작합니다...")
        
        all_data = []
        files = [f for f in os.listdir(DATA_DIR) if f.endswith('.parquet')]
        
        if not files:
            print("❌ 학습할 데이터가 없습니다.")
            return

        print(f"📂 총 {len(files)}개 파일 로드 중...")
        for i, filename in enumerate(files):
            ticker = filename.replace('.parquet', '')
            file_path = os.path.join(DATA_DIR, filename)
            try:
                df = pd.read_parquet(file_path)
                if df.index.tz is not None: df.index = df.index.tz_localize(None)
                
                processed_df = self.add_features(df, ticker=ticker)
                if processed_df.empty: continue
                
                # [수정] 5일 단기 스윙 전략
                # 기준: 5일(PRED_DAYS) 동안 ATR의 1.5배(ATR_MULT) 이상 상승
                PRED_DAYS, ATR_MULT = 5, 1.5
                
                future_highs = pd.concat([processed_df['High'].shift(-i) for i in range(1, PRED_DAYS + 1)], axis=1)
                max_future_high = future_highs.max(axis=1)
                threshold = (processed_df['ATR'] / processed_df['Close']) * ATR_MULT
                
                processed_df['Target'] = ((max_future_high / processed_df['Close'] - 1) > threshold).astype(int)
                
                all_data.append(processed_df[self.features + ['Target']].dropna())

            except: continue
            
        if not all_data: 
            print("❌ 유효한 학습 데이터가 없습니다.")
            return

        full_df = pd.concat(all_data)
        print(f"✅ 데이터 병합 완료! 총 샘플 수: {len(full_df)}개")
        
        # 클래스 밸런스 확인
        target_counts = Counter(full_df['Target'])
        neg_count = target_counts[0]
        pos_count = target_counts[1]
        
        print(f"\n⚖️ [클래스 밸런스 체크 (5일 내 ATR 1.5배 상승)]")
        print(f"   - 횡보/하락(0): {neg_count}개")
        print(f"   - 급등(1): {pos_count}개")
        
        if pos_count == 0:
            print("❌ '급등(1)' 샘플이 0개입니다. 기준을 조금 더 낮춰보세요.")
            return
            
        # 가중치 자동 계산
        if neg_count > pos_count:
            scale_pos_weight = neg_count / pos_count
            print(f"   👉 급등(1)이 소수입니다. 가중치 {scale_pos_weight:.2f}배 적용")
        else:
            scale_pos_weight = neg_count / pos_count
            print(f"   👉 급등(1)이 다수입니다. 가중치 {scale_pos_weight:.2f}배 적용")
        
        print("\n🤖 XGBoost 모델 학습 중...")
        
        model = xgb.XGBClassifier(
            n_estimators=300, 
            max_depth=8, 
            learning_rate=0.05, 
            n_jobs=-1, 
            random_state=42,
            scale_pos_weight=scale_pos_weight
        )
        model.fit(full_df[self.features], full_df['Target'])
        
        joblib.dump(model, self.model_path)
        print(f"🎉 모델 저장 완료: {self.model_path}")

    def predict_next_move(self, ticker):
        if not self.model: return None
        file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
        
        if os.path.exists(file_path): 
            df = pd.read_parquet(file_path)
        else: 
            try: df = yf.Ticker(ticker).history(period="1y")
            except: return 50.0

        if df.empty: return 50.0
        if df.index.tz is not None: df.index = df.index.tz_localize(None)
        
        df = self.add_features(df, ticker=ticker)
        if df.empty: return 50.0
        
        latest = df.iloc[[-1]]
        if latest[self.features].isnull().any().any(): latest = latest.ffill().bfill()
        
        try: return self.model.predict_proba(latest[self.features])[0][1] * 100
        except: return 50.0

    def get_technical_signals(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if df.empty: return []

            df = self.add_features(df)
            if df.empty: return []
            
            last = df.iloc[-1]
            signals = []

            if 'RSI' in last:
                rsi = last['RSI']
                if rsi > 70: signals.append(("⚠️ RSI 과매수", f"{rsi:.0f}", "red"))
                elif rsi < 30: signals.append(("✅ RSI 과매도", f"{rsi:.0f}", "green"))
                else: signals.append(("RSI 중립", f"{rsi:.0f}", "gray"))

            if 'MA20_Ratio' in last:
                if last['MA20_Ratio'] > 1.0: signals.append(("📈 20일선 위", "상승세", "red"))
                else: signals.append(("📉 20일선 아래", "조정중", "blue"))

            if 'BB_Pos' in last:
                if last['BB_Pos'] > 1.0: signals.append(("⚠️ 밴드 상단", "과열", "red"))
                elif last['BB_Pos'] < 0.0: signals.append(("✅ 밴드 하단", "기회", "green"))

            return signals
        except: return []

if __name__ == "__main__":
    predictor = StockPredictor()
    predictor.train_model()