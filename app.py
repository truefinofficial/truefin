"""
TrueFin v3.0 — Monthly Performance Intelligence Platform
更新内容：
  - 响应式布局修复（大屏幕不再拉扁）
  - 重命名 "Seasonal" → "Monthly"
  - 12宫格颜色升级为6档渐变
  - 新增黄金宏观时间段选择器（牛市/熊市筛选）
  - 时间段选择器联动12宫格数据重计算
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import warnings
import os
import base64

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="TrueFin | 月次金融インテリジェンス",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
ASSETS = {
    "gold":   {"label_jp": "ゴールド",  "label_en": "Gold",    "color": "#F5C842", "symbol": "XAU/USD"},
    "sp500":  {"label_jp": "S&P500",   "label_en": "S&P 500", "color": "#4ECDC4", "symbol": "SPX"},
    "usdjpy": {"label_jp": "ドル円",    "label_en": "USD/JPY", "color": "#FF6B6B", "symbol": "USD/JPY"},
    "eurjpy": {"label_jp": "ユーロ円",  "label_en": "EUR/JPY", "color": "#A8DADC", "symbol": "EUR/JPY"},
}

MONTHS_JP = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
MONTHS_EN = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# 美联储议息会议月份
FOMC_MONTHS = {1, 3, 5, 6, 7, 9, 10, 12}

# ─────────────────────────────────────────────
# 黄金历史牛熊市时间段定义
# 数据来源：创始人研究 + 黄金历史价格
# ─────────────────────────────────────────────
GOLD_PERIODS = {
    "all": {
        "jp":    "全期間（1970〜現在）",
        "en":    "All History (1970–present)",
        "desc_jp": "56年間の月次データ全体平均",
        "desc_en": "Full 56-year monthly average",
        "ranges": [("1970-01-01", "2099-12-31")],
        "badge_color": "#555577",
        "badge_bg":    "#2A2A3A",
    },
    "bull1": {
        "jp":    "第1次強気相場（1971–1980）",
        "en":    "Bull Market I (1971–1980)",
        "desc_jp": "ブレトンウッズ崩壊・石油危機・インフレ急騰",
        "desc_en": "Bretton Woods collapse · Oil crisis · Inflation surge",
        "ranges": [("1971-01-01", "1980-01-21")],
        "badge_color": "#FF8A80",
        "badge_bg":    "#3D0A0A",
    },
    "bull2": {
        "jp":    "第2次強気相場（1999–2011）",
        "en":    "Bull Market II (1999–2011)",
        "desc_jp": "ITバブル崩壊・ドル安・リーマンショック",
        "desc_en": "Dotcom bust · USD weakness · GFC",
        "ranges": [("1999-07-20", "2011-09-05")],
        "badge_color": "#FF8A80",
        "badge_bg":    "#3D0A0A",
    },
    "bull3": {
        "jp":    "第3次強気相場（2018〜現在）",
        "en":    "Bull Market III (2018–present)",
        "desc_jp": "米中摩擦・コロナ・地政学リスク・利上げ",
        "desc_en": "US-China trade war · COVID · Rate hikes",
        "ranges": [("2018-08-16", "2099-12-31")],
        "badge_color": "#FF8A80",
        "badge_bg":    "#3D0A0A",
    },
    "bear": {
        "jp":    "歴史的弱気相場",
        "en":    "Historical Bear Markets",
        "desc_jp": "牛市以外の期間（1980–1999、2011–2018）",
        "desc_en": "Non-bull periods (1980–1999, 2011–2018)",
        "ranges": [
            ("1970-01-01", "1970-12-31"),      # 第1次牛市前
            ("1980-01-22", "1999-07-19"),       # 第1次牛市后 → 第2次前
            ("2011-09-06", "2018-08-15"),       # 第2次牛市后 → 第3次前
        ],
        "badge_color": "#90CAF9",
        "badge_bg":    "#050D1A",
    },
}

# ─────────────────────────────────────────────
# LOGO LOADER
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_logo_b64() -> str:
    candidate_paths = [
        "assets/TrueFin_logo.jpg",
        "assets/truefin_logo.jpg",
        "assets/logo.jpg",
        "TrueFin_logo.jpg",
        "logo.jpg",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "lang":          "jp",
        "theme":         "dark",
        "asset":         "gold",
        "view":          "main",
        "detail_month":  None,
        "detail_asset":  None,
        "show_about":    False,
        "show_contact":  False,
        "gold_periods":  ["all"],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

L    = st.session_state["lang"]
DARK = st.session_state["theme"] == "dark"

# ─────────────────────────────────────────────
# THEME COLORS
# ─────────────────────────────────────────────
if DARK:
    BG     = "#0A0A0F"
    BG2    = "#111118"
    BG3    = "#1A1A24"
    BORDER = "#2A2A38"
    TEXT   = "#E8E8F0"
    TEXT2  = "#8888AA"
    ACCENT = "#F5C842"
else:
    BG     = "#F0F0F8"
    BG2    = "#FFFFFF"
    BG3    = "#E8E8F2"
    BORDER = "#CCCCDD"
    TEXT   = "#111122"
    TEXT2  = "#555566"
    ACCENT = "#C8A000"

# ─────────────────────────────────────────────
# 月份卡片颜色（6档渐变，日本惯例：赤=上昇/青=下落）
# 阈值：±0.5%, ±1.5%, ±3.0%
# ─────────────────────────────────────────────
def get_card_color(avg_ret: float) -> dict:
    """
    6档颜色（深色主题）— 日本惯例：红=上涨，蓝=下跌
    Ultra Bull(>=+3%)  用 #FF1744（亮红） 区别于 Bull+(#C62828 深红）
    """
    if avg_ret >= 3.0:
        return {"bg":"#5C0000","border":"#FF1744","text":"#FF6B6B",
                "badge_bg":"#FF1744","badge_text":"#fff","label":"ULTRA BULL" if L=="en" else "極強気"}
    elif avg_ret >= 1.5:
        return {"bg":"#3D0A0A","border":"#C62828","text":"#FF9A9A",
                "badge_bg":"#C62828","badge_text":"#fff","label":"BULL+" if L=="en" else "強気+"}
    elif avg_ret > 0:
        return {"bg":"#2A1010","border":"#EF5350","text":"#FFCDD2",
                "badge_bg":"#EF5350","badge_text":"#fff","label":"BULL" if L=="en" else "強気"}
    elif avg_ret > -1.5:
        return {"bg":"#0A1828","border":"#42A5F5","text":"#BBDEFB",
                "badge_bg":"#42A5F5","badge_text":"#000","label":"BEAR" if L=="en" else "弱気"}
    elif avg_ret > -3.0:
        return {"bg":"#051020","border":"#1565C0","text":"#90CAF9",
                "badge_bg":"#1565C0","badge_text":"#fff","label":"BEAR-" if L=="en" else "弱気-"}
    else:
        return {"bg":"#020810","border":"#0D47A1","text":"#64B5F6",
                "badge_bg":"#0D47A1","badge_text":"#fff","label":"ULTRA BEAR" if L=="en" else "極弱気"}

def get_card_color_light(avg_ret: float) -> dict:
    if avg_ret >= 3.0:
        return {"bg":"#FFF0F0","border":"#FF1744","text":"#C62828",
                "badge_bg":"#FF1744","badge_text":"#fff","label":"ULTRA BULL" if L=="en" else "極強気"}
    elif avg_ret >= 1.5:
        return {"bg":"#FFEBEE","border":"#C62828","text":"#B71C1C",
                "badge_bg":"#C62828","badge_text":"#fff","label":"BULL+" if L=="en" else "強気+"}
    elif avg_ret > 0:
        return {"bg":"#FFF5F5","border":"#EF9A9A","text":"#C62828",
                "badge_bg":"#EF9A9A","badge_text":"#B71C1C","label":"BULL" if L=="en" else "強気"}
    elif avg_ret > -1.5:
        return {"bg":"#F0F8FF","border":"#90CAF9","text":"#1565C0",
                "badge_bg":"#90CAF9","badge_text":"#0D47A1","label":"BEAR" if L=="en" else "弱気"}
    elif avg_ret > -3.0:
        return {"bg":"#E3F2FD","border":"#1565C0","text":"#0D47A1",
                "badge_bg":"#1565C0","badge_text":"#fff","label":"BEAR-" if L=="en" else "弱気-"}
    else:
        return {"bg":"#E3F2FD","border":"#0D47A1","text":"#0D47A1",
                "badge_bg":"#0D47A1","badge_text":"#fff","label":"ULTRA BEAR" if L=="en" else "極弱気"}

# ─────────────────────────────────────────────
# GLOBAL CSS（含响应式max-width修复）
# ─────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&family=Noto+Sans+JP:wght@300;400;500;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {BG} !important;
        color: {TEXT} !important;
        font-family: 'Noto Sans JP', sans-serif;
    }}
    [data-testid="stSidebar"], [data-testid="stToolbar"],
    header, footer, div[data-testid="stDecoration"] {{ display: none !important; }}

    /* ── 响应式宽度修复：限制最大宽度，防止27寸拉扁 ── */
    .block-container {{
        padding: 0 !important;
        max-width: 1600px !important;   /* 核心修复：限制最大宽度 */
        margin: 0 auto !important;      /* 居中显示 */
        width: 100% !important;
    }}

    ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
    ::-webkit-scrollbar-track {{ background: {BG2}; }}
    ::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 2px; }}

    /* ── Topbar ── */
    .topbar {{
        position: sticky; top: 0; z-index: 999;
        background: {BG2}; border-bottom: 1px solid {BORDER};
        padding: 0 24px; display: flex;
        align-items: center; justify-content: space-between;
        height: 54px;
    }}
    .logo-img {{ height: 32px; width: auto; }}
    .logo-text {{
        font-family: 'Space Mono', monospace;
        font-size: 18px; font-weight: 700; color: {ACCENT}; letter-spacing: 2px;
    }}
    .logo-sub {{
        font-size: 10px; color: {TEXT2};
        font-family: 'Space Mono', monospace;
        margin-left: 8px; letter-spacing: 1px;
    }}

    /* ── Topbar Contact Us ── */
    .topbar-contact {{
        font-size: 11px; color: {TEXT2};
        font-family: 'Space Mono', monospace;
        cursor: help; letter-spacing: 1px;
        border-bottom: 1px dashed {BORDER};
        padding-bottom: 1px;
    }}
    .topbar-contact:hover {{ color: {ACCENT}; }}

    /* ── Ticker ── */
    .ticker-bar {{
        background: {BG3}; border-bottom: 1px solid {BORDER};
        padding: 7px 24px; display: flex; gap: 28px;
        overflow-x: auto; white-space: nowrap;
    }}
    .ticker-item {{ display: flex; flex-direction: column; gap: 1px; min-width: 80px; }}
    .ticker-symbol {{ font-family: 'Space Mono', monospace; font-size: 9px; color: {TEXT2}; letter-spacing: 1px; }}
    .ticker-price {{ font-family: 'Space Mono', monospace; font-size: 13px; font-weight: 700; color: {TEXT}; }}
    .ticker-change.pos {{ color: #FF6B6B; font-size: 10px; }}
    .ticker-change.neg {{ color: #64B5F6; font-size: 10px; }}

    /* ── Section header ── */
    .section-header {{
        padding: 16px 24px 10px;
        display: flex; justify-content: space-between; align-items: flex-end;
    }}
    .section-title {{
        font-family: 'Syne', sans-serif;
        font-size: 20px; font-weight: 800; color: {TEXT}; letter-spacing: -0.5px;
    }}
    .section-subtitle {{ font-size: 11px; color: {TEXT2}; margin-top: 3px; }}

    /* ── 宏观事件选择器 ── */
    .period-selector {{
        margin: 0 24px 4px;
        background: {BG2};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 16px 20px;
    }}
    .period-selector-title {{
        font-family: 'Space Mono', monospace;
        font-size: 9px; color: {TEXT2};
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 12px;
        display: flex; align-items: center; gap: 8px;
    }}

    /* ── ? 悬浮说明tooltip ── */
    .help-tooltip {{
        display: inline-flex; align-items: center; justify-content: center;
        width: 15px; height: 15px; border-radius: 50%;
        background: {BORDER}; color: {TEXT2};
        font-size: 9px; font-weight: 700; cursor: help;
        font-family: 'Space Mono', monospace;
        position: relative;
        flex-shrink: 0;
    }}
    .help-tooltip::after {{
        content: attr(data-tip);
        position: absolute; bottom: 22px; left: 0;
        background: {BG2}; border: 1px solid {BORDER};
        color: {TEXT}; font-size: 11px; line-height: 1.6;
        padding: 10px 14px; border-radius: 8px;
        width: 320px; white-space: normal;
        font-family: 'Noto Sans JP', sans-serif;
        letter-spacing: 0; text-transform: none;
        font-weight: 400;
        pointer-events: none; opacity: 0;
        transition: opacity 0.2s;
        z-index: 999;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }}
    .help-tooltip:hover::after {{ opacity: 1; }}
    .period-chips {{
        display: flex; gap: 8px; flex-wrap: wrap;
    }}
    .period-chip {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 6px 14px; border-radius: 20px;
        border: 1px solid {BORDER};
        background: {BG3}; color: {TEXT2};
        font-size: 11px; cursor: pointer;
        transition: all 0.18s;
        font-family: 'Noto Sans JP', sans-serif;
    }}
    .period-chip.active {{
        border-color: #C62828; background: #3D0A0A; color: #FF8A80;
    }}
    .period-chip.active.bear {{
        border-color: #1565C0; background: #051020; color: #90CAF9;
    }}
    .period-desc {{
        font-size: 10px; color: {TEXT2}; margin-top: 10px;
        padding-top: 10px; border-top: 1px solid {BORDER};
        font-style: italic;
    }}

    /* ── Month Card（底部无圆角，通过隔离层与Details按钮分开）── */
    .month-card-v2 {{
        border-radius: 14px;
        border: 2px solid var(--c-border, {BORDER});
        background: var(--c-bg, {BG2});
        padding: 18px 16px 14px;
        position: relative;
        transition: all 0.2s;
        cursor: pointer;
        overflow: hidden;
        margin-bottom: 0;
    }}
    .month-card-v2::before {{
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 4px;
        background: var(--c-border, {BORDER});
        border-radius: 14px 14px 0 0;
    }}
    /* 卡片与Details按钮之间的透明间隙层 */
    .mc-gap {{
        height: 6px;
        background: {BG};
    }}
    .mc-month-label {{
        font-family: 'Space Mono', monospace;
        font-size: 11px; color: {TEXT2};
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 6px;
    }}
    .mc-return {{
        font-family: 'Space Mono', monospace;
        font-size: 34px; font-weight: 700;
        line-height: 1.1; margin-bottom: 8px;
    }}
    .mc-badge {{
        display: inline-block;
        font-size: 10px; padding: 3px 9px; border-radius: 20px;
        font-weight: 700; letter-spacing: 1px;
        background: var(--c-badge-bg, {BORDER});
        color: var(--c-badge-text, {TEXT2});
        margin-bottom: 8px;
    }}
    .mc-stats-row {{
        display: flex; gap: 14px; margin-top: 6px; flex-wrap: wrap;
    }}
    .mc-stat {{ display: flex; flex-direction: column; gap: 2px; }}
    .mc-stat-label {{
        font-size: 9px; color: {TEXT2};
        letter-spacing: 1px; text-transform: uppercase;
    }}
    .mc-stat-value {{
        font-family: 'Space Mono', monospace;
        font-size: 14px; font-weight: 700; color: {TEXT};
    }}

    /* ── 双色WIN/LOSS 分割条 ── */
    .mc-win-section {{ margin-top: 10px; }}
    .mc-win-labels {{
        display: flex; justify-content: space-between;
        font-size: 9px; margin-bottom: 4px;
        font-family: 'Space Mono', monospace; letter-spacing: 0.5px;
    }}
    .mc-win-label-win {{ color: #FF8A80; font-weight: 700; }}
    .mc-win-label-lose {{ color: #90CAF9; font-weight: 700; }}
    .mc-win-dual-bar {{
        height: 5px; border-radius: 3px;
        overflow: hidden; display: flex;
    }}
    .mc-win-bar-fill {{
        height: 100%; background: #C62828;
        border-radius: 3px 0 0 3px;
    }}
    .mc-loss-bar-fill {{
        height: 100%; background: #1565C0;
        border-radius: 0 3px 3px 0;
    }}

    .mc-fomc-tag {{
        position: absolute; top: 10px; right: 10px;
        font-size: 8px; padding: 2px 6px; border-radius: 8px;
        background: rgba(255,193,7,0.15); color: #FFC107;
        border: 1px solid rgba(255,193,7,0.3);
        font-weight: 700; letter-spacing: 0.5px;
    }}
    .mc-current-tag {{
        margin-top: 6px; display: block;
        font-size: 10px; padding: 2px 7px; border-radius: 6px;
        background: rgba(255,255,255,0.06); color: {TEXT2};
        border: 1px solid {BORDER}; font-weight: 700;
        text-align: right; width: fit-content; margin-left: auto;
    }}

    /* ── Details按钮（独立卡片，与上方宫格有视觉间隙）── */
    .mc-details-btn .stButton > button {{
        border-radius: 10px !important;
        border: 1px solid {BORDER} !important;
        background: {BG2} !important;
        color: {TEXT2} !important;
        font-size: 11px !important;
        padding: 8px 8px !important;
        letter-spacing: 1px;
        font-family: 'Space Mono', monospace !important;
        transition: all 0.2s !important;
        width: 100% !important;
    }}
    .mc-details-btn .stButton > button:hover {{
        color: {ACCENT} !important;
        border-color: {ACCENT} !important;
        background: {BG3} !important;
    }}

    /* ── Buttons ── */
    .stButton > button {{
        background: {BG3} !important;
        border: 1px solid {BORDER} !important;
        color: {TEXT} !important;
        border-radius: 8px !important;
        font-family: 'Noto Sans JP', sans-serif !important;
        font-size: 12px !important;
        padding: 6px 12px !important;
        transition: all 0.2s !important;
    }}
    .stButton > button:hover {{
        border-color: {ACCENT} !important;
        color: {ACCENT} !important;
    }}

    /* ── Asset selector active glow ── */
    .asset-active-gold   .stButton > button {{ border-color: #F5C842 !important; box-shadow: 0 0 14px rgba(245,200,66,0.45) !important; color: #F5C842 !important; background: rgba(245,200,66,0.08) !important; font-weight: 700 !important; }}
    .asset-active-sp500  .stButton > button {{ border-color: #4ECDC4 !important; box-shadow: 0 0 14px rgba(78,205,196,0.45)  !important; color: #4ECDC4 !important; background: rgba(78,205,196,0.08) !important; font-weight: 700 !important; }}
    .asset-active-usdjpy .stButton > button {{ border-color: #FF6B6B !important; box-shadow: 0 0 14px rgba(255,107,107,0.45) !important; color: #FF6B6B !important; background: rgba(255,107,107,0.08) !important; font-weight: 700 !important; }}
    .asset-active-eurjpy .stButton > button {{ border-color: #A8DADC !important; box-shadow: 0 0 14px rgba(168,218,220,0.45) !important; color: #A8DADC !important; background: rgba(168,218,220,0.08) !important; font-weight: 700 !important; }}
    /* 所有资产按钮强制等高、顶部对齐 */
    div[data-testid="column"] {{ align-items: flex-start !important; }}
    .stMultiSelect > div > div {{
        background: {BG2} !important;
        border-color: {BORDER} !important;
        font-size: 12px !important;
    }}

    /* ── About ── */
    .about-container {{
        background: {BG2}; border: 1px solid {BORDER};
        border-radius: 16px; padding: 40px 48px;
        max-width: 740px; margin: 0 auto;
        line-height: 1.9;
    }}
    .about-title {{
        font-family: 'Syne', sans-serif;
        font-size: 22px; font-weight: 800;
        color: {ACCENT}; margin-bottom: 8px;
    }}
    .about-subtitle {{
        font-size: 13px; color: {TEXT2}; margin-bottom: 32px;
        border-bottom: 1px solid {BORDER}; padding-bottom: 16px;
    }}
    .about-body {{ font-size: 14px; color: {TEXT}; }}
    .about-body p {{ margin-bottom: 16px; }}
    .about-body .highlight {{
        background: rgba(245,200,66,0.1);
        border-left: 3px solid {ACCENT};
        padding: 12px 16px; border-radius: 0 8px 8px 0;
        margin: 20px 0; font-style: italic; color: {TEXT};
    }}
    .about-sig {{
        margin-top: 32px; font-size: 13px;
        color: {TEXT2}; text-align: right;
    }}

    /* ── Detail view ── */
    .split-panel-title {{
        font-family: 'Space Mono', monospace;
        font-size: 10px; color: {TEXT2}; letter-spacing: 2px;
        text-transform: uppercase; margin-bottom: 14px;
        padding-bottom: 8px; border-bottom: 1px solid {BORDER};
    }}
    .hist-card {{
        background: {BG2}; border: 1px solid {BORDER};
        border-radius: 10px; padding: 14px; margin-bottom: 10px;
    }}
    .hist-year {{
        font-family: 'Space Mono', monospace;
        font-size: 20px; font-weight: 700; color: {TEXT};
    }}
    /* ── 三维标签行 ── */
    .macro-tags {{
        display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;
    }}
    /* Fed利率标签 */
    .tag-fed {{
        display: inline-flex; align-items: center; gap: 4px;
        padding: 3px 9px; border-radius: 6px;
        background: rgba(255,193,7,0.1); border: 1px solid rgba(255,193,7,0.35);
        font-family: 'Space Mono', monospace; font-size: 10px; font-weight: 700;
        color: #FFC107; letter-spacing: 0.5px;
    }}
    .tag-fed-label {{
        font-size: 8px; color: rgba(255,193,7,0.6); font-weight: 400; margin-right: 2px;
    }}
    /* DXY货币方向标签 */
    .tag-dxy-weak {{
        display: inline-flex; align-items: center; gap: 4px;
        padding: 3px 9px; border-radius: 6px;
        background: rgba(78,205,196,0.1); border: 1px solid rgba(78,205,196,0.35);
        font-family: 'Space Mono', monospace; font-size: 10px; font-weight: 700;
        color: #4ECDC4; letter-spacing: 0.5px;
    }}
    .tag-dxy-strong {{
        display: inline-flex; align-items: center; gap: 4px;
        padding: 3px 9px; border-radius: 6px;
        background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.35);
        font-family: 'Space Mono', monospace; font-size: 10px; font-weight: 700;
        color: #FF6B6B; letter-spacing: 0.5px;
    }}
    .tag-dxy-stable {{
        display: inline-flex; align-items: center; gap: 4px;
        padding: 3px 9px; border-radius: 6px;
        background: rgba(136,136,170,0.1); border: 1px solid rgba(136,136,170,0.3);
        font-family: 'Space Mono', monospace; font-size: 10px; font-weight: 700;
        color: {TEXT2}; letter-spacing: 0.5px;
    }}
    /* 地缘事件标签（带tooltip）*/
    .tag-geo {{
        display: inline-flex; align-items: center; gap: 4px;
        padding: 3px 9px; border-radius: 6px;
        background: rgba(168,218,220,0.1); border: 1px solid rgba(168,218,220,0.35);
        font-family: 'Noto Sans JP', sans-serif; font-size: 10px;
        color: #A8DADC; cursor: help; position: relative;
    }}
    .tag-geo::after {{
        content: attr(data-geo);
        position: absolute; bottom: 28px; left: 0;
        background: {BG2}; border: 1px solid {BORDER};
        color: {TEXT}; font-size: 11px; line-height: 1.7;
        padding: 10px 14px; border-radius: 8px;
        width: 300px; white-space: normal;
        font-family: 'Noto Sans JP', sans-serif;
        pointer-events: none; opacity: 0;
        transition: opacity 0.2s;
        z-index: 9999;
        box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    }}
    .tag-geo:hover::after {{ opacity: 1; }}
    .tag-geo-dot {{
        width: 6px; height: 6px; border-radius: 50%;
        background: #A8DADC; flex-shrink: 0;
    }}

    /* ── 响应式 ── */
    @media (max-width: 1024px) {{
        .mc-return {{ font-size: 24px; }}
        .block-container {{ max-width: 100% !important; }}
    }}
    @media (max-width: 768px) {{
        .mc-return {{ font-size: 20px; }}
        .period-selector {{ margin: 0 8px 4px; }}
    }}
    </style>
    """, unsafe_allow_html=True)

