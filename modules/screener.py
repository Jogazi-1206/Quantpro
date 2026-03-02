import os
from modules.predictor import StockPredictor
from modules.valuation import ValuationAnalyzer

class HiddenGemsScreener:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "daily_price")
        self.predictor = StockPredictor()

    def run_scan(self, min_ai_prob, min_val_score, limit, progress_callback=None):
        """조건에 맞는 저평가 우량주를 스캔하여 리스트로 반환"""
        if not os.path.exists(self.data_dir): 
            return None # 데이터 폴더 없음
            
        files = [f for f in os.listdir(self.data_dir) if f.endswith('.parquet')]
        tickers_to_scan = [f.replace('.parquet', '') for f in files][:limit]
        
        if not tickers_to_scan:
            return [] # 학습 데이터 없음
            
        results = []
        total = len(tickers_to_scan)
        
        for i, ticker in enumerate(tickers_to_scan):
            # UI에 진행 상황을 전달하기 위한 콜백 함수
            if progress_callback:
                progress_callback(i, total, ticker)
                
            try:
                # 1차 필터: 로컬 AI 예측 (초고속)
                ai_prob = self.predictor.predict_next_move(ticker)
                if ai_prob is None or ai_prob < min_ai_prob:
                    continue 
                    
                # 2차 필터: API 기반 펀더멘털 평가 (1차 합격자만)
                val = ValuationAnalyzer(ticker)
                v_data = val.get_financial_data()
                if not v_data: continue
                
                score, _, _ = val.calculate_valuation_score(v_data)
                if score >= min_val_score:
                    results.append({
                        "Ticker": ticker,
                        "Name": v_data.get('name', ticker),
                        "Sector": v_data.get('sector', 'N/A'),
                        "AI Prob": ai_prob,
                        "Val Score": score,
                        "Price": v_data.get('current_price', 0)
                    })
            except:
                continue
                
        # 랭킹 정렬 (AI 확률 + 펀더멘털 점수 합산 내림차순)
        results.sort(key=lambda x: x['AI Prob'] + x['Val Score'], reverse=True)
        return results