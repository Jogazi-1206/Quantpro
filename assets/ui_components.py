import numpy as np
import textwrap

# =========================================================
# [1] 헬퍼 함수: HTML 클리너 (핵심 수정)
# =========================================================
def clean_html(html_str):
    """
    [핵심 수정]
    Streamlit이 들여쓰기된 HTML을 '코드 블록'으로 오인하지 않도록
    모든 줄바꿈(\n)을 공백으로 바꾸고, 불필요한 공백을 제거하여 한 줄로 만듭니다.
    """
    # 1. 우선 textwrap으로 기본 들여쓰기 제거
    dedented = textwrap.dedent(html_str)
    # 2. 줄바꿈을 공백으로 변환 (한 줄로 만들기)
    flat_html = dedented.replace("\n", " ")
    # 3. 앞뒤 공백 제거
    return flat_html.strip()

# =========================================================
# [2] 스파크라인 생성기
# =========================================================
def generate_sparkline_svg(data_list, color="#3182F6"):
    if not data_list or len(data_list) < 2: return ""
    width, height = 100, 35
    try:
        data = [float(x) for x in data_list]
        min_val, max_val = min(data), max(data)
        r = max_val - min_val if max_val != min_val else 1
        
        points = []
        for i, val in enumerate(data):
            x = (i / (len(data) - 1)) * width
            y = height - ((val - min_val) / r) * height
            points.append(f"{x},{y}")
        polyline = " ".join(points)
        stroke = "#23C55E" if color == "green" else "#F43F5E" if color == "red" else color
        
        return f'<svg width="{width}" height="{height}" style="overflow:visible"><polyline points="{polyline}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    except: return ""

# =========================================================
# [3] UI 컴포넌트
# =========================================================