inject_css()

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_asset_data(asset_key: str) -> pd.DataFrame:
    """加载日线收盘价数据（仅date+close）"""
    file_map = {
        "gold":   ["data/raw/us_gold_daily.csv","data/us_gold_daily.csv","data/gold.csv","data/XAUUSD.csv"],
        "sp500":  ["data/raw/sp500_daily.csv","data/sp500_daily.csv","data/sp500.csv","data/SPX.csv"],
        "usdjpy": ["data/raw/usjp_fx_daily.csv","data/usjp_fx_daily.csv","data/usdjpy.csv","data/USDJPY.csv"],
        "eurjpy": ["data/raw/eujp_fx_daily.csv","data/eujp_fx_daily.csv","data/eurjpy.csv","data/EURJPY.csv"],
    }
    for path in file_map.get(asset_key, []):
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                df.columns = [c.lower().strip().replace(" ","_") for c in df.columns]
                date_col = next((c for c in df.columns if "date" in c or "time" in c), df.columns[0])
                df = df.rename(columns={date_col: "date"})
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date")
                close_candidates = ["close","price","adj_close","last","settle"]
                close_col = next((c for c in close_candidates if c in df.columns),
                                 next((c for c in df.columns if "close" in c or "price" in c), None))
                if close_col and close_col != "close":
                    df = df.rename(columns={close_col: "close"})
                if "close" in df.columns:
                    df["close"] = pd.to_numeric(df["close"], errors="coerce")
                    df = df.dropna(subset=["close"])
                    return df[["date","close"]].reset_index(drop=True)
            except Exception:
                continue
    return _generate_synthetic(asset_key)

