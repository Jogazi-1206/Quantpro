import os
from google import genai
from dotenv import load_dotenv
from datetime import datetime

# .env 파일 로드
load_dotenv()

class InvestmentReporter:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)
        
        self.model_name = "gemini-2.5-flash"

    def generate_ai_report(self, ticker, data):
        """
        Gemini API를 사용하여 심층 투자 리포트 생성
        """
        if not self.client:
            return "❌ 오류: .env 파일에 GOOGLE_API_KEY가 없습니다."

        try:
            # 1. 데이터 파싱
            info = data.get('info', {})
            basic = data.get('basic', {}) 
            val = data.get('val', {})
            ai = data.get('ai', {})
            macro = data.get('macro', {})
            
            # 2. 매크로 지표 추출
            indicators = macro.get('indicators', {})
            vix = indicators.get('VIX', {}).get('value', 'N/A')
            us10y = indicators.get('US10Y', {}).get('value', 'N/A')
            dxy = indicators.get('DXY', {}).get('value', 'N/A')
            
            # 3. [핵심] 계산 근거(Data Lineage) 추출
            v_data = val.get('data', {})
            formulas = v_data.get('formulas', {})
            formulas_text = "\n".join([f"- {k}: {v}" for k, v in formulas.items()]) if formulas else "데이터 부족"
            
            today = datetime.now().strftime('%Y-%m-%d')
            business_summary = basic.get('summary', '정보 없음')
            sector = basic.get('sector', 'N/A')
            
            # 4. [프롬프트 수정] 표 깨짐 방지 룰 추가 및 목차 양식 개선
            prompt = f"""
Role: 당신은 골드만삭스의 수석 애널리스트이자, 맥킨지 출신의 전략 컨설턴트입니다.
Task: 아래 제공된 [Raw Data]를 완벽하게 분석하여 '{ticker}'에 대한 심층 투자 보고서를 작성하십시오. 
Rule 1: 절대 길게 늘여 쓰지 마십시오. 불릿 포인트(-)를 적극 활용하여 위계 있고 깔끔하게 작성하십시오. (PDF 1~2페이지 분량)
Rule 2: 인터넷 검색으로 지어내지 말고, 반드시 제공된 데이터(특히 재무 수식)를 직접 인용하여 논리를 전개하십시오.
Rule 3: 마크다운 표(Table)를 생성할 때는 반드시 표 위아래로 빈 줄(Enter)을 넣고, 각 행을 줄바꿈하여 표가 절대 깨지지 않게 하십시오.

### [Raw Data]
- 종목: {ticker} ({info.get('name', '')}) / 섹터: {sector}
- 현재가: ${info.get('current_price', 0)}
- 비즈니스 요약: {business_summary}
- 자체 Valuation 퀀트 점수: {val.get('score', 0)}점 / 100점 (평가: {val.get('status', 'N/A')})
- 주요 재무 지표 및 계산 근거:
{formulas_text}
- AI 모델 예측: 향후 단기(5일) 내 급등(ATR 1.5배 상승) 확률 {ai.get('prob', 0):.1f}%
- 거시경제 환경: VIX: {vix} / US10Y: {us10y}% / DXY: {dxy}

---
### 📝 [보고서 양식 - 이 목차와 포맷을 엄격히 따르십시오]

## 📄 {ticker} 심층 투자 리포트
**발행일**: {today} | **애널리스트**: QuantPro AI

### 1. Executive Summary (핵심 요약)
* **투자의견**: (Strong Buy / Buy / Hold / Sell 중 택 1)
* (투자의견에 대한 핵심 근거를 3개의 불릿 포인트로 아주 간결하게 요약)

### 2. Company & Industry Positioning
* **비즈니스 모델**: (무엇을 팔아 돈을 버는지 1~2줄 요약)
* **현재 포지션 및 경제적 해자**: (경쟁사 대비 우위, 기술력/네트워크 효과 등)
* **향후 성장성**: (미래 시장 전망 및 성장 모멘텀)

### 3. Fundamental & Valuation Analysis
**[핵심 재무 지표 현황]**

| 지표명 | 수치 및 계산 근거 | 의미 |
|---|---|---|
| (지표명) | (ex: 주가 ÷ EPS = 30배) | (ex: 섹터 대비 저평가) |

* **Valuation 평가**: (위 표의 숫자를 바탕으로 현재 퀀트 점수 {val.get('score', 0)}점이 나온 이유를 논리적으로 해석)

### 4. AI Momentum & Macro Impact
* **AI 예측 및 기술적 분석**: (AI 예측 확률 {ai.get('prob', 0):.1f}%의 의미와 단기 트렌드 해석)
* **거시경제 리스크**: (VIX, 국채금리 등 현재 매크로 지표가 해당 종목에 미치는 긍정적/부정적 영향)

### 5. Final Strategy (최종 투자 전략)
* **단기 대응 전략**: (매수 타점, 주의사항 등)
* **중장기 보유 전략**: (목표, 리스크 관리 방안)
"""

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            return response.text

        except Exception as e:
            return f"❌ 리포트 생성 중 오류 발생:\n{str(e)}"