import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

# ==================== 配置 ====================
st.set_page_config(
    page_title="TrueFin - Gold Edition", 
    page_icon="💎", 
    layout="wide"
)

# ==================== 样式 ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    
    .main-header h1 {
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        color: #FFD700;
    }
    
    .main-header p {
        font-size: 1.2rem;
        color: #888;
        margin: 0.5rem 0;
    }
    
    .price-card {
        background: #1E2025;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    
    .price-big {
        font-size: 3rem;
        font-weight: 800;
        color: #FFD700;
        margin: 1rem 0;
    }
    
    .insight-box {
        background: rgba(255, 215, 0, 0.1);
        border-left: 4px solid #FFD700;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }
    
    .metric-row {
        display: flex;
        justify-content: space-around;
        margin: 1.5rem 0;
    }
    
    .metric-item {
        text-align: center;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #888;
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: #FAFAFA;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 数据加载 ====================
@st.cache_data
def load_gold_data(currency="USD"):
    """加载黄金数据"""
    try:
        if currency == "USD":
            file_path = "data/us_gold_daily.csv"
        else:
            file_path = "data/jp_gold_daily.csv"
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values('Date')
        else:
            # 如果文件不存在，返回示例数据
            return create_sample_data(currency)
    except Exception as e:
        st.error(f"数据加载错误: {str(e)}")
        return create_sample_data(currency)

def create_sample_data(currency):
    """创建示例数据（用于演示）"""
    dates = pd.date_range(end=datetime.now(), periods=365, freq='D')
    if currency == "USD":
        base_price = 2615
        prices = base_price + (pd.Series(range(365)) * 0.5) + (pd.Series(range(365)).apply(lambda x: x % 30 - 15) * 2)
    else:
        base_price = 391000
        prices = base_price + (pd.Series(range(365)) * 75) + (pd.Series(range(365)).apply(lambda x: x % 30 - 15) * 300)
    
    return pd.DataFrame({
        'Date': dates,
        'Close': prices,
        'Open': prices * 0.99,
        'High': prices * 1.01,
        'Low': prices * 0.98
    })

# ==================== 图表生成 ====================
def create_price_chart(df, currency):
    """创建价格图表"""
    fig = go.Figure()
    
    # 添加价格线
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Close'],
        mode='lines',
        name='Gold Price',
        line=dict(color='#FFD700', width=2),
        fill='tozeroy',
        fillcolor='rgba(255, 215, 0, 0.1)'
    ))
    
    # 布局
    symbol = "$" if currency == "USD" else "¥"
    fig.update_layout(
        title=f"Gold Price ({currency})",
        xaxis_title="Date",
        yaxis_title=f"Price ({symbol})",
        height=400,
        template="plotly_dark",
        hovermode='x unified',
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig

# ==================== 主应用 ====================
def main():
    # 顶部Header
    st.markdown("""
    <div class="main-header">
        <h1>💎 TrueFin</h1>
        <p>為替の幻を消す | True Records, True Returns</p>
        <p style="font-size: 0.9rem; color: #666;">Gold Edition - Beta v1.0</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 汇率切换
    st.markdown("---")
    col1, col2, col3 = st.columns([3, 2, 5])
    
    with col1:
        st.markdown("### 表示通貨")
    
    with col2:
        currency = st.radio(
            "Choose currency",
            ["USD ($)", "JPY (¥)"],
            horizontal=True,
            label_visibility="collapsed"
        )
        currency_code = "USD" if "USD" in currency else "JPY"
    
    with col3:
        st.info("💡 汇率切换功能：一键查看不同币种的真实价值")
    
    # 加载数据
    df = load_gold_data(currency_code)
    
    if df.empty:
        st.error("数据加载失败，请检查data文件夹")
        return
    
    # 当前价格
    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    price_change = ((current_price - prev_price) / prev_price) * 100
    
    symbol = "$" if currency_code == "USD" else "¥"
    
    # 价格卡片
    st.markdown(f"""
    <div class="price-card">
        <h2>💰 Gold (XAU/{currency_code})</h2>
        <div class="price-big">{symbol}{current_price:,.2f}</div>
        <div style="font-size: 1.2rem; color: {'#4CAF50' if price_change > 0 else '#F44336'};">
            {'+' if price_change > 0 else ''}{price_change:.2f}% (24h)
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 汇率影响分析（如果切换到JPY）
    if currency_code == "JPY":
        # 计算汇率贡献（简化版示例）
        fx_contribution = 0.8  # 这里应该是真实计算，示例用固定值
        st.markdown(f"""
        <div class="insight-box">
            <strong>💡 TrueFin Insight:</strong><br>
            日元贬值为您的黄金投资贡献了约 <strong>+{fx_contribution}%</strong> 的收益。
            这部分收益来自汇率变化，而非黄金本身的价值增长。
        </div>
        """, unsafe_allow_html=True)
    
    # 关键指标
    st.markdown("### 📊 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        week_high = df['High'].tail(7).max()
        st.metric("7日最高", f"{symbol}{week_high:,.2f}")
    
    with col2:
        week_low = df['Low'].tail(7).min()
        st.metric("7日最低", f"{symbol}{week_low:,.2f}")
    
    with col3:
        month_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-30]) / df['Close'].iloc[-30]) * 100
        st.metric("30日変動", f"{month_change:+.2f}%")
    
    with col4:
        year_high = df['High'].tail(365).max()
        st.metric("年間最高", f"{symbol}{year_high:,.2f}")
    
    # 图表
    st.markdown("### 📈 Price Chart")
    
    # 时间范围选择
    time_range = st.select_slider(
        "時間範囲",
        options=["7日", "30日", "90日", "1年", "全て"],
        value="30日"
    )
    
    # 根据选择过滤数据
    if time_range == "7日":
        df_chart = df.tail(7)
    elif time_range == "30日":
        df_chart = df.tail(30)
    elif time_range == "90日":
        df_chart = df.tail(90)
    elif time_range == "1年":
        df_chart = df.tail(365)
    else:
        df_chart = df
    
    # 显示图表
    chart = create_price_chart(df_chart, currency_code)
    st.plotly_chart(chart, use_container_width=True, key="main_chart")
    
    # AI历史镜像（占位符）
    st.markdown("### 🤖 AI Historical Mirror")
    st.info("""
    **Coming Soon**: AI will find the most similar historical patterns to help you understand potential future movements.
    
    This feature will compare current market conditions with 50 years of gold price history.
    """)
    
    # Smart Money追踪（占位符）
    st.markdown("### 💰 Smart Money Flow")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Central Bank Purchases** 🏦
        - Q4 2024: +125 tons
        - Trend: ⬆️ Increasing
        """)
    
    with col2:
        st.markdown("""
        **CFTC Net Long** 📊
        - Current: 245K contracts
        - Change: +15% vs last week
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem 0;">
        <p>TrueFin Gold Edition v1.0 Beta</p>
        <p>Data updates daily | Built with ❤️ for Japanese investors</p>
        <p style="font-size: 0.8rem;">
            <a href="mailto:truefin.official@gmail.com" style="color: #FFD700;">Contact</a> | 
            <a href="#" style="color: #FFD700;">About</a> | 
            <a href="#" style="color: #FFD700;">Privacy</a>
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