@st.cache_data(ttl=3600, show_spinner=False)
def load_ohlc_data(asset_key: str) -> pd.DataFrame:
    """
    加载OHLC数据。
    优先读取CSV中的open/high/low/close四列。
    若CSV只有close，则将日线数据按周聚合为周K线（open=周一收盘，high=周内最高，low=最低，close=周末收盘）。
    """
    file_map = {
        "gold":   ["data/raw/us_gold_daily.csv","data/us_gold_daily.csv","data/gold.csv","data/XAUUSD.csv"],
        "sp500":  ["data/raw/sp500_daily.csv","data/sp500_daily.csv","data/sp500.csv","data/SPX.csv"],
        "usdjpy": ["data/raw/usjp_fx_daily.csv","data/usjp_fx_daily.csv","data/usdjpy.csv","data/USDJPY.csv"],
        "eurjpy": ["data/raw/eujp_fx_daily.csv","data/eujp_fx_daily.csv","data/eurjpy.csv","data/EURJPY.csv"],
    }
    for path in file_map.get(asset_key, []):
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                df.columns = [c.lower().strip().replace(" ","_") for c in df.columns]
                date_col = next((c for c in df.columns if "date" in c or "time" in c), df.columns[0])
                df = df.rename(columns={date_col: "date"})
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).sort_values("date")

                # 尝试找到 close
                close_candidates = ["close","price","adj_close","last","settle"]
                close_col = next((c for c in close_candidates if c in df.columns),
                                 next((c for c in df.columns if "close" in c or "price" in c), None))
                if not close_col:
                    continue
                if close_col != "close":
                    df = df.rename(columns={close_col: "close"})
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
                df = df.dropna(subset=["close"])

                # 检查是否有OHLC
                has_open  = any(c in df.columns for c in ["open"])
                has_high  = any(c in df.columns for c in ["high"])
                has_low   = any(c in df.columns for c in ["low"])

                if has_open and has_high and has_low:
                    for col in ["open","high","low"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    return df[["date","open","high","low","close"]].dropna().reset_index(drop=True)
                else:
                    # 只有close：合成日线OHLC
                    # open = 前一日收盘，high/low用当日价格范围估算
                    df = df[["date","close"]].copy().reset_index(drop=True)
                    df["open"]  = df["close"].shift(1).fillna(df["close"])
                    df["high"]  = df[["open","close"]].max(axis=1) * 1.002   # 日内高点估算+0.2%
                    df["low"]   = df[["open","close"]].min(axis=1) * 0.998   # 日内低点估算-0.2%
                    return df[["date","open","high","low","close"]].reset_index(drop=True)
            except Exception:
                continue

    # fallback：从synthetic数据合成日线OHLC
    df = _generate_synthetic(asset_key)
    df["open"]  = df["close"].shift(1).fillna(df["close"])
    df["high"]  = df[["open","close"]].max(axis=1) * 1.002
    df["low"]   = df[["open","close"]].min(axis=1) * 0.998
    return df[["date","open","high","low","close"]]


def make_candlestick_chart(asset_key: str, year: int, month: int, color: str, height: int = 240) -> go.Figure:
    """
    日线K线蜡烛图：读取OHLC日线数据，截取指定年月。
    涨跌颜色沿用日本惯例（红=涨，蓝=跌）。
    """
    df = load_ohlc_data(asset_key)
    mask = (df["date"].dt.year == year) & (df["date"].dt.month == month)
    sub  = df[mask].copy().reset_index(drop=True)

    fig = go.Figure()
    if len(sub) >= 2:
        fig.add_trace(go.Candlestick(
            x=sub["date"],
            open =sub["open"],
            high =sub["high"],
            low  =sub["low"],
            close=sub["close"],
            increasing=dict(line=dict(color="#C62828", width=1), fillcolor="#C62828"),
            decreasing=dict(line=dict(color="#1565C0", width=1), fillcolor="#1565C0"),
            name="",
        ))
        # 月首价格水平参考线
        base_price = float(sub["open"].iloc[0])
        final_price = float(sub["close"].iloc[-1])
        ret_pct = (final_price - base_price) / base_price * 100
        sign = "+" if ret_pct >= 0 else ""
        fig.add_hline(
            y=base_price,
            line_dash="dot", line_color=BORDER, line_width=1,
            annotation_text=f"Start {base_price:,.1f}  →  End {final_price:,.1f} ({sign}{ret_pct:.1f}%)",
            annotation_font_size=8, annotation_font_color=color,
            annotation_position="top left",
        )
    else:
        fig.add_annotation(text="No daily data for this period", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(color=TEXT2, size=11))

    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=28, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT2, size=9),
        xaxis=dict(showgrid=False, color=TEXT2, rangeslider=dict(visible=False),
                   tickformat="%b %d"),
        yaxis=dict(showgrid=True, gridcolor=BORDER, color=TEXT2),
        showlegend=False,
    )
    return fig

def _generate_synthetic(asset_key: str) -> pd.DataFrame:
    np.random.seed({"gold":42,"sp500":43,"usdjpy":44,"eurjpy":45}.get(asset_key, 0))
    dates = pd.date_range("1970-01-01", "2025-12-31", freq="D")
    n = len(dates)
    params = {"gold":(35,0.0003,0.012),"sp500":(92,0.0004,0.010),
              "usdjpy":(357,0.0001,0.006),"eurjpy":(130,0.0001,0.007)}
    p0, drift, vol = params.get(asset_key, (100, 0.0003, 0.010))
    prices = p0 * np.exp(np.cumsum(np.random.normal(drift, vol, n)))
    return pd.DataFrame({"date": dates, "close": prices})

# ─────────────────────────────────────────────
# 月度统计计算（支持时间段过滤）
# period_ranges: list of (start_str, end_str) tuples
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def compute_monthly_stats(asset_key: str,
                          period_ranges: tuple = (("1970-01-01","2099-12-31"),)) -> pd.DataFrame:
    """
    计算12个月的统计数据。
    period_ranges: 元组的元组（可哈希），每个元素是(start, end)字符串。
    多个时间段的月度数据合并后统计。
    """
    df = load_asset_data(asset_key)
    df = df[df["date"] >= "1970-01-01"].copy()

    # 根据时间段过滤（多段合并）
    masks = []
    for (start, end) in period_ranges:
        masks.append((df["date"] >= start) & (df["date"] <= end))
    if masks:
        combined_mask = masks[0]
        for m in masks[1:]:
            combined_mask = combined_mask | m
        df = df[combined_mask].copy()

    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month
    monthly = (df.groupby(["year","month"])["close"].last()
               .reset_index().sort_values(["year","month"]))

    # ── Bug修复：不按年分组shift，改为全序列连续shift ──
    # 原来：monthly.groupby("year")["close"].shift(1) → 每年1月prev_close=NaN → N=0
    # 修复：直接shift(1)，12月→次年1月 正确连接，保证全部12个月都有数据
    monthly = monthly.sort_values(["year","month"]).reset_index(drop=True)
    monthly["prev_close"] = monthly["close"].shift(1)

    # 过滤掉年份跳跃的异常行（时间段过滤后可能出现非连续月份）
    monthly["prev_year"]  = monthly["year"].shift(1).fillna(0).astype(int)
    monthly["prev_month"] = monthly["month"].shift(1).fillna(0).astype(int)
    is_consecutive = (
        ((monthly["month"] == 1) & (monthly["prev_month"] == 12) & (monthly["year"] == monthly["prev_year"] + 1)) |
        ((monthly["month"] > 1) & (monthly["month"] == monthly["prev_month"] + 1) & (monthly["year"] == monthly["prev_year"]))
    )
    monthly = monthly[is_consecutive].copy()
    monthly["ret"] = (monthly["close"] - monthly["prev_close"]) / monthly["prev_close"] * 100
    monthly = monthly.dropna(subset=["ret"])

    stats = []
    for m in range(1, 13):
        sub = monthly[monthly["month"] == m]["ret"]
        if len(sub) == 0:
            stats.append({"month":m,"avg_return":0.0,"win_rate":50.0,
                          "median_return":0.0,"max_return":0.0,"min_return":0.0,
                          "std_return":0.0,"sample_count":0})
            continue
        stats.append({
            "month":          m,
            "avg_return":     round(float(sub.mean()), 2),
            "win_rate":       round(float((sub > 0).mean() * 100), 1),
            "median_return":  round(float(sub.median()), 2),
            "max_return":     round(float(sub.max()), 2),
            "min_return":     round(float(sub.min()), 2),
            "std_return":     round(float(sub.std()), 2),
            "sample_count":   int(len(sub)),
        })
    return pd.DataFrame(stats)

def get_period_ranges_from_keys(period_keys: list) -> tuple:
    """将选择的时间段key列表转换为可哈希的ranges元组"""
    all_ranges = []
    for key in period_keys:
        if key in GOLD_PERIODS:
            all_ranges.extend(GOLD_PERIODS[key]["ranges"])
    if not all_ranges:
        all_ranges = [("1970-01-01", "2099-12-31")]
    return tuple(all_ranges)

@st.cache_data(ttl=3600, show_spinner=False)
def get_year_month_data(asset_key: str, year: int, month: int) -> pd.DataFrame:
    df = load_asset_data(asset_key)
    mask = (df["date"].dt.year == year) & (df["date"].dt.month == month)
    sub = df[mask].copy()
    if len(sub) > 1:
        base = sub["close"].iloc[0]
        sub["pct"] = (sub["close"] / base - 1) * 100
    return sub

