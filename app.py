import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import datetime
import pytz
import importlib

# --- 1. 全局配置 ---
st.set_page_config(page_title="TrueFin - True Records, True Returns", page_icon="💎", layout="wide")

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- 2. 尝试导入宏观数据库 ---
try:
    import macro_data
    importlib.reload(macro_data)
    from macro_data import get_macro_data
    MACRO_DB = get_macro_data()
except Exception:
    MACRO_DB = {}

# --- 3. 状态初始化 ---
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'dashboard'
if 'selected_asset' not in st.session_state: st.session_state.selected_asset = 'XAU/USD'
if 'target_asset' not in st.session_state: st.session_state.target_asset = '黄金 (XAU/USD)'
if 'theme_mode' not in st.session_state: st.session_state.theme_mode = 'Dark'
if 'lang_select' not in st.session_state: st.session_state.lang_select = '日本語'

# --- 4. 样式融合 ---
is_dark = (st.session_state.theme_mode == 'Dark')
bg_color = "#0E1117" if is_dark else "#FFFFFF"
text_color = "#FAFAFA" if is_dark else "#000000"
card_bg = "rgba(255,255,255,0.03)" if is_dark else "#F0F2F6"
border_color = "#333" if is_dark else "#E0E0E0"

css_combined = f"""
<style>
    /* === 全局设定 === */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=Roboto+Mono:wght@400;500;700&family=Oswald:wght@400;500&display=swap');
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    [data-testid="stSidebar"] {{ background-color: #21252B; border-right: 1px solid #333; }}
    
    .macro-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 6px;
        padding: 8px;
        text-align: center;
        height: 100%;
    }}
    .macro-label {{ font-size: 10px; color: #888; display: block; margin-bottom: 2px; }}
    .macro-val {{ font-size: 14px; font-weight: 700; color: {text_color}; font-family: 'Roboto Mono', monospace; }}
    .macro-tag {{ font-size: 9px; padding: 1px 3px; border-radius: 2px; margin-left: 4px; }}
    .tag-mid {{ border: 1px solid #FFD700; color: #FFD700; }}
    .tag-strong {{ border: 1px solid #FF4B4B; color: #FF4B4B; }}
    .tag-low {{ border: 1px solid #00CC96; color: #00CC96; }}

    div.stButton > button {{
        background-color: transparent !important;
        color: #FFD700 !important;
        border: 1px solid #FFD700 !important;
        border-radius: 12px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        padding: 2px 12px !important;
        height: 26px !important;
        min-height: 26px !important;
        line-height: 20px !important;
    }}
    div.stButton > button:hover {{ background-color: rgba(255, 215, 0, 0.1) !important; }}

    /* 分析相关样式 */
    .u-font-mono, .t-date, .grid-val-date {{ font-family: 'Roboto Mono', monospace !important; font-weight: 500 !important; letter-spacing: -0.5px; }}
    .u-font-price, .t-price-text, .grid-val-price {{ font-family: 'Inter', sans-serif !important; font-weight: 600 !important; }}
    .u-font-ret, .t-ret {{ font-family: 'Oswald', sans-serif !important; font-weight: 400 !important; letter-spacing: 0.5px; }}
    
    .ticket-container {{ background-color: transparent; margin-top: 0px; padding: 10px 0 0 0; min-width: 250px; }} 
    .ticket-block {{ 
        background-color: #262730; 
        border: 1px solid #444; 
        border-radius: 8px; 
        padding: 12px 14px; 
        text-align: left; 
        white-space: nowrap; 
        overflow: hidden; 
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 80px; 
    }}
    .t-label {{ font-size: 11px; color: #999; margin-bottom: 2px; font-family: 'Inter', sans-serif; }}
    .t-date {{ font-size: 12px; color: #BBB; margin-bottom: 3px; }}
    .t-price-text {{ font-size: 20px !important; color: #FFD700 !important; line-height: 1.1; }}
    .mid-section {{ display: flex; flex-direction: column; justify-content: center; align-items: center; height: 80px; padding-top: 5px; }}
    .t-arrow {{ font-size: 16px; color: #666; margin-bottom: 0px; }}
    .source-tag {{ font-size: 10px; color: #555; text-align: right; margin-top: 5px; margin-bottom: 10px; font-family: 'Inter', sans-serif; letter-spacing: 0.5px; }}
    
    .sidebar-card {{ background-color: #2D3139; border: 1px solid #444; border-radius: 8px; padding: 15px; margin-top: 20px; margin-bottom: 20px; }}
    .sc-header {{ font-size: 14px; color: #FAFAFA; margin-bottom: 15px; border-bottom: 1px solid #444; padding-bottom: 10px; }}
    .res-header-box {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .big-stat {{ font-size: 26px; font-weight: 600 !important; color: #FFD700; font-family: 'Inter', sans-serif; }}
    .sub-label {{ font-size: 14px; color: #B0B0B0; text-transform: uppercase; letter-spacing: 1px; }}
    
    .res-grid-box {{ background-color: #1E2025; border: 1px solid #333; border-radius: 6px; padding: 14px; margin-top: 5px; margin-bottom: 10px; }}
    .grid-row {{ display: flex; justify-content: space-between; align-items: center; font-size: 14px; margin-bottom: 6px; }}
    .grid-val-price {{ color: #FFF; font-size: 14px; }}
    .tag-match {{ color: #00E5FF; font-size: 11px; border: 1px solid #00E5FF; padding: 1px 6px; border-radius: 3px; margin-right: 5px; font-weight: 500; }}
    .tag-proj {{ color: #FF6D00; font-size: 11px; border: 1px solid #FF6D00; padding: 1px 6px; border-radius: 3px; margin-right: 5px; font-weight: 500; }}
    .grid-divider {{ border-bottom: 1px dashed #333; margin: 10px 0; }}

    .res-macro-box {{ background-color: #1E2025; border: 1px solid #333; border-radius: 6px; padding: 15px; }}
    .driver-label {{ color: #666; font-weight: 500; font-size: 12px; margin-right: 5px; text-transform: uppercase; width: 95px; display: inline-block; white-space: nowrap;}}
    .macro-text-row {{ font-size: 14px; color: #999; margin-bottom: 8px; line-height: 1.6; display: flex; align-items: center; font-family: 'Inter', sans-serif;}}
    .highlight-factor {{ color: #FAFAFA !important; font-weight: 600; border-left: 3px solid #FFD700; padding-left: 8px; margin-left: -11px; background: linear-gradient(90deg, rgba(255, 215, 0, 0.1) 0%, rgba(0,0,0,0) 100%); }}
    .highlight-label {{ color: #FFD700 !important; font-weight: 700 !important; }}
    .macro-desc {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid #444; color: #FFFFFF; font-size: 14px; line-height: 1.6; font-weight: 400; font-family: 'Inter', sans-serif;}}

    /* TrueFin 品牌标语 */
    .truefin-tagline {{
        text-align: center;
        color: #888;
        font-size: 11px;
        font-family: 'Inter', sans-serif;
        margin-top: 5px;
        letter-spacing: 0.5px;
    }}

    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
</style>
"""
st.markdown(css_combined, unsafe_allow_html=True)

# --- 5. 辅助函数与逻辑库 ---

def switch_to_analysis(asset):
    map_dict = {
        "XAU/USD": "黄金 (XAU/USD)", "Gold (XAU/USD)": "黄金 (XAU/USD)",
        "XAU/JPY": "日元金 (XAU/JPY)", "USD/JPY": "美日 (USD/JPY)",
        "EUR/JPY": "欧日 (EUR/JPY)", "S&P 500": "标普500 (S&P 500)", "S&P 500 (SPX)": "标普500 (S&P 500)"
    }
    st.session_state.target_asset = map_dict.get(asset, asset)
    st.session_state.view_mode = 'analysis'

