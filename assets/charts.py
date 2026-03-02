import plotly.graph_objects as go

def plot_market_trend(data, title="Market Trend"):
    """
    [네이버/토스 증권 스타일] S&P 500 차트
    - 기간 선택 버튼 (1M, 3M, 6M, 1Y)
    - 십자선 커서 (Hover)
    - 그라데이션 영역 채우기
    """
    if data.empty:
        return None

    # 데이터가 Series인 경우 처리
    close_data = data
    
    start_p = close_data.iloc[0]
    end_p = close_data.iloc[-1]
    
    # 상승/하락 색상 (한국형: 상승=빨강 / 하락=파랑)
    if end_p >= start_p:
        line_color = '#F43F5E' # Red
        fill_color = 'rgba(244, 63, 94, 0.1)' # 아주 연한 빨강
    else:
        line_color = '#3182F6' # Blue
        fill_color = 'rgba(49, 130, 246, 0.1)' # 아주 연한 파랑

    fig = go.Figure()

    # 메인 라인 차트
    fig.add_trace(go.Scatter(
        x=close_data.index,
        y=close_data,
        mode='lines',
        line=dict(color=line_color, width=2),
        fill='tozeroy',           # 바닥까지 채우기
        fillcolor=fill_color,     # 연한 투명색
        name='S&P 500',
        hovertemplate='%{y:,.2f}' # 호버 시 가격 포맷
    ))

    # 레이아웃 설정 (네이버/토스 느낌)
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=20), # 여백 최소화
        height=350,
        showlegend=False,
        hovermode="x unified", # [핵심] 십자선 커서 모드
        
        # X축 설정 (기간 버튼 추가)
        xaxis=dict(
            type="date",
            showgrid=False,
            showline=False,
            tickfont=dict(color='#9CA3AF', size=11),
            # 기간 선택 버튼 (Range Selector)
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all", label="MAX")
                ]),
                bgcolor="#2A2E35",      # 버튼 배경색
                activecolor="#3182F6",  # 선택된 버튼 색
                font=dict(color="white", size=10),
                x=0, y=1,               # 버튼 위치 (좌측 상단)
                bordercolor="#2A2E35",
                borderwidth=1
            )
        ),
        
        # Y축 설정 (오른쪽에 배치)
        yaxis=dict(
            showgrid=True,         # 가로 격자는 은은하게 유지 (네이버 스타일)
            gridcolor='rgba(42, 46, 53, 0.5)', 
            gridwidth=1,
            showline=False,
            tickfont=dict(color='#9CA3AF', size=11),
            side='right',          # Y축 오른쪽 배치
            tickformat=",.0f"      # 천단위 콤마
        )
    )
    
    return fig

# ... (plot_candle_chart는 기존 유지)
def plot_candle_chart(df):
    """
    개별 종목 상세 분석용 캔들스틱 차트
    """
    if df.empty:
        return None

    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        increasing_line_color='#EF4444', # 빨강
        decreasing_line_color='#3B82F6'  # 파랑
    )])
    
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_rangeslider_visible=False,
        font=dict(color='#9CA3AF'),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#2A2E35')
    )
    return fig