# ─────────────────────────────────────────────
# HISTORICAL SIMILARITY ENGINE
# ─────────────────────────────────────────────
MACRO_REGIMES = {
    (1970,1972): {
        "rates":"rising", "usd":"weak",   "geo":"medium",
        "jp":"石油危機前夜",        "en":"Pre-Oil Crisis",
        "fed_rate":"4–8%",
        "geo_event":"Vietnam War",
        "geo_detail":"US deeply involved in Vietnam. Military spending drives inflation. Nixon ends gold standard (1971).",
        "dxy":"weak",
    },
    (1973,1974): {
        "rates":"rising", "usd":"weak",   "geo":"high",
        "jp":"第1次石油危機",       "en":"Oil Crisis I",
        "fed_rate":"8–13%",
        "geo_event":"OPEC Oil Embargo",
        "geo_detail":"Arab OPEC nations embargo oil to US/Europe over Yom Kippur War. Oil price quadruples. Gold surges from $35 to $195.",
        "dxy":"weak",
    },
    (1975,1977): {
        "rates":"high",   "usd":"weak",   "geo":"medium",
        "jp":"スタグフレーション",  "en":"Stagflation",
        "fed_rate":"5–7%",
        "geo_event":"Post-Vietnam Stagflation",
        "geo_detail":"US exits Vietnam. Stagflation: high unemployment + high inflation. Fed struggles with dual mandate.",
        "dxy":"weak",
    },
    (1978,1979): {
        "rates":"rising", "usd":"weak",   "geo":"high",
        "jp":"第2次石油危機",       "en":"Oil Crisis II",
        "fed_rate":"9–20%",
        "geo_event":"Iran Revolution",
        "geo_detail":"Shah of Iran overthrown. Iran-Iraq War begins. Oil supply collapses. Gold peaks at $850 (Jan 1980). Volcker begins emergency rate hikes.",
        "dxy":"weak",
    },
    (1980,1981): {
        "rates":"peak",   "usd":"strong", "geo":"high",
        "jp":"ボルカーショック",    "en":"Volcker Shock",
        "fed_rate":"15–20%",
        "geo_event":"Iran-Iraq War",
        "geo_detail":"Fed Chair Volcker raises rates to 20% to crush inflation. Dollar surges. Gold collapses from $850 peak. Severe US recession.",
        "dxy":"strong",
    },
    (1982,1984): {
        "rates":"falling","usd":"strong", "geo":"medium",
        "jp":"レーガノミクス",      "en":"Reaganomics",
        "fed_rate":"9–15%",
        "geo_event":"Latin America Debt Crisis",
        "geo_detail":"Reagan's tax cuts + military spending. Strong dollar crushes exports. Mexico, Brazil default. Gold subdued under strong USD.",
        "dxy":"strong",
    },
    (1985,1987): {
        "rates":"high",   "usd":"weak",   "geo":"low",
        "jp":"プラザ合意",          "en":"Plaza Accord",
        "fed_rate":"6–9%",
        "geo_event":"Plaza Accord (1985)",
        "geo_detail":"G5 nations agree to depreciate USD. Dollar falls 50% vs JPY/DEM in 2 years. Black Monday crash (Oct 1987). Gold benefits from weak dollar.",
        "dxy":"weak",
    },
    (1988,1989): {
        "rates":"rising", "usd":"stable", "geo":"low",
        "jp":"日本バブル",          "en":"Japan Bubble",
        "fed_rate":"8–10%",
        "geo_event":"Japan Asset Bubble Peak",
        "geo_detail":"Japanese real estate and stock market at historic peak. Fed raises rates preemptively. Berlin Wall falls Nov 1989.",
        "dxy":"stable",
    },
    (1990,1991): {
        "rates":"falling","usd":"stable", "geo":"high",
        "jp":"バブル崩壊・湾岸",    "en":"Gulf War / Japan Bust",
        "fed_rate":"5–9%",
        "geo_event":"Gulf War (1990–91)",
        "geo_detail":"Iraq invades Kuwait Aug 1990. US-led coalition Desert Storm Jan 1991. Oil spike, then collapse. Japan bubble bursts. Gold spikes then retreats.",
        "dxy":"stable",
    },
    (1992,1994): {
        "rates":"falling","usd":"weak",   "geo":"medium",
        "jp":"平成不況",            "en":"Heisei Recession",
        "fed_rate":"3–6%",
        "geo_event":"ERM Crisis / Balkan Wars",
        "geo_detail":"Soros breaks Bank of England (Sep 1992). Yugoslavia disintegrates; Bosnian War. Fed cuts rates to 3%. Gold range-bound.",
        "dxy":"weak",
    },
    (1995,1997): {
        "rates":"stable", "usd":"strong", "geo":"medium",
        "jp":"アジア通貨危機前夜",  "en":"Pre-Asian Crisis",
        "fed_rate":"5–6%",
        "geo_event":"Asian Currency Pressures",
        "geo_detail":"Strong dollar and US tech boom. Asian currencies pegged to USD under pressure. Gold enters multi-year bear market.",
        "dxy":"strong",
    },
    (1998,1999): {
        "rates":"falling","usd":"strong", "geo":"medium",
        "jp":"LTCM・ロシア危機",    "en":"LTCM / Russia Default",
        "fed_rate":"4.75–6%",
        "geo_event":"Russia Default + LTCM (1998)",
        "geo_detail":"Russia sovereign default Aug 1998. LTCM hedge fund collapses; Fed emergency cut. Kosovo NATO bombing 1999. Gold tests $250 low.",
        "dxy":"strong",
    },
    (2000,2001): {
        "rates":"falling","usd":"strong", "geo":"high",
        "jp":"ITバブル崩壊・9.11",  "en":"Dotcom Bust / 9.11",
        "fed_rate":"2.5–6.5%",
        "geo_event":"9/11 Attacks (2001)",
        "geo_detail":"Dotcom bubble bursts Mar 2000. Sept 11 attacks; US invades Afghanistan. Fed cuts from 6.5% to 1.75%. Gold begins recovery from $250 bottom.",
        "dxy":"strong",
    },
    (2002,2003): {
        "rates":"low",    "usd":"weak",   "geo":"high",
        "jp":"イラク戦争",          "en":"Iraq War",
        "fed_rate":"1–2%",
        "geo_event":"Iraq War (2003)",
        "geo_detail":"US invades Iraq Mar 2003. WMD pretext. Dollar weakens sharply. Fed holds rates at 1% (Greenspan put). Gold bull market begins, breaks $400.",
        "dxy":"weak",
    },
    (2004,2006): {
        "rates":"rising", "usd":"weak",   "geo":"medium",
        "jp":"住宅バブル",          "en":"Housing Bubble",
        "fed_rate":"1–5.25%",
        "geo_event":"US Housing Bubble",
        "geo_detail":"Fed raises rates 17 consecutive times. Sub-prime lending explodes. Dollar remains weak despite rate hikes. Gold breaks $700.",
        "dxy":"weak",
    },
    (2007,2008): {
        "rates":"falling","usd":"weak",   "geo":"high",
        "jp":"リーマンショック",    "en":"Global Financial Crisis",
        "fed_rate":"0.25–5.25%",
        "geo_event":"Lehman Brothers Collapse (2008)",
        "geo_detail":"Sub-prime crisis spreads globally. Bear Stearns fails Mar 2008. Lehman Brothers bankrupt Sep 2008. Fed cuts to 0.25%. Gold briefly dips then surges.",
        "dxy":"weak",
    },
    (2009,2010): {
        "rates":"zero",   "usd":"weak",   "geo":"medium",
        "jp":"QE・量的緩和開始",    "en":"QE Begins",
        "fed_rate":"0–0.25%",
        "geo_event":"Global QE Expansion",
        "geo_detail":"Fed launches QE1, QE2. Balance sheet expands from $900B to $2.8T. Dollar weakens significantly. Gold surges from $700 toward $1,900.",
        "dxy":"weak",
    },
    (2011,2012): {
        "rates":"zero",   "usd":"stable", "geo":"high",
        "jp":"欧州債務危機",        "en":"EU Debt Crisis",
        "fed_rate":"0–0.25%",
        "geo_event":"Eurozone Debt Crisis",
        "geo_detail":"Greece, Ireland, Portugal bailouts. ECB 'whatever it takes' Jul 2012. Arab Spring; Libya NATO intervention. Gold peaks at $1,920 Sep 2011.",
        "dxy":"stable",
    },
    (2013,2015): {
        "rates":"zero",   "usd":"strong", "geo":"medium",
        "jp":"アベノミクス・テーパー","en":"Taper Tantrum / Abenomics",
        "fed_rate":"0–0.25%",
        "geo_event":"Fed Taper Tantrum (2013)",
        "geo_detail":"Bernanke hints at QE tapering May 2013; gold crashes 15% in 2 days. Abenomics weakens yen. Ukraine crisis begins 2014. Gold bear market -40% from peak.",
        "dxy":"strong",
    },
    (2016,2017): {
        "rates":"rising", "usd":"strong", "geo":"medium",
        "jp":"トランプ相場",        "en":"Trump Rally",
        "fed_rate":"0.5–1.5%",
        "geo_event":"Brexit + Trump Election (2016)",
        "geo_detail":"UK Brexit vote Jun 2016. Trump elected Nov 2016; dollar surges. Fed begins gradual rate hikes. Gold volatile but range-bound $1,150–$1,350.",
        "dxy":"strong",
    },
    (2018,2019): {
        "rates":"peak",   "usd":"strong", "geo":"medium",
        "jp":"米中貿易摩擦",        "en":"US-China Trade War",
        "fed_rate":"2–2.5%",
        "geo_event":"US-China Trade War",
        "geo_detail":"Trump imposes tariffs on $360B of Chinese goods. China retaliates. Fed raises then cuts rates. Gold recovers above $1,500 on uncertainty.",
        "dxy":"strong",
    },
    (2020,2020): {
        "rates":"zero",   "usd":"weak",   "geo":"high",
        "jp":"コロナパンデミック",  "en":"COVID-19 Pandemic",
        "fed_rate":"0–0.25%",
        "geo_event":"COVID-19 Pandemic",
        "geo_detail":"WHO declares pandemic Mar 2020. Fed cuts to zero, launches unlimited QE. Congress passes $3T stimulus. M2 money supply grows 25% in 12 months. Gold surges to $2,075 record.",
        "dxy":"weak",
    },
    (2021,2021): {
        "rates":"zero",   "usd":"weak",   "geo":"medium",
        "jp":"インフレ台頭",        "en":"Inflation Surge",
        "fed_rate":"0–0.25%",
        "geo_event":"Transitory Inflation Debate",
        "geo_detail":"Supply chain disruptions + $1.9T stimulus = inflation. Fed calls it 'transitory'. M2 at historic high. Gold weakens despite inflation as real rates rise.",
        "dxy":"weak",
    },
    (2022,2022): {
        "rates":"rising", "usd":"strong", "geo":"high",
        "jp":"利上げ・ウクライナ",  "en":"Rate Hikes + Ukraine War",
        "fed_rate":"0.25–4.5%",
        "geo_event":"Russia Invades Ukraine (Feb 24)",
        "geo_detail":"Russia invades Ukraine Feb 24, 2022. Largest European war since WWII. Fed raises rates 425bp in 9 months. Gold spikes to $2,070, then falls as dollar surges.",
        "dxy":"strong",
    },
    (2023,2023): {
        "rates":"peak",   "usd":"strong", "geo":"high",
        "jp":"高金利・中東危機",    "en":"High Rates + Middle East",
        "fed_rate":"5–5.5%",
        "geo_event":"Hamas Attack Oct 7 / Israel-Gaza War",
        "geo_detail":"Hamas attacks Israel Oct 7, killing 1,200. Israel launches Gaza campaign. Fed holds at 5.25-5.5%. US bank failures (SVB). Gold breaks $2,000 on safe-haven demand.",
        "dxy":"strong",
    },
    (2024,2025): {
        "rates":"falling","usd":"strong", "geo":"high",
        "jp":"利下げ開始・中東緊張継続","en":"Rate Cuts + Geopolitical Risk",
        "fed_rate":"4.25–5.5%",
        "geo_event":"Middle East Escalation / US Election",
        "geo_detail":"Fed begins cutting rates Sep 2024. Iran-Israel direct strikes. Trump elected Nov 2024; tariff threats. Central bank gold buying at record pace. Gold breaks $2,500, then $2,700.",
        "dxy":"strong",
    },
}