def asset_row_html(name, price, change):
    """[New] 주요 자산 및 지수용 행 디자인"""
    color = "#23C55E" if change >= 0 else "#F43F5E"
    arrow = "▲" if change >= 0 else "▼"
    
    if "Bitcoin" in name or "Nasdaq" in name or "Dow" in name:
        price_str = f"{price:,.0f}"
    else:
        price_str = f"{price:,.2f}"

    return clean_html(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; padding: 12px 0; border-bottom: 1px solid #2A2E35;">
        <span style="color:#D1D5DB; font-size:0.9rem; font-weight:500;">{name}</span>
        <div style="text-align:right;">
            <div style="color:white; font-weight:bold; font-size:1rem;">{price_str}</div>
            <div style="color:{color}; font-size:0.8rem;">{arrow} {abs(change):.2f}%</div>
        </div>
    </div>
    """)

def macro_card_html(title, value, status, color_class="text-gray", progress=50):
    """거시경제 지표 카드"""
    bar_color = "#3182F6"
    if "red" in color_class: bar_color = "#F43F5E"
    elif "green" in color_class: bar_color = "#23C55E"
    elif "yellow" in color_class: bar_color = "#EAB308"
    
    return clean_html(f"""
    <div class="glass-card">
        <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:12px;">
            <div>
                <p style="font-size:0.75rem; font-weight:700; color:#9CA3AF; text-transform:uppercase;">{title}</p>
                <h3 style="font-size:1.8rem; font-weight:700; color:white; margin:0;">{value}</h3>
            </div>
            <span style="font-size:0.7rem; padding:4px 8px; border-radius:6px; background:#2A2E35; color:white;">{status}</span>
        </div>
        <div class="progress-bg"><div style="width:{progress}%; height:100%; background:{bar_color}; border-radius:99px;"></div></div>
    </div>
    """)

def sector_row_html(name, change):
    """섹터별 등락률 바"""
    try:
        val = float(change)
        color = "#23C55E" if val >= 0 else "#F43F5E"
        width = min(abs(val) * 10, 100)
    except: val, color, width = 0, "#9CA3AF", 0
    
    return clean_html(f"""
    <div style="margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px;">
            <span style="color:#D1D5DB;">{name}</span>
            <span style="font-weight:bold; color:{color};">{val:+.2f}%</span>
        </div>
        <div class="progress-bg">
            <div style="width:{width}%; height:100%; background:{color}; border-radius:99px;"></div>
        </div>
    </div>
    """)

def stock_list_item_html(info, score, prob, sparkline_data):
    """리스트 아이템"""
    change = info.get('change_percent', 0)
    color = "green" if change >= 0 else "red"
    text_color = "text-green" if change >= 0 else "text-red"
    spark_svg = generate_sparkline_svg(sparkline_data, color)
    
    return clean_html(f"""
    <div class="glass-card" style="padding:16px; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between; cursor:pointer; border-left: 3px solid {'#23C55E' if score >= 80 else '#2A2E35'};">
        <div style="width:35%;">
            <div style="font-weight:bold; font-size:1.1rem; color:white;">{info['ticker']}</div>
            <div style="font-size:0.75rem; color:#9CA3AF;">{info.get('name', '')[:12]}..</div>
        </div>
        <div style="width:30%; text-align:center;">{spark_svg}</div>
        <div style="width:35%; text-align:right;">
            <div style="font-weight:bold; color:white;">${info.get('current_price', 0):.2f}</div>
            <div style="font-size:0.8rem;" class="{text_color}">{change:+.2f}%</div>
        </div>
    </div>
    """)

def company_header_html(info, basic):
    """기업 기본 정보 헤더"""
    return clean_html(f"""
    <div style="margin-bottom:20px; border-bottom:1px solid #2A2E35; padding-bottom:20px;">
        <div style="display:flex; justify-content:space-between; align-items:end;">
            <div>
                <span style="background:rgba(49, 130, 246, 0.1); color:#3182F6; padding:4px 8px; border-radius:6px; font-size:0.7rem; font-weight:bold;">{basic.get('sector', 'N/A')}</span>
                <h1 style="font-size:2.5rem; font-weight:800; color:white; margin:8px 0;">{info['ticker']}</h1>
                <p style="font-size:0.9rem; color:#9CA3AF; line-height:1.4;">{basic.get('summary', '')[:200]}...</p>
            </div>
            <div style="text-align:right;">
                <div style="font-size:2rem; font-weight:bold; color:white;">${info.get('current_price', 0)}</div>
                <div style="font-size:0.9rem; color:#23C55E;">Live Market</div>
            </div>
        </div>
    </div>
    """)

def metric_grid_html(metrics):
    """기본 재무 정보 그리드"""
    items = ""
    for title, val in metrics.items():
        # [수정] 여기서 f-string 내부의 들여쓰기도 문제가 될 수 있으므로 clean_html을 개별 적용하거나
        # 가장 바깥에서 강력하게 밀어버려야 합니다. 
        # 현재 바뀐 clean_html은 replace('\n', ' ')를 하므로 안전합니다.
        items += f"""
        <div style="background:#1A1D24; padding:16px; border-radius:12px; text-align:center;">
            <p style="font-size:0.75rem; color:#9CA3AF; margin-bottom:4px;">{title}</p>
            <p style="font-size:1rem; font-weight:bold; color:white;">{val}</p>
        </div>
        """
    return clean_html(f'<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom:24px;">{items}</div>')

def valuation_detail_html(score, reasons, comparison):
    """밸류에이션 상세"""
    breakdown_html = ""
    for r in reasons:
        breakdown_html += f"<li style='color:#D1D5DB; font-size:0.85rem; margin-bottom:4px;'>• {r}</li>"

    my_per = float(comparison.get('my_per') or 0)
    avg_per = float(comparison.get('avg_per') or 1)
    if avg_per <= 0: avg_per = 1
    
    ratio = (my_per / avg_per) * 100
    bar_pos_percent = min((my_per / (avg_per * 2)) * 100, 100)
    
    return clean_html(f"""
    <div class="glass-card">
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="font-size:0.8rem; font-weight:bold; color:#9CA3AF;">VALUATION SCORE</span>
            <span style="font-size:1.5rem; font-weight:bold; color:#3182F6;">{score}/100</span>
        </div>
        <div style="background:#2A2E35; height:6px; border-radius:99px; margin-bottom:16px;">
            <div style="width:{score}%; height:100%; background:#3182F6; border-radius:99px;"></div>
        </div>
        <ul style="list-style:none; padding:0; margin:0 0 20px 0;">{breakdown_html}</ul>
        
        <div style="border-top:1px solid #2A2E35; padding-top:15px;">
            <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:5px;">
                <span style="color:#9CA3AF;">PER Comparison</span>
                <span style="color:white;">vs {comparison.get('sector_name')} Avg</span>
            </div>
            <div style="position:relative; height:20px; background:#2A2E35; border-radius:4px; margin-top:10px;">
                <div style="position:absolute; left:50%; top:0; bottom:0; width:2px; background:#9CA3AF; z-index:1;"></div> 
                <div style="position:absolute; top:4px; height:12px; width:4px; background:#3182F6; border-radius:2px; left:{bar_pos_percent}%; transition: left 0.5s;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#9CA3AF; margin-top:4px;">
                <span>저평가</span><span>평균</span><span>고평가</span>
            </div>
        </div>
    </div>
    """)

def ai_prediction_card_html(ai_prob):
    """AI 예측 결과 카드"""
    return clean_html(f"""
    <div class="glass-card">
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="font-size:0.8rem; font-weight:bold; color:#9CA3AF;">AI TREND FORECAST</span>
            <span style="font-size:1.5rem; font-weight:bold; color:#A855F7;">{ai_prob:.1f}%</span>
        </div>
        <div style="background:#2A2E35; height:6px; border-radius:99px; margin-bottom:16px;">
            <div style="width:{ai_prob}%; height:100%; background:#A855F7; border-radius:99px;"></div>
        </div>
        <p style="font-size:0.8rem; color:#D1D5DB;">거시경제 및 기술적 패턴 분석 결과,<br>60일 내 추세 상승 확률입니다.</p>
    </div>
    """)

def final_verdict_html(verdict, score, color_class):
    """최종 판결 카드"""
    color = "#3182F6" 
    if "red" in color_class: color = "#F43F5E"
    elif "yellow" in color_class: color = "#EAB308"
    
    return clean_html(f"""
    <div class="glass-card" style="text-align:center; border: 2px solid {color}; padding: 30px;">
        <p style="font-size:0.8rem; font-weight:bold; color:#9CA3AF; text-transform:uppercase; margin-bottom:8px;">FINAL VERDICT</p>
        <h1 style="font-size:3rem; font-weight:900; color:{color}; margin:0;">{verdict}</h1>
        <p style="font-size:1rem; color:white; margin-top:8px;">Total Score: <b>{score:.0f}</b> / 100</p>
    </div>
    """)

def ai_report_box_html(text):
    """AI 리포트 출력 박스"""
    return clean_html(f"""
    <div class="glass-card" style="border:1px solid #3182F6; padding: 30px;">
        <h3 style="color:white; margin-bottom:16px; font-size:1.2rem;">📑 AI Investment Report</h3>
        <div style="color:#D1D5DB; line-height:1.6; font-size:0.95rem;">
            {str(text).replace(chr(10), '<br>')}
        </div>
    </div>
    """)

def macro_status_html(res, color_class):
    """매크로 상태 배지"""
    color = "#23C55E" if "green" in color_class else "#F43F5E"
    return clean_html(f"""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
        <div style="width:12px; height:12px; border-radius:50%; background:{color}; box-shadow: 0 0 10px {color};"></div>
        <h2 style="margin:0; font-size:1.5rem; color:white;">{res['status']}</h2>
    </div>
    <p style="color:#9CA3AF; margin:0;">Risk Level: <span style="color:white; font-weight:bold;">{res['risk_level']}</span></p>
    """)

def technical_badge_html(signals):
    """기술적 지표 뱃지"""
    badges = ""
    for label, val, color in signals:
        bg = "#23C55E20" if color == "green" else "#F43F5E20" if color == "red" else "#2A2E35"
        txt = "#23C55E" if color == "green" else "#F43F5E" if color == "red" else "#9CA3AF"
        badges += f"<span style='background:{bg}; color:{txt}; padding:4px 8px; border-radius:6px; font-size:0.75rem; font-weight:bold; margin-right:6px;'>{label}</span>"
    return clean_html(f"<div style='margin-bottom:20px;'>{badges}</div>")

def sector_comparison_html(my_per, avg_per, sector_name):
    """섹터 비교 HTML (valuation_detail_html과 중복되지만 app.py 호출 호환성을 위해 유지)"""
    return ""