def switch_to_dashboard():
    st.session_state.view_mode = 'dashboard'

def toggle_theme():
    st.session_state.theme_mode = 'Light' if st.session_state.theme_mode == 'Dark' else 'Dark'

def get_tokyo_time():
    jp_tz = pytz.timezone('Asia/Tokyo')
    now = datetime.datetime.now(jp_tz)
    return now.strftime("%Y-%m-%d %H:%M JST")

def render_macro_card(label, val, tag_text, tag_type, date_text):
    tag_class = f"tag-{tag_type}" if tag_type else ""
    tag_html = f"<span class='macro-tag {tag_class}'>{tag_text}</span>" if tag_text else ""
    date_c = "#888"
    return f"""<div class="macro-card"><span class="macro-label">{label}</span><span class="macro-val">{val}</span>{tag_html}<div style="font-size:9px; color:{date_c}; margin-top:2px">{date_text}</div></div>"""

def get_title_html(title, df, is_gold=False, df_jpy=None):
    TRANSLATIONS = {
        "日本語": {"source_label": "出所: Investing.com"},
        "English": {"source_label": "Source: Investing.com"},
        "中文": {"source_label": "数据来源: Investing.com"}
    }
    L_func = TRANSLATIONS.get(st.session_state.get('lang_select', '日本語'), TRANSLATIONS['日本語'])
    source_text = L_func.get('source_label', 'Source: Investing.com')
    if df.empty: return "No Data"
    last = df.iloc[-1]['Close']
    prev = df.iloc[-2]['Close'] if len(df) > 1 else last
    chg = (last - prev) / prev * 100
    color = '#00CC96' if chg >= 0 else '#FF4B4B'
    sign = "+" if chg >= 0 else ""
    unit = "¥" if ("JPY" in title or "円" in title) else "$"
    if "S&P" in title or "标普" in title: unit = ""
    text_c = "#FAFAFA" if is_dark else "#000000"
    source_html = f"<div style='font-size: 9px; color: #888; margin-top: 2px; font-weight: normal;'>{source_text}</div>"
    if is_gold and df_jpy is not None and not df_jpy.empty:
        jpy_price = df_jpy.iloc[-1]['Close']
        jpy_chg = (jpy_price - df_jpy.iloc[-2]['Close']) / df_jpy.iloc[-2]['Close'] * 100
        jpy_c = '#00CC96' if jpy_chg >= 0 else '#FF4B4B'
        line_c = "#555" if is_dark else "#CCC"
        main_title = f"<span style='font-size:14px; font-weight:bold; color:{text_c}'>{title}</span> <span style='font-size:14px; color:{color}; font-weight:bold'>${last:,.2f}</span> <span style='color:{line_c}; margin: 0 5px'>|</span><span style='color:#FFD700; font-size:18px; font-weight:800'> ¥{jpy_price:,.0f}</span> <span style='font-size:12px; color:{jpy_c}'>({jpy_chg:+.2f}%)</span>"
    else:
        main_title = f"<span style='font-size:15px; font-weight:bold; color:{text_c}'>{title}</span> <span style='font-size:15px; color:{text_c}; font-weight:bold; margin-left:6px'>{unit}{last:,.2f}</span> <span style='font-size:13px; color:{color}; margin-left:4px'>({sign}{chg:.2f}%)</span>"
    return f"<div>{main_title}{source_html}</div>"