def get_regime(year: int) -> dict:
    for (y0, y1), r in MACRO_REGIMES.items():
        if y0 <= year <= y1:
            return {**r, "year_range": f"{y0}-{y1}"}
    return {
        "rates":"stable","usd":"stable","geo":"medium",
        "jp":"不明","en":"Unknown","year_range":"N/A",
        "fed_rate":"N/A","geo_event":"Unknown","geo_detail":"","dxy":"stable",
    }

# ─────────────────────────────────────────────
# 相似度引擎（支持用户可选权重模式）
#
# match_mode 权重分配：
#   combined : Fed 25% + DXY 15% + Geo 10% + Price 50%
#   fed      : Fed 55% + DXY 10% + Geo  5% + Price 30%
#   dxy      : Fed 10% + DXY 55% + Geo  5% + Price 30%
#   geo      : Fed  5% + DXY  5% + Geo 55% + Price 35%
#   price    : Fed  5% + DXY  5% + Geo  0% + Price 90%
# ─────────────────────────────────────────────
MATCH_WEIGHTS = {
    "combined": {"fed": 0.25, "dxy": 0.15, "geo": 0.10, "price": 0.50},
    "fed":      {"fed": 0.55, "dxy": 0.10, "geo": 0.05, "price": 0.30},
    "dxy":      {"fed": 0.10, "dxy": 0.55, "geo": 0.05, "price": 0.30},
    "geo":      {"fed": 0.05, "dxy": 0.05, "geo": 0.55, "price": 0.35},
    "price":    {"fed": 0.05, "dxy": 0.05, "geo": 0.00, "price": 0.90},
}

def _fed_similarity(r1: dict, r2: dict) -> float:
    """Fed利率环境匹配：按利率周期相似度评分"""
    rate_map = {"zero":0, "low":1, "stable":2, "rising":3, "high":4, "peak":5, "falling":2.5}
    v1 = rate_map.get(r1.get("rates","stable"), 2)
    v2 = rate_map.get(r2.get("rates","stable"), 2)
    diff = abs(v1 - v2)
    # 完全一致=1.0，差1档=0.7，差2档=0.3，差3+档=0.0
    return {0: 1.0, 1: 0.7, 2: 0.3}.get(int(diff), 0.0)

def _dxy_similarity(r1: dict, r2: dict) -> float:
    """DXY美元方向匹配"""
    d1 = r1.get("dxy", r1.get("usd", "stable"))
    d2 = r2.get("dxy", r2.get("usd", "stable"))
    if d1 == d2:
        return 1.0
    # strong vs weak = 对立 = 0.0；stable vs 任意 = 0.5
    if {d1, d2} == {"strong", "weak"}:
        return 0.0
    return 0.5

def _geo_similarity(r1: dict, r2: dict) -> float:
    """地缘风险等级匹配"""
    geo_map = {"low": 0, "medium": 1, "high": 2}
    g1 = geo_map.get(r1.get("geo","medium"), 1)
    g2 = geo_map.get(r2.get("geo","medium"), 1)
    diff = abs(g1 - g2)
    return {0: 1.0, 1: 0.5, 2: 0.0}.get(diff, 0.0)

def _price_similarity(year1: int, year2: int, df: pd.DataFrame, month: int) -> float:
    """价格形态相关性（标准化后的Pearson相关系数）"""
    def norm_series(y, m):
        mask = (df["date"].dt.year == y) & (df["date"].dt.month == m)
        s = df[mask]["close"].dropna().values
        if len(s) < 5: return None
        rng = s.max() - s.min()
        return (s - s.min()) / (rng + 1e-10)
    s1, s2 = norm_series(year1, month), norm_series(year2, month)
    if s1 is None or s2 is None:
        return 0.0
    n = min(len(s1), len(s2))
    if n < 5:
        return 0.0
    c = np.corrcoef(s1[:n], s2[:n])[0, 1]
    return float(max(0.0, c)) if not np.isnan(c) else 0.0

def compute_similarity(year1: int, year2: int, df: pd.DataFrame, month: int,
                       match_mode: str = "combined") -> float:
    """综合相似度：根据match_mode分配权重"""
    r1, r2 = get_regime(year1), get_regime(year2)
    w = MATCH_WEIGHTS.get(match_mode, MATCH_WEIGHTS["combined"])
    score = (
        w["fed"]   * _fed_similarity(r1, r2) +
        w["dxy"]   * _dxy_similarity(r1, r2) +
        w["geo"]   * _geo_similarity(r1, r2) +
        w["price"] * _price_similarity(year1, year2, df, month)
    )
    return round(min(score, 1.0), 4)

def find_similar_months(asset_key: str, month: int,
                        match_mode: str = "combined", top_n: int = 6,
                        min_score: float = 0.30):
    """
    查找历史相似月份。
    min_score：最低匹配阈值（默认30%）。
    如果高于阈值的结果不足3个，取分数最高的前3个作为保底。
    """
    current_year = datetime.now().year
    df = load_asset_data(asset_key)
    candidate_years = [y for y in sorted(df["date"].dt.year.unique())
                       if 1970 <= y < current_year]
    results, data_map = [], {}
    for y in candidate_years:
        mask = (df["date"].dt.year == y) & (df["date"].dt.month == month)
        mdata = df[mask]
        if len(mdata) < 3: continue
        sim = compute_similarity(current_year, y, df, month, match_mode)
        ret = (mdata["close"].iloc[-1] / mdata["close"].iloc[0] - 1) * 100
        results.append({
            "year":       y,
            "similarity": sim,
            "return":     round(ret, 2),
            "regime":     get_regime(y),
        })
        data_map[y] = mdata

    results.sort(key=lambda x: x["similarity"], reverse=True)

    # 过滤：高于阈值的优先，不足3个则取top 3兜底
    above = [r for r in results if r["similarity"] >= min_score]
    if len(above) >= 3:
        return above[:top_n], data_map
    else:
        return results[:max(top_n, 3)], data_map

# ─────────────────────────────────────────────
# TICKER DATA
# ─────────────────────────────────────────────
def get_ticker_data():
    snapshots = [
        ("XAU/USD","3,024.5","+1.2%",True),
        ("円建て金","452,380","+1.1%",True),
        ("SPX","5,891.2","+0.3%",True),
        ("USD/JPY","149.85","-0.2%",False),
        ("EUR/JPY","163.40","+0.1%",True),
        ("DXY","106.32","+0.15%",True),
        ("WTI","78.65","-0.8%",False),
        ("VIX","18.42","-1.3%",False),
    ]
    try:
        import json
        cache_path = "data/precomputed/similarity_cache.json"
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)
            ticker_list = cache.get("ticker", [])
            if ticker_list:
                result = []
                for t in ticker_list:
                    chg = t.get("change_pct", 0)
                    sign = "+" if chg >= 0 else ""
                    result.append({
                        "symbol": t["symbol"],
                        "price":  f"{t['price']:,.2f}",
                        "change": f"{sign}{chg:.2f}%",
                        "pos":    t.get("positive", chg >= 0),
                    })
                return result
    except Exception:
        pass
    return [{"symbol":s,"price":p,"change":c,"pos":pos} for s,p,c,pos in snapshots]

# ─────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────
def make_line_chart(df: pd.DataFrame, title: str, color: str, height: int = 280) -> go.Figure:
    if df.empty: return go.Figure()
    col = "pct" if "pct" in df.columns else "close"
    r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df[col], mode="lines", name="",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({r},{g},{b},0.08)",
        hovertemplate=f"<b>%{{x|%m/%d}}</b><br>%{{y:.2f}}{'%' if col=='pct' else ''}<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=BORDER, line_width=1)
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color=TEXT), x=0.0),
        height=height, margin=dict(l=8,r=8,t=32,b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT2, size=10),
        xaxis=dict(showgrid=False, zeroline=False, color=TEXT2),
        yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False, color=TEXT2,
                   ticksuffix="%" if col=="pct" else ""),
        showlegend=False, hovermode="x unified",
    )
    return fig

def make_distribution_chart(asset_key: str, month: int, height: int = 220) -> go.Figure:
    """
    月度收益分布图：
    - X轴：涨跌幅区间
    - Y轴：历史上有多少年落在该区间
    - 右半（涨）= 红色柱，左半（跌）= 蓝色柱
    - 金色竖线 = 历史平均值
    """
    df = load_asset_data(asset_key)
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month
    mc = (df.groupby(["year","month"])["close"].last()
          .reset_index().sort_values(["year","month"]).reset_index(drop=True))
    mc["prev_close"] = mc["close"].shift(1)
    mc["prev_year"]  = mc["year"].shift(1).fillna(0).astype(int)
    mc["prev_month"] = mc["month"].shift(1).fillna(0).astype(int)
    is_consec = (
        ((mc["month"]==1) & (mc["prev_month"]==12) & (mc["year"]==mc["prev_year"]+1)) |
        ((mc["month"]>1)  & (mc["month"]==mc["prev_month"]+1) & (mc["year"]==mc["prev_year"]))
    )
    mc = mc[is_consec].copy()
    mc["ret"] = (mc["close"] - mc["prev_close"]) / mc["prev_close"] * 100
    sub = mc[mc["month"] == month]["ret"].dropna()

    fig = go.Figure()
    if len(sub) == 0:
        fig.add_annotation(text="No data", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(color=TEXT2))
        fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)")
        return fig

    avg = float(sub.mean())
    n_up   = int((sub > 0).sum())
    n_down = int((sub <= 0).sum())

    # 用Histogram绘制，正值柱红色，负值柱蓝色
    # 方法：拆成两组分别画
    up_vals   = sub[sub > 0].tolist()
    down_vals = sub[sub <= 0].tolist()

    nbins = 20
    bin_min = float(sub.min()) - 0.5
    bin_max = float(sub.max()) + 0.5
    bin_size = (bin_max - bin_min) / nbins

    if up_vals:
        fig.add_trace(go.Histogram(
            x=up_vals, name="Up years",
            xbins=dict(start=0, end=bin_max, size=bin_size),
            marker_color="#C62828", opacity=0.80,
        ))
    if down_vals:
        fig.add_trace(go.Histogram(
            x=down_vals, name="Down years",
            xbins=dict(start=bin_min, end=0, size=bin_size),
            marker_color="#1565C0", opacity=0.80,
        ))

    # 均值竖线
    fig.add_vline(x=avg, line_dash="dash", line_color=ACCENT, line_width=2,
                  annotation_text=f"Avg {avg:+.1f}%",
                  annotation_font_size=10, annotation_font_color=ACCENT,
                  annotation_position="top right")
    # 0基准线
    fig.add_vline(x=0, line_dash="dot", line_color=TEXT2, line_width=1)

    # 在图内标注涨跌年数
    fig.add_annotation(
        x=bin_max * 0.95, y=1.0, xref="x", yref="paper",
        text=f"<b style='color:#C62828'>{n_up} UP</b>",
        showarrow=False, font=dict(size=11, color="#C62828"), xanchor="right",
    )
    fig.add_annotation(
        x=bin_min * 0.95, y=1.0, xref="x", yref="paper",
        text=f"<b>{n_down} DOWN</b>",
        showarrow=False, font=dict(size=11, color="#64B5F6"), xanchor="left",
    )

    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT2, size=9),
        barmode="overlay",
        xaxis=dict(
            showgrid=False, color=TEXT2, ticksuffix="%",
            title=dict(text="Monthly return (%)", font=dict(size=9, color=TEXT2)),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=BORDER, color=TEXT2,
            title=dict(text="Years (count)", font=dict(size=9, color=TEXT2)),
        ),
        showlegend=False,
        bargap=0.05,
    )
    return fig

