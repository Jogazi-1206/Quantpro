import pandas as pd
import os

class MacroAnalyzer:
    def __init__(self):
        # 중앙화된 데이터 파일 경로 설정 (data/macro_data.csv)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.file_path = os.path.join(base_dir, "data", "macro_data.csv")

    def get_macro_data(self):
        """
        [New] 인터넷 다운로드 대신, data_loader가 저장한 CSV 파일을 읽어옵니다.
        """
        # 1. 파일 존재 여부 확인
        if not os.path.exists(self.file_path):
            print("❌ [Macro] 데이터 파일이 없습니다. 'python modules/data_loader.py'를 먼저 실행하세요.")
            return None

        try:
            # 2. CSV 읽기 (날짜 컬럼 파싱 포함)
            df = pd.read_csv(self.file_path, index_col=0, parse_dates=True)
            
            if df.empty or len(df) < 2:
                print("⚠️ [Macro] 데이터가 너무 적습니다.")
                return None

            # 3. 최신 데이터 추출 (마지막 행 vs 전일 행 비교)
            latest = df.iloc[-1]   # 오늘
            prev = df.iloc[-2]     # 어제
            
            data = {}
            # data_loader에서 저장한 컬럼명: VIX, US10Y, DXY, SP500
            indicators = ['VIX', 'US10Y', 'DXY', 'SP500']
            
            for ind in indicators:
                # CSV에 해당 컬럼이 있는지 확인
                if ind in df.columns:
                    val = latest[ind]
                    prev_val = prev[ind]
                    
                    # 전일 대비 변화율 계산
                    change = ((val - prev_val) / prev_val) * 100 if prev_val != 0 else 0
                    
                    data[ind] = {
                        "value": val,
                        "change": change
                    }
                else:
                    data[ind] = {"value": 0, "change": 0}

            return data

        except Exception as e:
            print(f"❌ [Macro] 파일 읽기 실패: {e}")
            return None

    def analyze_market_status(self, data):
        """
        거시경제 데이터를 바탕으로 '시장 신호등'을 켭니다.
        (로직은 기존과 동일하지만, 입력 데이터가 CSV 기반으로 안정화됨)
        """
        if not data:
            return {
                "status": "Unknown",
                "risk_level": "알 수 없음",
                "reasons": ["데이터 파일이 없거나 읽을 수 없습니다."]
            }

        score = 0
        reasons = []
        
        # ------------------------------------------------
        # 1. VIX (공포 지수) 평가
        # ------------------------------------------------
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

        # ------------------------------------------------
        # 2. 국채 금리 (10년물) 평가
        # ------------------------------------------------
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

        # ------------------------------------------------
        # 3. 달러 인덱스 (강달러 여부)
        # ------------------------------------------------
        dxy = data.get('DXY', {}).get('value', 0)
        if dxy > 105:
            score -= 1
            reasons.append(f"💵 강달러로 인한 실적 부담 (DXY {dxy:.1f})")
        elif dxy < 100:
            reasons.append("✅ 달러 약세 (위험자산 선호)")
        
        # ------------------------------------------------
        # 종합 판정 (신호등)
        # ------------------------------------------------
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

# 테스트 실행
if __name__ == "__main__":
    print("🌍 거시경제(Macro) 데이터 분석 중 (CSV 모드)...")
    macro = MacroAnalyzer()
    raw_data = macro.get_macro_data()
    
    if raw_data:
        result = macro.analyze_market_status(raw_data)
        print(f"\n======== [ 시장 날씨: {result['status']} ] ========")
        print(f"🌡️ 위험도: {result['risk_level']}")
        print(f"📊 주요 지표:")
        print(f"   - VIX(공포): {raw_data['VIX']['value']:.2f}")
        print(f"   - 국채10년: {raw_data['US10Y']['value']:.2f}%")
        print(f"   - 달러인덱스: {raw_data['DXY']['value']:.2f}")
        print("-" * 30)
        print("💡 [판단 근거]")
        for r in result['reasons']:
            print(f" - {r}")
    else:
        print("\n❌ 데이터를 가져오지 못했습니다. data_loader.py를 실행했는지 확인하세요.")