@st.cache_data
def load_deep_data(asset_name):
    filename = ""
    possible_filenames = []
    
    if "XAU/USD" in asset_name or "Gold" in asset_name or "黄金" in asset_name:
        possible_filenames = ["us_gold_daily.csv"]
        sub_folder = os.path.join("Gold_Section", "XAU_USD_Data")
    elif "XAU/JPY" in asset_name or "日元金" in asset_name:
        possible_filenames = ["jp_gold_daily.csv"]
        sub_folder = os.path.join("Gold_Section", "XAU_JPY_Data")
    elif "USD/JPY" in asset_name:
        possible_filenames = ["usjp_fx_daily.csv"]
        sub_folder = os.path.join("Forex_Section", "USD_JPY_Data")
    elif "EUR/JPY" in asset_name:
        possible_filenames = ["eujp_fx_daily.csv"]
        sub_folder = os.path.join("Forex_Section", "EUR_JPY_Data")
    elif "S&P" in asset_name or "标普" in asset_name:
        # === 核心修改：加入了 sp500_daily.csv ===
        possible_filenames = ["sp500_daily.csv", "spx_daily.csv", "S&P500.csv", "GSPC.csv", "SPX.csv"]
        sub_folder = os.path.join("S&P500_Section", "Index_Data")
    else:
        return pd.DataFrame()

    project_root = os.path.dirname(current_dir)
    
    # 尝试寻找文件
    final_path = None
    for fname in possible_filenames:
        paths = [
            os.path.join(project_root, sub_folder, fname), 
            os.path.join(current_dir, sub_folder, fname), 
            os.path.join(current_dir, fname)
        ]
        found = next((p for p in paths if os.path.exists(p)), None)
        if found:
            final_path = found
            break
            
    if not final_path: return pd.DataFrame()

    try:
        df = pd.read_csv(final_path)
        df.columns = [c.strip() for c in df.columns]
        if 'Date' not in df.columns:
            rename_map = {'日期': 'Date', '收盘': 'Close', 'Price': 'Close', 'date': 'Date', 'close': 'Close'}
            df.rename(columns=rename_map, inplace=True)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df.dropna(subset=['Date', 'Close'], inplace=True)
        for col in ['Close', 'Open', 'High', 'Low']:
            if col in df.columns and df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '').astype(float)
        df.sort_values('Date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        if "us_gold" in str(possible_filenames):
            fund_folder = os.path.join("Gold_Section", "Fundamental_Data")
            cftc_path = next((os.path.join(r, fund_folder, "cftc_cot_gold.csv") for r in [project_root, current_dir] if os.path.exists(os.path.join(r, fund_folder, "cftc_cot_gold.csv"))), None)
            if cftc_path:
                try:
                    df_c = pd.read_csv(cftc_path)
                    df_c['Date'] = pd.to_datetime(df_c['Date'])
                    df_c.sort_values('Date', inplace=True)
                    df = pd.merge_asof(df, df_c[['Date', 'Money_Manager_Net']], on='Date', direction='backward')
                    df['Money_Manager_Net'] = df['Money_Manager_Net'].fillna(0)
                except: df['Money_Manager_Net'] = 0
            
            wgc_path = next((os.path.join(r, fund_folder, "wgc_central_bank.csv") for r in [project_root, current_dir] if os.path.exists(os.path.join(r, fund_folder, "wgc_central_bank.csv"))), None)
            if wgc_path:
                try:
                    df_w = pd.read_csv(wgc_path)
                    df_w['Date'] = pd.to_datetime(df_w['Date'])
                    df_w.sort_values('Date', inplace=True)
                    df = pd.merge_asof(df, df_w[['Date', 'Net_Purchase_Tonnes']], on='Date', direction='backward')
                    df['Net_Purchase_Tonnes'] = df['Net_Purchase_Tonnes'].fillna(0)
                except: df['Net_Purchase_Tonnes'] = 0
        return df
    except: return pd.DataFrame()

@st.cache_data
def precompute_vectors(df, window=90):
    price_vectors = []
    indices = []
    prices = df['Close'].values
    if len(prices) > window:
        for i in range(0, len(prices) - window, 5): 
            p_data = prices[i : i+window]
            p_vec = p_data / p_data[0]
            price_vectors.append(p_vec)
            indices.append(i)
    return np.array(price_vectors), indices

def get_macro_tags(year):
    tags = set()
    if (1973 <= year <= 1982) or (2021 <= year <= 2023): tags.add("High Inflation")
    elif (1990 <= year <= 2008): tags.add("Great Moderation")
    if year in [1973, 1974, 1977, 1978, 1979, 1980, 1994, 1999, 2004, 2005, 2006, 2015, 2016, 2017, 2018, 2022, 2023]: tags.add("Tightening")
    if year in [1975, 1982, 1990, 1991, 1992, 2001, 2002, 2003, 2008, 2009, 2019, 2020]: tags.add("Easing")
    if year in [1971, 1979, 1980, 1987, 1990, 2000, 2001, 2008, 2009, 2020, 2022]: tags.add("Crisis")
    return tags

def get_macro_info(year_str, lang_code):
    data = MACRO_DB.get(year_str)
    if not data:
        for k in sorted(MACRO_DB.keys(), reverse=True):
            if k.isdigit() and abs(int(year_str) - int(k)) <= 2:
                data = MACRO_DB[k]; break
    if not data: 
        data = {"dominant": "fed", lang_code: {"event": "Unknown", "rate": "-", "geo": "-", "desc": "Data not available", "source": ""}}
    info = data.get(lang_code, data.get('en', {}))
    info['dominant'] = data.get('dominant', 'fed')
    return info

def render_header(label, idx, score):
    return f'<div class="res-header-box"><span class="sub-label">{label} 0{idx+1}</span><span class="big-stat">{score}%</span></div>'

def render_grid(L, mi, pi, m_c, m_s, p_c, p_s, rank_color):
    return f'''<div class="res-grid-box"><div class="grid-row"><span><span class="tag-match" style="color:{rank_color}; border-color:{rank_color};">{L['grid_match']}</span><span class="grid-val-date u-font-date">{mi['s_date']} ➜ {mi['e_date']}</span></span></div><div class="grid-row"><span class="grid-val-price u-font-price" style="margin-left:auto;">${int(mi['s_price'])} ➜ ${int(mi['e_price'])} (<span style="color:{m_c}" class="u-font-ret">{m_s}</span>)</span></div><div class="grid-divider"></div><div class="grid-row"><span><span class="tag-proj" style="color:{rank_color}; border-color:{rank_color};">{L['grid_proj']}</span><span class="grid-val-date u-font-date">{pi['s_date']} ➜ {pi['e_date']}</span></span></div><div class="grid-row"><span class="grid-val-price u-font-price" style="margin-left:auto;">${int(pi['s_price'])} ➜ ${int(pi['e_price'])} (<span style="color:{p_c}" class="u-font-ret">{p_s}</span>)</span></div></div>'''

def render_macro(L, macro):
    dom = macro.get('dominant', 'fed')
    cls_event = "highlight-factor" if dom in ['geo','liq'] else ""
    cls_rate = "highlight-factor" if dom == 'fed' else ""
    cls_geo = "highlight-factor" if dom == 'geo' else ""
    lbl_cls_event = "highlight-label" if cls_event else "driver-label"
    lbl_cls_rate = "highlight-label" if cls_rate else "driver-label"
    lbl_cls_geo = "highlight-label" if cls_geo else "driver-label"
    val_style_event = "color:#FFF; font-weight:600;" if cls_event else "color:#999; font-weight:400;"
    val_style_rate = "color:#FFF; font-weight:600;" if cls_rate else "color:#999; font-weight:400;"
    val_style_geo = "color:#FFF; font-weight:600;" if cls_geo else "color:#999; font-weight:400;"
    raw_src = macro.get('source', '')
    src_text = raw_src.replace("Source", L['source_prefix']) if "Source" in raw_src else (f"{L['source_prefix']}: {raw_src}" if raw_src else "")

    return f'''
    <div class="res-macro-box">
    <div class="macro-text-row {cls_event}"><span class="{lbl_cls_event}">{L['lbl_event']}:</span> <span style="{val_style_event}">{macro.get('event','-')}</span></div>
    <div class="macro-text-row {cls_rate}"><span class="{lbl_cls_rate}">{L['lbl_rate']}:</span> <span style="{val_style_rate}">{macro.get('rate','-')}</span></div>
    <div class="macro-text-row {cls_geo}"><span class="{lbl_cls_geo}">{L['lbl_geo']}:</span> <span style="{val_style_geo}">{macro.get('geo','-')}</span></div>
    <div class="macro-desc">{macro.get('desc','-')}</div>
    <div style="font-size:10px; color:#555; text-align:right; margin-top:5px;">{src_text}</div>
    </div>
    '''

def align_to_daily(df_slice):
    if df_slice.empty: return df_slice
    df_slice = df_slice.set_index('Date')
    df_slice = df_slice.resample('B').ffill()
    df_slice = df_slice.reset_index()
    return df_slice

# --- V14.1 季节性分析 ---
def calculate_seasonality(df):
    df = df.copy()
    monthly_df = df.set_index('Date').resample('ME').last()
    monthly_df['Return'] = monthly_df['Close'].pct_change() * 100
    monthly_df.dropna(inplace=True)
    monthly_df['Month'] = monthly_df.index.month
    
    stats = []
    months_label = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    for m in range(1, 13):
        m_data = monthly_df[monthly_df['Month'] == m]
        if len(m_data) > 0:
            avg_ret = m_data['Return'].mean()
            win_count = len(m_data[m_data['Return'] > 0])
            total_count = len(m_data)
            win_rate = (win_count / total_count) * 100
            stats.append({"Month_Code": m, "Month": months_label[m-1], "Avg_Return": avg_ret, "Win_Rate": win_rate, "Years_Count": total_count})
    return pd.DataFrame(stats)

def render_seasonality_chart(stats_df, df_full_range, is_dark=True):
    s_year = df_full_range['Date'].dt.year.min()
    e_year = df_full_range['Date'].dt.year.max()
    long_term_ref = {1: 1.85, 2: 0.25, 3: -0.30, 4: 0.45, 5: 0.15, 6: -0.10, 7: 0.30, 8: 1.10, 9: 1.65, 10: -0.20, 11: 0.65, 12: 1.10}
    ret_map = dict(zip(stats_df['Month_Code'], stats_df['Avg_Return']))
    win_map = dict(zip(stats_df['Month_Code'], stats_df['Win_Rate']))
    
    grid_layout = [[9, 10, 11, 12], [5, 6, 7, 8], [1, 2, 3, 4]]
    z_data, text_data = [], []
    vals = list(ret_map.values())
    v_min = min(vals) if vals else 0
    
    for row in grid_layout: 
        z_row, t_row = [], []
        for m_code in row:
            ret = ret_map.get(m_code, 0)
            win = win_map.get(m_code, 0)
            ref_ret = long_term_ref.get(m_code, 0)
            month_name = datetime.date(2000, m_code, 1).strftime('%b')
            z_row.append(ret)
            icon = "🔥" if ret > 2.0 else ("❄️" if ret < 0 else "")
            t_row.append(f"<b>{month_name}</b><br><span style='font-size:14px'>{ret:+.1f}%</span><br><span style='font-size:9px; color:#CCC'>Win:{win:.0f}% {icon}</span>")
        z_data.append(z_row)
        text_data.append(t_row)

    if v_min > 0: colorscale = [[0.0, '#263238'], [0.5, '#B71C1C'], [1.0, '#FF4B4B']]
    else: colorscale = [[0.0, '#00CC96'], [0.5, '#1E2025'], [1.0, '#FF4B4B']]

    fig = go.Figure(data=go.Heatmap(
        z=z_data, x=['M1', 'M2', 'M3', 'M4'], y=['Q4', 'Q2', 'Q1'], 
        text=text_data, texttemplate="%{text}", textfont={"size": 11, "color": "white", "family": "Roboto Mono"},
        colorscale=colorscale, zmid=0 if v_min <=0 else None, showscale=False, xgap=3, ygap=3
    ))
    fig.update_layout(
        title=f"<b>Seasonal Heatmap</b> <span style='font-size:10px; color:#888'>Data: {s_year}-{e_year}</span>",
        title_font=dict(size=14, color="#FFD700" if is_dark else "#333"),
        template="plotly_dark" if is_dark else "plotly_white",
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=260,
        margin=dict(l=10, r=10, t=35, b=10), xaxis=dict(visible=False), yaxis=dict(visible=False)
    )
    return fig

# --- 6. 主程序入口 ---

if st.session_state.view_mode == 'dashboard':
    TRANSLATIONS = {
        "日本語": {"analyze": "詳細分析", "theme_dark": "ダーク", "theme_light": "ライト", "gold_title": "ゴールド (XAU/USD)", "uj_title": "ドル円 (USD/JPY)", "spx_title": "S&P 500", "ej_title": "ユーロ円 (EUR/JPY)", "macro_yield": "米国10年債", "macro_cpi": "米国CPI", "macro_nfp": "雇用統計", "macro_vix": "恐怖指数", "tag_mid": "粘着", "tag_strong": "強い", "tag_low": "安定"},
        "English": {"analyze": "Deep Dive", "theme_dark": "Dark", "theme_light": "Light", "gold_title": "Gold (XAU/USD)", "uj_title": "USD/JPY", "spx_title": "S&P 500", "ej_title": "EUR/JPY", "macro_yield": "US 10Y Yield", "macro_cpi": "US CPI", "macro_nfp": "Non-Farm Payrolls", "macro_vix": "VIX Index", "tag_mid": "Sticky", "tag_strong": "Strong", "tag_low": "Low"},
        "中文": {"analyze": "深度分析", "theme_dark": "暗色", "theme_light": "亮色", "gold_title": "黄金 (XAU/USD)", "uj_title": "美日 (USD/JPY)", "spx_title": "标普 500", "ej_title": "欧日 (EUR/JPY)", "macro_yield": "美债10年", "macro_cpi": "美国CPI", "macro_nfp": "非农数据", "macro_vix": "恐慌指数", "tag_mid": "顽固", "tag_strong": "强劲", "tag_low": "低波"}
    }
    L = TRANSLATIONS[st.session_state.get('lang_select', '日本語')]

    # --- 修复后的绘图引擎 (Fix Chart Engine) ---
    def render_gold_monitor_fixed(df_usd, df_jpy, theme='Dark'):
        """ XAU/USD (Left Axis) + XAU/JPY (Right Axis, Solid Yellow) + No Slider """
        is_dk = (theme == 'Dark')
        
        df_u = df_usd.copy().tail(90)
        df_j = df_jpy.copy().tail(90)
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 2. XAU/USD K线 (主轴 - 左侧)
        if not df_u.empty:
            fig.add_trace(go.Candlestick(
                x=df_u['Date'], open=df_u['Open'], high=df_u['High'], low=df_u['Low'], close=df_u['Close'],
                name="XAU/USD", increasing_line_color='#00CC96', decreasing_line_color='#FF4B4B'
            ), secondary_y=False)

        # 3. XAU/JPY 黄线 (副轴 - 右侧 - 实线)
        if not df_j.empty:
             fig.add_trace(go.Scatter(
                x=df_j['Date'], y=df_j['Close'], mode='lines', name="XAU/JPY",
                line=dict(color='#FFD700', width=1.5) # Removed dash='dot' (实线)
            ), secondary_y=True)

        grid_c = "#333" if is_dk else "#EEE"
        font_c = "#AAA" if is_dk else "#333"
        
        fig.update_layout(
            template="plotly_dark" if is_dk else "plotly_white",
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            height=280, margin=dict(l=5, r=5, t=10, b=20),
            showlegend=False,
            xaxis_rangeslider_visible=False, # 移除底部滑块
            xaxis=dict(
                type='date', 
                rangebreaks=[dict(bounds=["sat", "mon"])],
                showgrid=False, 
                tickformat="%m-%d",
                tickfont=dict(size=10, color=font_c)
            ),
            yaxis=dict(showgrid=True, gridcolor=grid_c, tickfont=dict(size=10, color=font_c), side='left'),
            # 右侧轴显示 XAU/JPY 价格 (符合你的要求)
            yaxis2=dict(showgrid=False, showticklabels=True, side='right', tickfont=dict(color='#FFD700', size=10)) 
        )
        return fig

    def render_mini_candle_fixed(df, theme='Dark'):
        """ Standard Candle + Right Axis + No Slider """
        is_dk = (theme == 'Dark')
        df_s = df.copy().tail(90)
        
        fig = go.Figure()
        if not df_s.empty:
            fig.add_trace(go.Candlestick(
                x=df_s['Date'], open=df_s['Open'], high=df_s['High'], low=df_s['Low'], close=df_s['Close'],
                name="Price", increasing_line_color='#00CC96', decreasing_line_color='#FF4B4B'
            ))

        grid_c = "#333" if is_dk else "#EEE"
        font_c = "#AAA" if is_dk else "#333"

        fig.update_layout(
            template="plotly_dark" if is_dk else "plotly_white",
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            height=280, margin=dict(l=5, r=5, t=10, b=20),
            showlegend=False,
            xaxis_rangeslider_visible=False, # 移除底部滑块
            xaxis=dict(
                type='date',
                rangebreaks=[dict(bounds=["sat", "mon"])],
                showgrid=False,
                tickformat="%m-%d",
                tickfont=dict(size=10, color=font_c)
            ),
            # 单品种图表价格显示在右侧 (符合交易员习惯)
            yaxis=dict(showgrid=True, gridcolor=grid_c, tickfont=dict(size=10, color=font_c), side='right')
        )
        return fig
    # -----------------------------------------------------------

    with st.container():
        c1, c2, c3, c4, c5 = st.columns([2, 3, 1.8, 1.2, 1])
        with c1: 
            st.markdown(f"<h3 style='margin:0; color:#FFD700;'>TrueFin <span style='font-size:11px; color:#666'>真実記録</span></h3>", unsafe_allow_html=True)
            st.markdown("<p class='truefin-tagline'>為替の幻を消す | True Records, True Returns</p>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div style='text-align:right; font-family:Roboto Mono; font-size:14px; color:#AAA; margin-top:5px;'>{get_tokyo_time()}</div>", unsafe_allow_html=True)
        with c4: lang = st.selectbox("Lang", ["日本語", "English", "中文"], key="lang_select", label_visibility="collapsed")
        with c5:
            btn_label = L['theme_light'] if is_dark else L['theme_dark']
            if st.button(btn_label, key="theme_toggle"): toggle_theme(); st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(render_macro_card(L['macro_yield'], "4.02%", "", "", "Live"), unsafe_allow_html=True)
    with m2: st.markdown(render_macro_card(L['macro_cpi'], "3.4%", L['tag_mid'], "mid", "Jan 12"), unsafe_allow_html=True)
    with m3: st.markdown(render_macro_card(L['macro_nfp'], "216k", L['tag_strong'], "strong", "Jan 05"), unsafe_allow_html=True)
    with m4: st.markdown(render_macro_card(L['macro_vix'], "13.5", L['tag_low'], "low", "Live"), unsafe_allow_html=True)
    st.markdown("---")

    with st.spinner("Loading Market Data..."):
        df_xau_usd = load_data_by_asset("XAU/USD", current_dir) if 'load_data_by_asset' in locals() else load_deep_data("XAU/USD")
        df_xau_jpy = load_data_by_asset("XAU/JPY", current_dir) if 'load_data_by_asset' in locals() else load_deep_data("XAU/JPY")
        df_usdjpy  = load_data_by_asset("USD/JPY", current_dir) if 'load_data_by_asset' in locals() else load_deep_data("USD/JPY")
        df_eurjpy  = load_data_by_asset("EUR/JPY", current_dir) if 'load_data_by_asset' in locals() else load_deep_data("EUR/JPY")
        df_spx     = load_data_by_asset("S&P 500", current_dir) if 'load_data_by_asset' in locals() else load_deep_data("S&P 500")

    def render_grid_cell(btn_key, asset_val, chart_fig, title_html):
        h1, h2 = st.columns([0.25, 0.75]) 
        with h1:
            if st.button(L['analyze'], key=btn_key): switch_to_analysis(asset_val); st.rerun()
        with h2: st.markdown(f"<div style='margin-top: 5px;'>{title_html}</div>", unsafe_allow_html=True)
        st.plotly_chart(chart_fig, use_container_width=True, config={'displayModeBar': False})

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            t1 = get_title_html(L['gold_title'], df_xau_usd, is_gold=True, df_jpy=df_xau_jpy)
            fig1 = render_gold_monitor_fixed(df_xau_usd, df_xau_jpy, theme=st.session_state.theme_mode)
            render_grid_cell("btn_g", "XAU/USD", fig1, t1)
    with col2:
        with st.container(border=True):
            t2 = get_title_html(L['uj_title'], df_usdjpy)
            fig2 = render_mini_candle_fixed(df_usdjpy, theme=st.session_state.theme_mode)
            render_grid_cell("btn_uj", "USD/JPY", fig2, t2)

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            t3 = get_title_html(L['spx_title'], df_spx)
            fig3 = render_mini_candle_fixed(df_spx, theme=st.session_state.theme_mode)
            render_grid_cell("btn_spx", "S&P 500", fig3, t3)
    with col4:
        with st.container(border=True):
            t4 = get_title_html(L['ej_title'], df_eurjpy)
            fig4 = render_mini_candle_fixed(df_eurjpy, theme=st.session_state.theme_mode)
            render_grid_cell("btn_ej", "EUR/JPY", fig4, t4)

else:
    # ... (保持分析模式逻辑不变)
    LANG_DICT = {
        "中文": {
            "code":"cn", "title":"TrueFin", "subtitle":"真实收益 | AI 历史镜像分析", 
            "asset_label":"标的", "time_nav":"时段导航", "year_label":"选择年份", "date_label":"选择交易日", 
            "mode_label": "图表显示状态", 
            "mode_pattern": "90天走线拟合与未来推演", 
            "mode_context": "历史大周期与宏观背景", 
            "mode_bull": "三大牛市赛跑 (Secular Bull Race)",
            "mode_vshape": "历史V型反转对比 (V-Shape Recovery)",
            "filter_label": "宏观体制过滤", "filter_help": "仅在选定的宏观背景中搜索历史相似走势。", "no_filter": "不过滤 (全历史)",
            "axis_bull_x": "牛市启动以来天数", "axis_bull_y": "价格 (美元) - 重定基",
            "chart_bull_title": "黄金长期牛市对比 (重定基至{year}年价格)",
            "axis_v_x": "触底以来天数 (Days Since Bottom)", "axis_v_y": "反弹幅度 (%)",
            "chart_v_title": "标普500 历史V型反转对比 (底部对齐 = 0%)",
            "grid_match": "历史", "grid_proj": "推演", "match_no": "相似排名", "show_line": "显示该K线", 
            "legend_current": "选择时段K线", "legend_match": "历史相似", "legend_real_future": "实际后续走势",
            "axis_title": "日期", "axis_y_title": "价格 (美元)", "axis_y2_title": "资金流向", "axis_cftc": "CFTC (合约)", "axis_wgc": "WGC (吨)",
            "fund_legend_cftc": "机构净多头", "fund_legend_wgc": "央行净购金", "tooltip_date": "日期", "tooltip_price": "价格",
            "ticket_start": "90天前报价 / 收盘 ($)", "ticket_end": "当日报价 / 收盘 ($)", "lbl_source": "数据来源",
            "lbl_event": "核心事件", "lbl_rate": "美联储利率", "lbl_geo": "地缘风险", "source_prefix": "数据来源",
            "sidebar_context_title": "选择时段局势"
        }
    }
    
    if "show_rank_0" not in st.session_state: st.session_state["show_rank_0"] = True
    if "show_rank_1" not in st.session_state: st.session_state["show_rank_1"] = True
    if "show_rank_2" not in st.session_state: st.session_state["show_rank_2"] = True

    with st.sidebar:
        if st.button("⬅ 返回仪表盘 / Dashboard", use_container_width=True): switch_to_dashboard(); st.rerun()
        st.markdown(f"<h2 style='color:#FFD700;'>TrueFin</h2>", unsafe_allow_html=True)
        lang_key, lang_code = "中文", "cn"
        L = LANG_DICT[lang_key]
        selected_asset = st.session_state.get("target_asset", "黄金 (XAU/USD)")

        st.divider()
        st.caption(f"当前分析标的: {selected_asset}")
        st.caption(L['mode_label'])
        if "XAU" in selected_asset or "Gold" in selected_asset or "黄金" in selected_asset:
            modes = [L['mode_pattern'], L['mode_context'], L['mode_bull']]
            is_gold = True
        else:
            modes = [L['mode_pattern'], L['mode_context'], L['mode_vshape']]
            is_gold = False
            
        display_mode = st.radio("Display Mode", modes, index=0, label_visibility="collapsed")
        st.divider()
        st.caption(L['filter_label'])
        all_regimes = ["High Inflation", "Tightening", "Easing", "Crisis"]
        selected_regimes = st.multiselect(L['filter_label'], options=all_regimes, default=[], label_visibility="collapsed", help=L['filter_help'])
        if not selected_regimes: st.caption(f"Status: {L['no_filter']}")
        else: st.caption(f"Status: Filtering {len(selected_regimes)} Regimes")

    df = load_deep_data(selected_asset)
    if df.empty:
        st.error(f"Missing Data File for {selected_asset}. Please check data path.")
    else:
        hist_vectors, hist_indices = precompute_vectors(df)
        with st.sidebar:
            st.divider()
            st.caption(L['time_nav']) 
            years = sorted(df['Date'].dt.year.unique(), reverse=True) 
            selected_year = st.selectbox(L['year_label'], years)
            df_year = df[df['Date'].dt.year == selected_year]
            available_dates = df_year['Date'].dt.strftime('%Y-%m-%d').tolist()
            if not available_dates: st.stop()
            selected_date_str = st.select_slider(L['date_label'], options=available_dates, value=available_dates[-1])
            end_idx_in_df = df[df['Date'] == selected_date_str].index[0]
            
            window, start_idx = 90, max(0, end_idx_in_df - 90 + 1)
            slice_df_ticket = df.iloc[start_idx : end_idx_in_df + 1].copy()
            t_start_date, t_end_date = slice_df_ticket.iloc[0]['Date'].strftime('%Y-%m-%d'), slice_df_ticket.iloc[-1]['Date'].strftime('%Y-%m-%d')
            p_start, p_end = slice_df_ticket.iloc[0]['Close'], slice_df_ticket.iloc[-1]['Close']
            ret_val = (p_end - p_start) / p_start * 100
            ret_color, ret_sign = ("#FF4B4B", "+") if ret_val > 0 else ("#00CC96", "")
            macro_info = get_macro_info(str(selected_year), lang_code)

            with st.container():
                st.markdown('<div class="ticket-container">', unsafe_allow_html=True)
                c_left, c_mid, c_right = st.columns([1, 0.35, 1])
                with c_left: st.markdown(f"""<div class="ticket-block"><div class="t-label">{L["ticket_start"]}</div><div class="t-date u-font-date">{t_start_date}</div><div class="t-price-text u-font-price">${p_start:,.2f}</div></div>""", unsafe_allow_html=True)
                with c_mid: st.markdown(f"""<div class="mid-section"><div class="t-arrow">➜</div><div class="t-ret u-font-ret" style="color:{ret_color}">{ret_sign}{ret_val:.2f}%</div></div>""", unsafe_allow_html=True)
                with c_right: st.markdown(f"""<div class="ticket-block" style="border:1px solid #FFD700;"><div class="t-label">{L["ticket_end"]}</div><div class="t-date u-font-date">{t_end_date}</div><div class="t-price-text u-font-price">${p_end:,.2f}</div></div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f"""<div class="source-tag">{L['lbl_source']}: <span style="color:#888;">Investing.com (Spot)</span></div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="sidebar-card"><div class="sc-header"> {L['sidebar_context_title']}</div><div class="driver-text"><p><span class="driver-label">{L['lbl_event']}:</span> <span style="color:#FFD700">{macro_info.get('event','-')}</span></p><p><span class="driver-label">{L['lbl_rate']}:</span> {macro_info.get('rate','-')}</p><p><span class="driver-label">{L['lbl_geo']}:</span> {macro_info.get('geo','-')}</p><p style="margin-top:8px; border-top:1px solid #444; padding-top:8px; color:#CCC;">{macro_info.get('desc','-')}</p></div></div>""", unsafe_allow_html=True)
        
        st.markdown(f'<h1 style="color: #FFD700;">{L["title"]} - {selected_asset}</h1>', unsafe_allow_html=True)
        st.caption(L['subtitle'])

        if is_gold:
            with st.expander("📅 Seasonal Heatmap (Calendar View)", expanded=True):
                 stats_df = calculate_seasonality(df)
                 fig_season = render_seasonality_chart(stats_df, df, is_dark=is_dark) 
                 st.plotly_chart(fig_season, use_container_width=True)
                 
                 current_month = datetime.datetime.now().month
                 row = stats_df[stats_df['Month_Code'] == current_month].iloc[0]
                 long_term_ref = {1:1.85, 2:0.25, 3:-0.3, 4:0.45, 5:0.15, 6:-0.1, 9:1.65}
                 ref_val = long_term_ref.get(current_month, 0)
                 ref_text = f"(vs 50yr Avg: {ref_val:+.1f}%)"
                 st.caption(f"💡 **TrueFin Insight**: Historically, **{row['Month']}** has an average return of **{row['Avg_Return']:.2f}%** {ref_text} with a win rate of **{row['Win_Rate']:.1f}%**.")

        if display_mode == L['mode_pattern']:
            start_idx = max(0, end_idx_in_df - 89)
            slice_df = df.iloc[start_idx : end_idx_in_df + 1].copy()
            current_prices = slice_df['Close'].values
            current_dates = slice_df['Date'].dt.strftime('%Y-%m-%d').values
            top3 = []
            if len(current_prices) > 10:
                current_vec = current_prices / current_prices[0]
                if len(current_vec) != 90:
                    x_old, x_new = np.linspace(0, 1, len(current_vec)), np.linspace(0, 1, 90)
                    current_vec_90 = np.interp(x_new, x_old, current_vec)
                else: current_vec_90 = current_vec
                scores = []
                for i, h_vec in enumerate(hist_vectors):
                    if abs(hist_indices[i] - start_idx) < 180: continue
                    if selected_regimes:
                        h_idx, h_year = hist_indices[i], df.iloc[hist_indices[i]]['Date'].year
                        if not any(tag in get_macro_tags(h_year) for tag in selected_regimes): continue
                    dist = np.linalg.norm(current_vec_90 - h_vec)
                    scores.append((dist, hist_indices[i]))
                if not scores and selected_regimes: st.warning(f"No history found matching filters: {selected_regimes}.")
                else: scores.sort(key=lambda x: x[0]); top3_indices = scores[:3]
                
                for dist, idx in top3_indices if scores else []:
                    full_len = 180 
                    available_len = min(full_len, len(df) - idx)
                    h_slice_full = df.iloc[idx : idx + available_len]
                    h_prices_full = h_slice_full['Close'].values
                    h_dates_full = h_slice_full['Date'].dt.strftime('%Y-%m-%d').values
                    if available_len >= 90:
                        h_match, match_dates_arr = h_prices_full[:90], h_dates_full[:90]
                        match_s_date, match_e_date = h_slice_full.iloc[0]['Date'].strftime('%Y-%m-%d'), h_slice_full.iloc[89]['Date'].strftime('%Y-%m-%d')
                        match_s_price, match_e_price = h_match[0], h_match[-1]
                        match_ret = (match_e_price - match_s_price) / match_s_price * 100
                    else:
                        h_match, match_dates_arr = h_prices_full, h_dates_full
                        match_s_date, match_e_date = h_slice_full.iloc[0]['Date'].strftime('%Y-%m-%d'), h_slice_full.iloc[-1]['Date'].strftime('%Y-%m-%d')
                        match_s_price, match_e_price, match_ret = h_match[0], h_match[-1], 0.0
                    h_proj, proj_dates_arr = np.array([]), np.array([])
                    proj_s_date, proj_e_date, proj_ret, proj_s_price, proj_e_price = "-", "-", 0.0, 0, 0
                    if available_len > 90:
                        h_proj, proj_dates_arr = h_prices_full[90:], h_dates_full[90:]
                        proj_s_date, proj_e_date = match_e_date, h_slice_full.iloc[-1]['Date'].strftime('%Y-%m-%d')
                        proj_s_price, proj_e_price = h_proj[0], h_proj[-1]
                        proj_ret = (proj_e_price - proj_s_price) / proj_s_price * 100
                    raw_match, raw_proj = (h_prices_full[:90], h_prices_full[90:] if available_len > 90 else []) if available_len >= 90 else (h_prices_full, [])
                    top3.append({"score": dist, "full_data": h_prices_full / h_prices_full[0], "match_len": len(h_match), "proj_len": len(h_proj), "match_dates": match_dates_arr, "proj_dates": proj_dates_arr, "raw_match": raw_match, "raw_proj": raw_proj, "match_info": {"s_date": match_s_date, "e_date": match_e_date, "ret": match_ret, "s_price": match_s_price, "e_price": match_e_price}, "proj_info": {"s_date": proj_s_date, "e_date": proj_e_date, "ret": proj_ret, "s_price": proj_s_price, "e_price": proj_e_price}, "start_date": match_s_date})

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.75, 0.25], specs=[[{"secondary_y": False}], [{"secondary_y": True}]])
            c_list, w_list = ['#5DADE2', '#81C784', '#E0E0E0'], [2.5, 2.5, 2.5]
            if top3:
                for i, m in reversed(list(enumerate(top3))):
                    if not st.session_state[f"show_rank_{i}"]: continue
                    full_projected, match_len = m['full_data'] * p_start, m['match_len']
                    match_data = full_projected[:match_len]
                    trace_name, current_color = f"{L['legend_match']} {i+1} ({m['start_date'][:4]})", c_list[i]
                    custom_data_match = np.stack((m['match_dates'], m['raw_match']), axis=-1)
                    fig.add_trace(go.Scatter(x=list(range(match_len)), y=match_data, mode='lines', name=f"{trace_name} (Match)", line=dict(color=current_color, width=w_list[i], dash='dot'), customdata=custom_data_match, hovertemplate=f"<b>{L['tooltip_date']}</b>: %{{customdata[0]}}<br><b>{L['tooltip_price']}</b>: $%{{customdata[1]:.2f}}<extra></extra>", hoverlabel=dict(bordercolor=current_color, font=dict(family="Roboto Mono, monospace")), showlegend=True, legendrank=i+3), row=1, col=1)
                    if m['proj_len'] > 0:
                        proj_data = full_projected[match_len:]
                        x_proj_plot, y_proj_plot = list(range(match_len - 1, match_len + m['proj_len'])), np.concatenate(([match_data[-1]], proj_data))
                        custom_data_proj = np.stack((np.concatenate(([m['match_dates'][-1]], m['proj_dates'])), np.concatenate(([m['raw_match'][-1]], m['raw_proj']))), axis=-1)
                        fig.add_trace(go.Scatter(x=x_proj_plot, y=y_proj_plot, mode='lines', name=f"{trace_name} (Forecast)", line=dict(color=current_color, width=w_list[i], dash='dot'), customdata=custom_data_proj, hovertemplate=f"<b>{L['tooltip_date']}</b>: %{{customdata[0]}}<br><b>{L['tooltip_price']}</b>: $%{{customdata[1]:.2f}}<extra></extra>", hoverlabel=dict(bordercolor=current_color, font=dict(family="Roboto Mono, monospace")), showlegend=False, legendrank=i+3), row=1, col=1)

            available_future = len(df) - 1 - end_idx_in_df
            if available_future > 0:
                future_limit = 90
                future_slice = df.iloc[end_idx_in_df : end_idx_in_df + min(future_limit, available_future) + 1]
                real_future_prices, real_future_dates = future_slice['Close'].values, future_slice['Date'].dt.strftime('%Y-%m-%d').values
                x_real_future = list(range(len(current_prices) - 1, len(current_prices) - 1 + len(real_future_prices)))
                custom_data_true = np.stack((real_future_dates, real_future_prices), axis=-1)
                fig.add_trace(go.Scatter(x=x_real_future, y=real_future_prices, mode='lines', name=L['legend_real_future'], line=dict(color='#FFD700', width=3), customdata=custom_data_true, hovertemplate=f"<b>{L['tooltip_date']}</b>: %{{customdata[0]}}<br><b>{L['tooltip_price']}</b>: $%{{customdata[1]:.2f}}<extra></extra>", hoverlabel=dict(bordercolor='#FFD700', font=dict(family="Roboto Mono, monospace")), legendrank=2, opacity=0.8), row=1, col=1)

            custom_data_curr = np.stack((current_dates, current_prices), axis=-1)
            if 'Open' in slice_df.columns and 'High' in slice_df.columns and 'Low' in slice_df.columns:
                fig.add_trace(go.Candlestick(x=list(range(len(slice_df))), open=slice_df['Open'], high=slice_df['High'], low=slice_df['Low'], close=slice_df['Close'], name=L['legend_current'], increasing_line_color='#00CC96', decreasing_line_color='#FF4B4B', customdata=custom_data_curr, hoverlabel=dict(bordercolor='#FFD700', font=dict(family="Roboto Mono, monospace")), legendrank=1), row=1, col=1)
                fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
            else:
                fig.add_trace(go.Scatter(y=current_prices, mode='lines', name=L['legend_current'], line=dict(color='#FFD700', width=4), customdata=custom_data_curr, hovertemplate=f"<b>{L['tooltip_date']}</b>: %{{customdata[0]}}<br><b>{L['tooltip_price']}</b>: $%{{customdata[1]:.2f}}<extra></extra>", hoverlabel=dict(bordercolor='#FFD700', font=dict(family="Roboto Mono, monospace")), legendrank=1), row=1, col=1)
            
            current_len = len(current_prices)
            fig.add_vrect(x0=0, x1=current_len-1, fillcolor="#0E1117", opacity=1, layer="below", line_width=0, row=1, col=1)
            fig.add_vrect(x0=current_len-1, x1=current_len + 90, fillcolor="rgba(30, 35, 50, 0.5)", opacity=1, layer="below", line_width=0, row=1, col=1)
            fig.add_vline(x=current_len-1, line_width=1, line_dash="dash", line_color="#888", row=1, col=1)
            fig.add_annotation(x=current_len-1, y=min(current_prices), text=slice_df.iloc[-1]['Date'].strftime('%Y-%m-%d'), showarrow=False, yshift=-30, bgcolor="#0E1117", opacity=0.9, font=dict(color="#FFD700", size=14, family="Roboto Mono, monospace", weight="bold"), row=1, col=1)
            
            if "Net_Purchase_Tonnes" in df.columns and (df['Net_Purchase_Tonnes'] != 0).any():
                slice_df['YearMonth'] = slice_df['Date'].dt.to_period('M')
                wgc_view = slice_df.drop_duplicates(subset=['YearMonth'], keep='first')
                wgc_view = wgc_view[wgc_view['Net_Purchase_Tonnes'] != 0] 
                wgc_indices = np.searchsorted(slice_df['Date'], wgc_view['Date'])
                fig.add_trace(go.Bar(x=wgc_indices, y=wgc_view['Net_Purchase_Tonnes'], name=L['fund_legend_wgc'], marker_color='#FFD700', opacity=0.6, customdata=np.stack((wgc_view['Date'].dt.strftime('%Y-%m-%d'), wgc_view['Net_Purchase_Tonnes']), axis=-1), hovertemplate="<b>📅 %{customdata[0]}</b><br>🏦 Central Bank Net: <b>%{y:.1f} Tonnes</b><extra></extra>"), row=2, col=1, secondary_y=True)

            if "Money_Manager_Net" in df.columns and (df['Money_Manager_Net'] != 0).any():
                cftc_curr = slice_df.get('Money_Manager_Net', pd.Series([0]*len(slice_df))).values
                dates_curr = slice_df['Date'].dt.strftime('%Y-%m-%d').values
                custom_cftc = np.stack((dates_curr, cftc_curr), axis=-1)
                fig.add_trace(go.Scatter(x=np.arange(len(cftc_curr)), y=cftc_curr, fill='tozeroy', mode='lines', name=L['fund_legend_cftc'], line=dict(width=1.5, color='#00E5FF'), fillcolor='rgba(0, 229, 255, 0.1)', customdata=custom_cftc, hovertemplate="<b>📅 %{customdata[0]}</b><br>💼 Managed Money Net: <b>%{y:,.0f} Contracts</b><extra></extra>"), row=2, col=1)

            last_date_obj = pd.to_datetime(current_dates[-1])
            future_dates_label = pd.bdate_range(start=last_date_obj, periods=91)[1:].strftime('%b %d').tolist()
            current_dates_formatted = pd.to_datetime(current_dates).strftime('%b %d').tolist()
            all_x_labels = current_dates_formatted + future_dates_label
            tick_vals = list(range(0, len(all_x_labels), 10))
            tick_text = [all_x_labels[i] for i in tick_vals]

            fig.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=600, margin=dict(l=0,r=0,t=90,b=20), legend=dict(orientation="h", y=1.15, x=1, xanchor='right', font=dict(color="white")), hoverlabel=dict(bgcolor="#1E1E1E", font_size=13, font_color="#FFFFFF", font_family="Roboto Mono, monospace"))
            axis_title_with_year = f"{L['axis_title']} ({selected_year})"
            fig.update_yaxes(title=dict(text=L['axis_y_title'], font=dict(color="#FFFFFF", size=12)), gridcolor='#333', tickprefix="$", row=1, col=1)
            fig.update_xaxes(showgrid=False, linecolor='#333', tickmode='array', tickvals=tick_vals, ticktext=tick_text, row=1, col=1)
            fig.update_xaxes(title=dict(text=axis_title_with_year, font=dict(color="#FFFFFF", size=12)), showgrid=False, linecolor='#333', tickmode='array', tickvals=tick_vals, ticktext=tick_text, row=2, col=1)
            fig.update_yaxes(title=dict(text=L['axis_cftc'], font=dict(color="#00E5FF", size=11)), gridcolor='#333', showgrid=False, row=2, col=1, secondary_y=False)
            fig.update_yaxes(title=dict(text=L['axis_wgc'], font=dict(color="#FFD700", size=11)), showgrid=False, row=2, col=1, secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
            
            if top3:
                cols = st.columns(3)
                for i, m in enumerate(top3):
                    sim_score = int(max(0, 100 - m['score']*8))
                    yr = m['start_date'][:4]
                    macro = get_macro_info(yr, lang_code)
                    mi, pi = m['match_info'], m['proj_info']
                    m_ret_color = '#FF4B4B' if mi['ret'] > 0 else '#00CC96'
                    p_ret_color = '#FF4B4B' if pi['ret'] > 0 else '#00CC96'
                    if pi['ret'] == 0: p_ret_color = '#888'
                    m_ret_str, p_ret_str = f"{'+' if mi['ret']>0 else ''}{mi['ret']:.1f}%", f"{'+' if pi['ret']>0 else ''}{pi['ret']:.1f}%" if m['proj_len'] > 0 else "N/A"
                    rank_color = c_list[i]
                    with cols[i]:
                        st.markdown(render_header(L['match_no'], i, sim_score), unsafe_allow_html=True)
                        st.toggle(f"{L['show_line']}", key=f"show_rank_{i}")
                        st.markdown(render_grid(L, mi, pi, m_ret_color, m_ret_str, p_ret_color, p_ret_str, rank_color), unsafe_allow_html=True)
                        st.markdown(render_macro(L, macro), unsafe_allow_html=True)

        elif display_mode == L.get('mode_bull'): 
            b1_start, b1_end, b2_start, b2_end, b3_start = '1971-01-01', '1980-01-21', '1999-07-20', '2011-09-05', '2018-08-16'
            df_b1, df_b2, df_b3 = align_to_daily(df[(df['Date'] >= b1_start) & (df['Date'] <= b1_end)].copy()), align_to_daily(df[(df['Date'] >= b2_start) & (df['Date'] <= b2_end)].copy()), align_to_daily(df[df['Date'] >= b3_start].copy())
            fig_bull = go.Figure()
            if not df_b3.empty:
                base_price = df_b3.iloc[0]['Close']
                if not df_b1.empty:
                    df_b1['Rebased'] = df_b1['Close'] * (base_price / df_b1.iloc[0]['Close'])
                    fig_bull.add_trace(go.Scatter(x=np.arange(len(df_b1)), y=df_b1['Rebased'], mode='lines', name=f"Bull 1 ({b1_start[:4]}-{b1_end[:4]})", line=dict(color='#26C6DA', width=1.5)))
                if not df_b2.empty:
                    df_b2['Rebased'] = df_b2['Close'] * (base_price / df_b2.iloc[0]['Close'])
                    fig_bull.add_trace(go.Scatter(x=np.arange(len(df_b2)), y=df_b2['Rebased'], mode='lines', name=f"Bull 2 ({b2_start[:4]}-{b2_end[:4]})", line=dict(color='#AB47BC', width=1.5)))
                fig_bull.add_trace(go.Scatter(x=np.arange(len(df_b3)), y=df_b3['Close'], mode='lines', name=f"Bull 3 ({b3_start[:4]}-Present)", line=dict(color='#66BB6A', width=2.5)))
                chart_title = L['chart_bull_title'].format(year=b3_start[:4])
                fig_bull.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=600, title=dict(text=chart_title, font=dict(color="white")), margin=dict(l=50,r=50,t=40,b=20), legend=dict(orientation="h", y=1.02, x=0, xanchor='left', font=dict(color="white")), hoverlabel=dict(bgcolor="#1E1E1E", font_size=13, font_color="#FFFFFF", font_family="Roboto Mono, monospace"), yaxis=dict(title=dict(text=L['axis_bull_y'], font=dict(color="#FFFFFF", size=12)), gridcolor='#333', tickprefix="$"))
                fig_bull.update_xaxes(title=dict(text=L['axis_bull_x'], font=dict(color="#FFFFFF", size=12)), showgrid=False, linecolor='#333')
                st.plotly_chart(fig_bull, use_container_width=True)

        elif display_mode == L.get('mode_vshape'):
            crashes = [{"name": "1987 Black Monday", "bottom": "1987-10-19", "color": "#AB47BC"}, {"name": "2008 GFC", "bottom": "2009-03-09", "color": "#26C6DA"}, {"name": "2020 Covid", "bottom": "2020-03-23", "color": "#66BB6A"}, {"name": "2022 Inflation", "bottom": "2022-10-12", "color": "#FF7043"}]
            fig_v, look_ahead = go.Figure(), 250 
            for crash in crashes:
                bottom_date = crash['bottom']
                mask = df['Date'] == bottom_date
                if mask.any():
                    idx_bottom = df.index[mask][0]
                    slice_df = df.iloc[idx_bottom : idx_bottom + look_ahead].copy() if idx_bottom + look_ahead < len(df) else df.iloc[idx_bottom:].copy()
                    if not slice_df.empty:
                        base_price = slice_df.iloc[0]['Close']
                        slice_df['PctChange'] = ((slice_df['Close'] - base_price) / base_price) * 100
                        fig_v.add_trace(go.Scatter(x=np.arange(len(slice_df)), y=slice_df['PctChange'], mode='lines', name=f"{crash['name']} ({bottom_date})", line=dict(color=crash['color'], width=2), hovertemplate="Day: %{x}<br>Return: %{y:.1f}%<extra></extra>"))
            fig_v.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=600, title=dict(text=L.get('chart_v_title', "Historical V-Shape Recoveries"), font=dict(color="white")), margin=dict(l=50, r=50, t=50, b=20), legend=dict(orientation="h", y=1.02, x=0, xanchor='left', font=dict(color="white")), hoverlabel=dict(bgcolor="#1E1E1E", font_size=13, font_color="#FFFFFF", font_family="Roboto Mono, monospace"))
            fig_v.update_xaxes(title=dict(text=L['axis_v_x'], font=dict(color="#FFFFFF", size=12)), showgrid=False, linecolor='#333')
            fig_v.update_yaxes(title=dict(text=L['axis_v_y'], font=dict(color="#FFFFFF", size=12)), gridcolor='#333', tickprefix="+", ticksuffix="%")
            fig_v.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_v, use_container_width=True)
            st.caption("Comparison of market recoveries following major historical bottoms. All prices are normalized to 0% at the day of the low.")