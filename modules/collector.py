import time
import os
import sys

# 경로 설정 (모듈 인식을 위해)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_loader import DataLoader

def collect_all_data():
    print("\n🚀 [Data Collector] S&P 500 전 종목 데이터 수집을 시작합니다...")
    
    loader = DataLoader()
    
    # 1. 종목 리스트 가져오기
    print("📋 S&P 500 리스트 확보 중 (위키피디아)...")
    tickers = loader.get_sp500_tickers()
    
    if not tickers:
        print("❌ 종목 리스트를 가져오지 못했습니다. 인터넷 연결을 확인하세요.")
        return

    total = len(tickers)
    print(f"✅ 총 {total}개 종목 발견! 10년 치 데이터 다운로드를 시작합니다.")
    print("   (예상 소요 시간: 10~15분 / 'data/daily_price' 폴더에 저장됩니다)")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    # 2. 반복문으로 데이터 수집
    for i, ticker in enumerate(tickers):
        try:
            # 진행률 표시 (줄바꿈 없이 덮어쓰기 효과)
            print(f"   ⏳ [{i+1}/{total}] {ticker} 다운로드 중...", end="\r")
            
            # 10년 치 데이터 요청 -> 내부적으로 Parquet 저장됨
            df = loader.get_historical_prices(ticker, period="10y")
            
            if not df.empty:
                success_count += 1
            else:
                fail_count += 1
            
            # [중요] 야후 파이낸스 차단 방지를 위한 딜레이
            time.sleep(0.3)
            
        except Exception as e:
            print(f"\n   ❌ {ticker} 실패: {e}")
            fail_count += 1
            continue

    print("\n" + "-" * 50)
    print(f"🎉 수집 완료!")
    print(f"   - 성공: {success_count}개")
    print(f"   - 실패: {fail_count}개")
    print(f"📂 저장 위치: {loader.data_dir}")
    print("👉 이제 'python -m modules.predictor'를 실행하면 전체 데이터로 AI가 학습합니다.")

if __name__ == "__main__":
    collect_all_data()