# ─────────────────────────────────────────────
# TOPBAR
# ─────────────────────────────────────────────
def render_topbar():
    logo_b64 = load_logo_b64()
    if logo_b64:
        logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" class="logo-img" alt="TrueFin"/>'
    else:
        logo_html = '<span class="logo-text">TRUE<span style="color:#1A73E8">FIN</span></span>'

    ticker_items = "".join([
        f'<div class="ticker-item">'
        f'<span class="ticker-symbol">{t["symbol"]}</span>'
        f'<span class="ticker-price">{t["price"]}</span>'
        f'<span class="ticker-change {"pos" if t["pos"] else "neg"}">{"+" if t["pos"] else "-"} {t["change"]}</span>'
        f'</div>'
        for t in get_ticker_data()
    ])

    sub_text = "月次インテリジェンス" if L == "jp" else "Monthly Intelligence"

    # Contact us：悬浮显示邮箱+X账号
    contact_label = "Contact Us" if L == "en" else "お問い合わせ"
    contact_html  = (
        f'<span class="topbar-contact"'
        f' title="Email: truefin.official@gmail.com  |  X: @TrueFin_JP">'
        f'{contact_label}'
        f'</span>'
    )

    st.markdown(
        f'<div class="topbar">'
        f'  <div style="display:flex;align-items:center;gap:12px;">'
        f'    {logo_html}'
        f'    <span class="logo-sub">{sub_text}</span>'
        f'  </div>'
        f'  <div style="display:flex;align-items:center;gap:20px;">'
        f'    <div style="font-size:10px;color:{TEXT2};font-family:\'Space Mono\',monospace;">'
        f'      <span style="color:{TEXT2};">Email</span>'
        f'      <span style="color:{ACCENT};margin-left:6px;">truefin.official@gmail.com</span>'
        f'      <span style="margin:0 10px;color:{BORDER};">|</span>'
        f'      <span style="color:{TEXT2};">X</span>'
        f'      <span style="color:{ACCENT};margin-left:6px;">@TrueFin_JP</span>'
        f'    </div>'
        f'  </div>'
        f'</div>'
        f'<div class="ticker-bar">{ticker_items}</div>',
        unsafe_allow_html=True,
    )

    # 按钮行：去掉Contact Us（已在顶栏显示），保留About Us + JP/EN + Mode + Refresh
    c1, c2, c3, c4, c5 = st.columns([6, 1, 1, 1, 1])
    with c2:
        about_label = "About Us" if L == "en" else "TrueFinとは"
        if st.button(about_label, key="about_btn", use_container_width=True):
            st.session_state.show_about = not st.session_state.get("show_about", False)
            st.rerun()
    with c3:
        if st.button("JP / EN", key="lang_btn", use_container_width=True):
            st.session_state.lang = "en" if L == "jp" else "jp"
            st.rerun()
    with c4:
        mode_label = "Light" if DARK else "Dark"
        if st.button(f"{mode_label} Mode", key="theme_btn", use_container_width=True):
            st.session_state.theme = "light" if DARK else "dark"
            st.rerun()
    with c5:
        if st.button("Refresh", key="refresh_btn", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

# ─────────────────────────────────────────────
# ABOUT US
# ─────────────────────────────────────────────
def render_about_modal():
    col_close, _ = st.columns([1, 9])
    with col_close:
        if st.button("Close" if L=="en" else "閉じる", key="close_about", use_container_width=True):
            st.session_state.show_about = False
            st.rerun()

    st.markdown(f"""
    <div class="about-container">
      <div class="about-title">ノイズだらけの市場で、真実を見つめたいあなたへ</div>
      <div class="about-subtitle">TrueFin 創業者からのメッセージ ／ 2026年2月 東京にて</div>
      <div class="about-body">
        <p>こんにちは。TrueFinの開発者です。</p>
        <p>「AIによる自動売買」「一攫千金」「秒速スキャルピング」……。<br>
        今の金融市場は、そんな耳触りの良い言葉と、絶え間ないノイズで溢れかえっています。</p>
        <p>そんな喧騒の中で、私はあえて<strong>「遅さ」の力</strong>と、<strong>「歴史」の価値</strong>についてお話しさせてください。</p>
        <p>実は、私もかつてはあなたと同じ、一人の個人トレーダーでした。<br>
        S&P500の激しい乱高下に狼狽し、ゴールド（XAU/USD）の不可解な動きに翻弄され、
        資産自体は増えているはずなのに、円安・円高（USD/JPY）の波に利益をいつの間にか奪われる…
        そんな悔しい夜を何度も過ごしました。</p>
        <div class="highlight">
          「多くのツールは『結果』しか見せない。『理由』は教えてくれない」<br><br>
          彼らが本当に欲しいのは、あなたの「納得」ではありません。
          あなたの「焦り」と、そこから生まれる「頻繁な売買（手数料）」です。
        </div>
        <p>TrueFinは、その「情報の壁」と「認知の歪み」を壊すために生まれました。<br>
        私が作りたかったのは、あなたを煽って手数料を稼ぐための道具ではありません。
        複雑なマクロ経済を俯瞰できる、<strong>「あなた専用のコックピット」</strong>です。</p>
        <div class="highlight">
          TrueFinは、「買え」とは言いません。「考えろ」と問いかけます。<br>
          盲目的な「追随」から、根拠のある「決断」へ。
        </div>
        <p>歴史の奔流の中で、一緒に「確かな静寂」を見つけに行きませんか。</p>
      </div>
      <div class="about-sig">TrueFin 創業者<br>2026年2月 東京にて</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 资产选择器 + 标题（已重命名为Monthly）
# ─────────────────────────────────────────────
def render_contact_modal():
    """Contact Us — 使用原生Streamlit组件，避免HTML渲染问题"""
    col_close, _ = st.columns([1, 9])
    with col_close:
        if st.button("Close" if L=="en" else "閉じる", key="close_contact", use_container_width=True):
            st.session_state.show_contact = False
            st.rerun()

    # 用原生Streamlit组件构建，不依赖HTML渲染
    st.markdown(f"""
    <div style="max-width:560px;margin:0 auto;background:{BG2};border:1px solid {BORDER};
    border-radius:16px;padding:40px 48px;line-height:1.9;">
      <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:{ACCENT};margin-bottom:8px;">
        {"Contact Us" if L=="en" else "お問い合わせ"}
      </div>
      <div style="font-size:13px;color:{TEXT2};margin-bottom:32px;border-bottom:1px solid {BORDER};padding-bottom:16px;">
        {"TrueFin Official Contact" if L=="en" else "TrueFin 公式お問い合わせ先"}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 正文用st.write，完全绕开HTML解析
    with st.container():
        st.markdown(f'<div style="max-width:560px;margin:0 auto;padding:0 48px 40px;">', unsafe_allow_html=True)

        if L == "en":
            st.write("For any inquiries regarding TrueFin — feedback, bug reports, partnership proposals, or media requests — please reach out via email.")
        else:
            st.write("TrueFinに関するご意見・不具合報告・業務提携・メディアからのお問い合わせは、以下のメールアドレスまでお気軽にどうぞ。")

        st.markdown(f"""
        <div style="background:rgba(245,200,66,0.1);border-left:3px solid {ACCENT};
        padding:16px 20px;border-radius:0 8px 8px 0;margin:20px 0;">
          <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
          color:{TEXT2};margin-bottom:8px;text-transform:uppercase;">
            {"Official Email" if L=="en" else "公式メールアドレス"}
          </div>
          <div style="font-family:'Space Mono',monospace;font-size:18px;font-weight:700;color:{ACCENT};">
            truefin.official@gmail.com
          </div>
        </div>
        """, unsafe_allow_html=True)

        if L == "en":
            st.caption("Response time: typically within 2–3 business days.")
        else:
            st.caption("返信は通常2〜3営業日以内を目安にお送りしております。")

        st.markdown(f'<div style="text-align:right;font-size:13px;color:{TEXT2};margin-top:24px;">TrueFin — {"Tokyo, Japan" if L=="en" else "東京"}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 资产选择器 + 标题
# ─────────────────────────────────────────────
def render_asset_selector():
    # 计算当前选择时间段的样本描述
    asset = st.session_state.asset
    period_keys = st.session_state.get("gold_periods", ["all"])
    period_ranges = get_period_ranges_from_keys(period_keys)

    # 样本年数估算（用于subtitle）
    label_key = "jp" if L == "jp" else "en"
    if asset == "gold" and period_keys != ["all"]:
        period_labels = " + ".join([GOLD_PERIODS[k][label_key].split("（")[0].split("(")[0].strip()
                                    for k in period_keys if k in GOLD_PERIODS])
        subtitle = (f"{period_labels} | " +
                    ("月をクリックして詳細へ" if L=="jp" else "Click a month for details"))
    else:
        subtitle = ("月をクリックして詳細へ | 1970年〜現在" if L=="jp"
                    else "Click a month for details | 1970–present")

    st.markdown(f"""
    <div class="section-header">
      <div>
        <div class="section-title">
          {"月次パフォーマンス分析" if L=="jp" else "Monthly Performance Analysis"}
        </div>
        <div class="section-subtitle">{subtitle}</div>
      </div>
      <div style="font-family:'Space Mono',monospace;font-size:11px;color:{TEXT2};">
        {datetime.now().year}{"年 最新" if L=="jp" else " Latest"}
      </div>
    </div>
    """, unsafe_allow_html=True)

    current = st.session_state.asset
    st.markdown('<div style="padding:0 24px 12px;">', unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for i, (key, meta) in enumerate(ASSETS.items()):
        label_en = meta["label_en"]
        label_jp = meta["label_jp"]
        label    = label_jp if L == "jp" else label_en
        ac       = meta["color"]
        is_sel   = (key == current)
        with cols[i]:
            if is_sel:
                st.markdown(f'<div class="asset-active-{key}">', unsafe_allow_html=True)
            if st.button(label, key=f"asset_{key}", use_container_width=True):
                st.session_state.asset = key
                st.rerun()
            if is_sel:
                st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 黄金时间段选择器（仅在Gold板块显示）
# ─────────────────────────────────────────────
def render_period_selector():
    """
    黄金专属宏观时间段选择器。
    支持多选，选中的时间段数据会合并后重新计算12格统计。
    其他资产不显示此选择器。
    """
    asset = st.session_state.asset
    if asset != "gold":
        return   # 仅Gold板块显示

    current_keys = st.session_state.get("gold_periods", ["all"])
    label_key = "jp" if L == "jp" else "en"

    # 标题（不含emoji，加 ? tooltip）
    selector_title = "相場局面フィルター" if L=="jp" else "Market Regime Filter"
    tooltip_text = (
        "全期間(56年)の平均は強気・弱気局面が相殺されます。局面を絞ることでより純粋な季節性が見えます。"
        if L=="jp" else
        "Full 56-year averages blend bull and bear cycles. Filter by regime to reveal unbiased seasonality."
    )
    hint_text = ("複数選択可 — 牛市・弱気相場のみのデータを分離" if L=="jp"
                 else "Multi-select — Isolate bull/bear periods")

    # 构建选择器区域（带tooltip问号）
    st.markdown(
        f'<div class="period-selector">'
        f'<div class="period-selector-title">'
        f'  {selector_title}'
        f'  <span class="help-tooltip" data-tip="{tooltip_text}">?</span>'
        f'</div>'
        f'<div style="font-size:10px;color:{TEXT2};margin-bottom:12px;">{hint_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 改用 st.radio 显示完整选项（单选基础模式）──
    # 方案：左侧radio单选一个主时间段；右侧可以叠加bear
    label_key = "jp" if L == "jp" else "en"

    # 构建选项列表（5个，完整文字，不截断）
    period_options = {pk: GOLD_PERIODS[pk][label_key] for pk in ["all","bull1","bull2","bull3","bear"]}
    option_labels  = list(period_options.values())
    option_keys    = list(period_options.keys())

    # 当前选择：如果是multi，取第一个非all的作为当前radio值
    current_single = current_keys[0] if current_keys else "all"

    col_radio, col_info = st.columns([3, 1])
    with col_radio:
        chosen_label = st.radio(
            label="",
            options=option_labels,
            index=option_keys.index(current_single) if current_single in option_keys else 0,
            horizontal=True,
            key="period_radio",
            label_visibility="collapsed",
        )
    chosen_key = option_keys[option_labels.index(chosen_label)]

    if chosen_key != current_single:
        st.session_state.gold_periods = [chosen_key]
        st.rerun()

    # 显示当前描述
    desc_key = "desc_jp" if L == "jp" else "desc_en"
    if current_single in GOLD_PERIODS:
        desc = GOLD_PERIODS[current_single][desc_key]
        st.markdown(
            f'<div style="padding:0 0 8px;font-size:10px;color:{TEXT2};font-style:italic;">[ {desc} ]</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# 12宫格月度卡片渲染
# ─────────────────────────────────────────────
def render_single_card(m: int, stats_row, cur_ret, color_fn,
                        current_month: int, asset_color: str, period_label: str = ""):
    avg_ret  = float(stats_row["avg_return"])
    win_rate = float(stats_row["win_rate"])
    lose_rate = 100.0 - win_rate
    std      = float(stats_row["std_return"])
    samples  = int(stats_row["sample_count"])

    c = color_fn(avg_ret)
    month_label = MONTHS_JP[m-1] if L == "jp" else MONTHS_EN[m-1]
    sign = "+" if avg_ret >= 0 else ""
    is_current = (m == current_month)

    # FOMC标签
    fomc_html = f'<div class="mc-fomc-tag">FOMC</div>' if m in FOMC_MONTHS else ""

    # 当年实绩（不再用absolute定位，改为底部inline显示）
    cur_html = ""
    if cur_ret is not None:
        cur_sign = "+" if cur_ret >= 0 else ""
        cur_html = f'<span class="mc-current-tag">{datetime.now().year}: {cur_sign}{cur_ret:.1f}%</span>'

    # 当月高亮（金色外框）
    current_glow = f"box-shadow:0 0 0 3px {asset_color}88;" if is_current else ""
    star = "[NOW] " if is_current else ""

    # ── 双色WIN/LOSS分割条 ──────────────────────────────
    # 日语：勝 / 負   英语：WIN / LOSS
    win_label  = "勝" if L=="jp" else "WIN"
    lose_label = "負" if L=="jp" else "LOSS"
    win_section = (
        f'<div class="mc-win-section">'
        f'  <div class="mc-win-labels">'
        f'    <span class="mc-win-label-win">▲ {win_label} {win_rate:.0f}%</span>'
        f'    <span class="mc-win-label-lose">▼ {lose_label} {lose_rate:.0f}%</span>'
        f'  </div>'
        f'  <div class="mc-win-dual-bar">'
        f'    <div class="mc-win-bar-fill" style="width:{win_rate:.1f}%;"></div>'
        f'    <div class="mc-loss-bar-fill" style="width:{lose_rate:.1f}%;"></div>'
        f'  </div>'
        f'</div>'
    )

    # ── 统计行：波動率 + 年数（替代STD DEV + N）──────────
    vol_label     = "波動率" if L=="jp" else "Volatility"
    years_label   = "年数"   if L=="jp" else "Years"

    html = (
        f'<div class="month-card-v2" '
        f'style="--c-bg:{c["bg"]};--c-border:{c["border"]};'
        f'--c-badge-bg:{c["badge_bg"]};--c-badge-text:{c["badge_text"]};{current_glow}">'
        f'{fomc_html}'
        f'<div class="mc-month-label">{star}{month_label}</div>'
        # 修复1：inline style直接传color，不依赖CSS变量，确保颜色渐变正确显示
        f'<div class="mc-return" style="color:{c["text"]};">{sign}{avg_ret:.1f}%</div>'
        f'<div class="mc-badge">{c["label"]}</div>'
        f'<div class="mc-stats-row">'
        f'  <div class="mc-stat">'
        f'    <span class="mc-stat-label">{vol_label}</span>'
        f'    <span class="mc-stat-value">{std:.1f}%</span>'
        f'  </div>'
        f'  <div class="mc-stat">'
        f'    <span class="mc-stat-label">{years_label}</span>'
        f'    <span class="mc-stat-value">{samples}</span>'
        f'  </div>'
        f'</div>'
        f'{win_section}'
        f'{cur_html}'
        f'</div>'
    )
    return html


def render_month_grid(stats_df: pd.DataFrame, period_label: str = ""):
    asset         = st.session_state.asset
    asset_color   = ASSETS[asset]["color"]
    current_year  = datetime.now().year
    current_month = datetime.now().month
    color_fn      = get_card_color if DARK else get_card_color_light

    # 获取今年各月实绩
    cur_year_returns = {}
    for m in range(1, 13):
        ym = get_year_month_data(asset, current_year, m)
        if len(ym) >= 2:
            cur_year_returns[m] = round(
                (ym["close"].iloc[-1] / ym["close"].iloc[0] - 1) * 100, 2
            )

    stats_map = {int(row["month"]): row for _, row in stats_df.iterrows()}

    # 图例（6档，无emoji，用小色块）
    legend_items = [
        ("#FF1744", "FF1744", "Ultra Bull >=+3%"    if L=="en" else "極強気 >=+3%"),
        ("#C62828", "C62828", "Bull +1.5~3%"        if L=="en" else "強気 +1.5~3%"),
        ("#EF5350", "EF5350", "Mild Bull 0~+1.5%"   if L=="en" else "小強気 0~+1.5%"),
        ("#42A5F5", "42A5F5", "Mild Bear 0~-1.5%"   if L=="en" else "小弱気 0~-1.5%"),
        ("#1565C0", "1565C0", "Bear -1.5~-3%"       if L=="en" else "弱気 -1.5~-3%"),
        ("#0D47A1", "0D47A1", "Ultra Bear <=-3%"    if L=="en" else "極弱気 <=-3%"),
    ]
    legend_html = " ".join([
        f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:10px;">'
        f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{col};"></span>'
        f'<span style="color:{TEXT2};font-size:10px;">{label}</span>'
        f'</span>'
        for col, _, label in legend_items
    ])
    st.markdown(
        f'<div style="padding:0 24px 10px;display:flex;flex-wrap:wrap;gap:2px;">{legend_html}</div>',
        unsafe_allow_html=True,
    )

    # ── 点击按钮标签 ──────────────────────────────────────
    click_label = "詳細分析" if L=="jp" else "Details"

    def render_card_with_btn(cols_list: list, months_range: range):
        """在一行columns中渲染卡片+间隙+Details按钮"""
        for i, m in enumerate(months_range):
            row_data = stats_map.get(m)
            if row_data is None:
                continue
            card_html = render_single_card(
                m, row_data, cur_year_returns.get(m),
                color_fn, current_month, asset_color, period_label
            )
            with cols_list[i]:
                # 卡片（完整圆角）
                st.markdown(card_html, unsafe_allow_html=True)
                # 6px透明间隙（使用页面背景色隔开）
                st.markdown(f'<div class="mc-gap"></div>', unsafe_allow_html=True)
                # Details按钮（独立卡片，带自己的圆角）
                st.markdown('<div class="mc-details-btn">', unsafe_allow_html=True)
                if st.button(click_label, key=f"card_btn_{m}", use_container_width=True):
                    st.session_state.view         = "detail"
                    st.session_state.detail_month = m
                    st.session_state.detail_asset = st.session_state.asset
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # 第1行：1-6月
    row1_cols = st.columns(6, gap="small")
    render_card_with_btn(row1_cols, range(1, 7))

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # 第2行：7-12月
    row2_cols = st.columns(6, gap="small")
    render_card_with_btn(row2_cols, range(7, 13))

# ─────────────────────────────────────────────
# DETAIL VIEW
# ─────────────────────────────────────────────
def render_detail_view():
    asset       = st.session_state.detail_asset or st.session_state.asset
    month       = st.session_state.detail_month or 1
    meta        = ASSETS[asset]
    color       = meta["color"]
    asset_label = meta["label_jp"] if L=="jp" else meta["label_en"]
    month_label = MONTHS_JP[month-1] if L=="jp" else MONTHS_EN[month-1]
    cur_year    = datetime.now().year

    col_back, _ = st.columns([1, 9])
    with col_back:
        if st.button("Back" if L=="en" else "戻る", key="back_btn", use_container_width=True):
            st.session_state.view = "main"
            st.rerun()

    st.markdown(
        f'<div style="padding:4px 24px 16px;">'
        f'<div style="font-family:\'Syne\',sans-serif;font-size:24px;font-weight:800;color:{color};">'
        f'{asset_label} · {month_label}'
        f'</div>'
        f'<div style="font-size:11px;color:{TEXT2};margin-top:4px;">'
        f'{"1970年〜現在のヒストリカル分析 | AI類似相場マッチング" if L=="jp" else "Historical analysis 1970–present | AI similarity matching"}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # 统计摘要
    stats_df = compute_monthly_stats(asset)
    row = stats_df[stats_df["month"] == month].iloc[0]
    m1, m2, m3, m4, m5 = st.columns(5)
    def stat_box(col, label, value):
        col.markdown(
            f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;'
            f'padding:12px 14px;border-top:3px solid {color};">'
            f'<div style="font-size:8px;color:{TEXT2};letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">{label}</div>'
            f'<div style="font-family:\'Space Mono\',monospace;font-size:20px;font-weight:700;color:{TEXT};">{value}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    s = "+" if row["avg_return"] > 0 else ""
    stat_box(m1, "平均騰落率" if L=="jp" else "Avg Return", f'{s}{row["avg_return"]:.2f}%')
    stat_box(m2, "勝率" if L=="jp" else "Win Rate",   f'{row["win_rate"]:.1f}%')
    stat_box(m3, "中央値" if L=="jp" else "Median",   f'{row["median_return"]:+.2f}%')
    stat_box(m4, "最大上昇" if L=="jp" else "Best",   f'+{row["max_return"]:.2f}%')
    stat_box(m5, "最大下落" if L=="jp" else "Worst",  f'{row["min_return"]:.2f}%')

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # Return Distribution：内嵌说明，让用户不用猜
    dist_label = ("リターン分布" if L=="jp" else "Return Distribution")
    with st.expander(dist_label, expanded=True):
        # 用原生st组件先解释图表含义
        if L == "en":
            st.caption(
                "How to read: X-axis = this month's gain/loss %. "
                "Y-axis = how many years landed in that range (out of ~56 years). "
                "RED bars = years with positive returns. BLUE bars = years with losses. "
                "Gold dashed line = historical average."
            )
        else:
            st.caption(
                "読み方：X軸＝この月の騰落率(%)、Y軸＝過去約56年のうち何年がその騰落率を記録したか。"
                "赤い棒＝上昇した年、青い棒＝下落した年、金色の点線＝歴史的平均値。"
            )
        st.plotly_chart(make_distribution_chart(asset, month),
                        use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # 左右分屏
    left_col, right_col = st.columns([10, 10], gap="large")

    with right_col:
        st.markdown(
            f'<div class="split-panel-title" style="color:{color};">'
            f'{cur_year}{"年 " if L=="jp" else " "}{month_label} — '
            f'{"当年データ" if L=="jp" else "Current Year"}'
            f'</div>',
            unsafe_allow_html=True,
        )
        cur_data = get_year_month_data(asset, cur_year, month)
        if len(cur_data) >= 2:
            ret_val = (cur_data["close"].iloc[-1] / cur_data["close"].iloc[0] - 1) * 100
            ret_color = "#FF6B6B" if ret_val >= 0 else "#64B5F6"
            sign = "+" if ret_val >= 0 else ""
            st.markdown(
                f'<div style="font-family:\'Space Mono\',monospace;font-size:36px;font-weight:700;'
                f'color:{ret_color};margin-bottom:12px;">{sign}{ret_val:.2f}%</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(make_line_chart(cur_data, f"{cur_year} {month_label}", color, height=300),
                            use_container_width=True, config={"displayModeBar": False})
            latest = cur_data.iloc[-1]
            st.markdown(
                f'<div style="background:{BG3};border-radius:8px;padding:10px 14px;">'
                f'<div style="font-size:9px;color:{TEXT2};margin-bottom:4px;">'
                f'{"最新値" if L=="jp" else "Latest"} — {latest["date"].strftime("%Y/%m/%d")}</div>'
                f'<div style="font-family:\'Space Mono\',monospace;font-size:18px;font-weight:700;color:{TEXT};">'
                f'{latest["close"]:,.2f}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("当月データなし" if L=="jp" else "No data yet for current month")

        cur_regime = get_regime(cur_year)
        # 当前宏观标签：Fed利率 + DXY方向 + 地缘事件（去掉所有emoji）
        fed_label  = cur_regime.get("fed_rate", cur_regime["rates"])
        dxy_dir    = cur_regime.get("dxy", cur_regime["usd"])
        geo_ev     = cur_regime.get("geo_event", cur_regime["geo"])
        geo_detail = cur_regime.get("geo_detail", "")
        era_label  = cur_regime["jp"] if L=="jp" else cur_regime["en"]

        dxy_cls = {"weak":"tag-dxy-weak","strong":"tag-dxy-strong"}.get(dxy_dir,"tag-dxy-stable")
        dxy_txt = {"weak":"USD Weak","strong":"USD Strong","stable":"USD Stable"}.get(dxy_dir,"USD Stable")

        regime_html = (
            f'<div class="macro-tags">'
            f'  <span class="tag-fed"><span class="tag-fed-label">FED</span>{fed_label}</span>'
            f'  <span class="{dxy_cls}"><span class="tag-fed-label">DXY</span>{dxy_txt}</span>'
            f'  <span class="tag-geo" data-geo="{geo_detail}">'
            f'    <span class="tag-geo-dot"></span>{geo_ev}'
            f'  </span>'
            f'  <span style="background:{BG3};border:1px solid {BORDER};border-radius:6px;'
            f'  padding:3px 9px;font-size:10px;color:{TEXT2};">{era_label}</span>'
            f'</div>'
        )
        st.markdown(
            f'<div style="margin-top:16px;">'
            f'<div style="font-size:9px;color:{TEXT2};letter-spacing:1px;margin-bottom:8px;">'
            f'{"現在のマクロ環境" if L=="jp" else "CURRENT MACRO REGIME"}</div>'
            f'{regime_html}</div>',
            unsafe_allow_html=True,
        )

    with left_col:
        # ── Match Mode Filter（用户可选匹配维度优先级）──────
        mode_labels = {
            "combined": "Combined" if L=="en" else "総合",
            "fed":      "Fed Rate"  if L=="en" else "Fed金利",
            "dxy":      "USD / DXY" if L=="en" else "米ドル強弱",
            "geo":      "Geo Risk"  if L=="en" else "地政学",
            "price":    "Price Pattern" if L=="en" else "価格形態",
        }
        mode_keys   = list(mode_labels.keys())
        mode_descs  = {
            "combined":  "Fed 25% + DXY 15% + Geo 10% + Price 50%",
            "fed":       "Fed Rate cycle 55% + Price 30% + DXY 10%",
            "dxy":       "USD direction 55% + Price 30% + Fed 10%",
            "geo":       "Geopolitical risk 55% + Price 35% + FED/DXY 10%",
            "price":     "Price pattern only 90% — pure chart similarity",
        }

        current_mode = st.session_state.get("match_mode", "combined")

        st.markdown(
            f'<div class="split-panel-title">'
            f'{"AI類似ヒストリカル相場" if L=="jp" else "AI Historical Matches"}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # 5个小按钮横排，选中高亮金色
        mode_cols = st.columns(5, gap="small")
        for ci, mk in enumerate(mode_keys):
            is_mode = (mk == current_mode)
            with mode_cols[ci]:
                if is_mode:
                    st.markdown(
                        f'<div style="border-radius:6px;border:1.5px solid {ACCENT};'
                        f'background:rgba(245,200,66,0.1);">',
                        unsafe_allow_html=True,
                    )
                if st.button(mode_labels[mk], key=f"mode_{mk}", use_container_width=True):
                    st.session_state.match_mode = mk
                    st.rerun()
                if is_mode:
                    st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            f'<div style="font-size:9px;color:{TEXT2};margin:4px 0 12px;font-style:italic;">'
            f'Weights: {mode_descs.get(current_mode,"")}'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.spinner("Finding matches..."):
            results, data_map = find_similar_months(
                asset, month,
                match_mode=current_mode,
                top_n=6,
                min_score=0.30,
            )

        if not results:
            st.info("データ不足" if L=="jp" else "Insufficient data")
        else:
            for res in results:
                y         = res["year"]
                sim       = res["similarity"]
                ret       = res["return"]
                regime    = res["regime"]
                ret_color = "#FF6B6B" if ret >= 0 else "#64B5F6"
                sign      = "+" if ret >= 0 else ""
                sim_pct   = int(sim * 100)
                year_lbl  = f'{y}{"年" if L=="jp" else ""} {month_label}'
                era_label = regime["jp"] if L=="jp" else regime["en"]

                # 三维标签：Fed利率 + DXY货币方向 + 地缘事件（鼠标悬浮tooltip）
                fed_rate   = regime.get("fed_rate", regime["rates"])
                dxy_dir    = regime.get("dxy", regime["usd"])
                geo_event  = regime.get("geo_event", regime["geo"])
                geo_detail = regime.get("geo_detail", "").replace('"', "&quot;")

                dxy_cls = {"weak":"tag-dxy-weak","strong":"tag-dxy-strong"}.get(dxy_dir,"tag-dxy-stable")
                dxy_txt = {"weak":"USD Weak","strong":"USD Strong","stable":"USD Stable"}.get(dxy_dir,"USD Stable")

                tags_html = (
                    f'<div class="macro-tags">'
                    f'  <span class="tag-fed"><span class="tag-fed-label">FED</span>{fed_rate}</span>'
                    f'  <span class="{dxy_cls}"><span class="tag-fed-label">DXY</span>{dxy_txt}</span>'
                    f'  <span class="tag-geo" data-geo="{geo_detail}">'
                    f'    <span class="tag-geo-dot"></span>{geo_event}'
                    f'  </span>'
                    f'  <span style="background:{BG3};border:1px solid {BORDER};border-radius:6px;'
                    f'  padding:3px 9px;font-size:10px;color:{TEXT2};">{era_label}</span>'
                    f'</div>'
                )

                st.markdown(
                    f'<div class="hist-card">'
                    f'  <div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                    f'    <div style="flex:1;">'
                    f'      <div class="hist-year">{year_lbl}</div>'
                    f'      <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">'
                    f'        <div style="font-size:10px;color:{TEXT2};">'
                    f'          {"類似度" if L=="jp" else "Match"}:'
                    f'          <span style="color:{color};font-family:\'Space Mono\',monospace;font-weight:700;margin-left:3px;">{sim_pct}%</span>'
                    f'        </div>'
                    f'        <div style="flex:1;height:3px;background:{BORDER};border-radius:2px;max-width:80px;overflow:hidden;">'
                    f'          <div style="height:100%;width:{sim_pct}%;background:{color};border-radius:2px;"></div>'
                    f'        </div>'
                    f'      </div>'
                    f'    </div>'
                    f'    <div style="text-align:right;flex-shrink:0;">'
                    f'      <div style="font-family:\'Space Mono\',monospace;font-size:28px;font-weight:700;color:{ret_color};">'
                    f'        {sign}{ret:.1f}%'
                    f'      </div>'
                    f'      <div style="font-size:9px;color:{TEXT2};">{"月間騰落" if L=="jp" else "Monthly return"}</div>'
                    f'    </div>'
                    f'  </div>'
                    f'  {tags_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # K线蜡烛图（替代折线图）
                fig_candle = make_candlestick_chart(asset, y, month, color, height=200)
                st.plotly_chart(
                    fig_candle,
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key=f"candle_{y}_{month}",
                )

# ─────────────────────────────────────────────
# MAIN VIEW
# ─────────────────────────────────────────────
def render_main_view():
    asset = st.session_state.asset

    # 确定时间段范围（Gold专属）
    period_keys = st.session_state.get("gold_periods", ["all"])
    if asset == "gold":
        period_ranges = get_period_ranges_from_keys(period_keys)
        # 生成简短标签用于卡片显示
        if period_keys == ["all"]:
            period_label = ""
        else:
            label_key = "jp" if L == "jp" else "en"
            short_names = []
            for pk in period_keys:
                if pk in GOLD_PERIODS:
                    full = GOLD_PERIODS[pk][label_key]
                    # 取括号前的核心词
                    core = full.split("（")[0].split("(")[0].strip()
                    short_names.append(core)
            period_label = "/".join(short_names)
    else:
        period_ranges = (("1970-01-01","2099-12-31"),)
        period_label  = ""

    with st.spinner(("データ読み込み中..." if L=="jp" else "Loading...")):
        stats_df = compute_monthly_stats(asset, period_ranges)

    render_asset_selector()
    render_period_selector()     # Gold板块专属选择器
    render_month_grid(stats_df, period_label)

    # 年×月热力图
    st.markdown(
        f'<div style="padding:20px 24px 6px;">'
        f'<div style="font-family:\'Syne\',sans-serif;font-size:17px;font-weight:800;color:{TEXT};">'
        f'{"年別 × 月別 パフォーマンス" if L=="jp" else "Year × Month Heatmap"}'
        f'</div>'
        f'<div style="font-size:10px;color:{TEXT2};margin-top:3px;">'
        f'{"赤=上昇 | 青=下落 | 数値は月次騰落率(%)" if L=="jp" else "Red=Up | Blue=Down | Monthly returns (%)"}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    df_all = load_asset_data(asset)
    df_all["year"]  = df_all["date"].dt.year
    df_all["month"] = df_all["date"].dt.month
    mc = (df_all.groupby(["year","month"])["close"].last()
          .reset_index().sort_values(["year","month"]).reset_index(drop=True))
    # 连续shift方法
    mc["prev_close"] = mc["close"].shift(1)
    mc["prev_year"]  = mc["year"].shift(1).fillna(0).astype(int)
    mc["prev_month"] = mc["month"].shift(1).fillna(0).astype(int)
    is_consec = (
        ((mc["month"] == 1) & (mc["prev_month"] == 12) & (mc["year"] == mc["prev_year"] + 1)) |
        ((mc["month"] > 1)  & (mc["month"] == mc["prev_month"] + 1) & (mc["year"] == mc["prev_year"]))
    )
    mc = mc[is_consec].copy()
    mc["ret"] = (mc["close"] - mc["prev_close"]) / mc["prev_close"] * 100
    mc = mc.dropna(subset=["ret"])

    # 同步 period_ranges 过滤（与12宫格保持一致）
    if period_ranges and period_ranges != (("1970-01-01","2099-12-31"),):
        masks = [((mc["year"] >= int(s[:4])) & (mc["year"] <= int(e[:4]))) for s, e in period_ranges]
        combined = masks[0]
        for mk in masks[1:]:
            combined = combined | mk
        mc_filtered = mc[combined]
    else:
        mc_filtered = mc[mc["year"] >= 1970]

    pivot = mc_filtered.pivot(index="year", columns="month", values="ret").sort_index(ascending=False)

    colorscale = [
        [0.00, "#0D47A1"],
        [0.35, "#42A5F5"],
        [0.50, BG3],
        [0.65, "#EF9A9A"],
        [1.00, "#C62828"],
    ]

    fig_heat = go.Figure(go.Heatmap(
        z=pivot.values,
        x=MONTHS_JP if L=="jp" else MONTHS_EN,
        y=pivot.index.tolist(),
        colorscale=colorscale,
        zmid=0, zmin=-10, zmax=10,
        text=np.round(pivot.values, 1),
        texttemplate="%{text}%",
        textfont=dict(size=8, color="white"),
        hovertemplate="%{y}" + ("年 " if L=="jp" else " ") + "%{x}: %{z:.2f}%<extra></extra>",
        showscale=True,
        colorbar=dict(thickness=10, len=0.8,
                      tickfont=dict(color=TEXT2, size=8), ticksuffix="%"),
    ))
    fig_heat.update_layout(
        height=max(380, len(pivot) * 17),
        margin=dict(l=8, r=60, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT2, size=9),
        xaxis=dict(side="top", color=TEXT2),
        yaxis=dict(
            color=TEXT2, tickfont=dict(size=9),
            dtick=5,            # Y轴每5年一个刻度
            tickmode="linear",
        ),
    )
    with st.container():
        st.markdown('<div style="padding:0 24px;">', unsafe_allow_html=True)
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# APP ENTRY
# ─────────────────────────────────────────────
def main():
    render_topbar()

    if st.session_state.get("show_about", False):
        render_about_modal()
        return

    if st.session_state.view == "main":
        render_main_view()
    elif st.session_state.view == "detail":
        render_detail_view()

if __name__ == "__main__":
    main()