"""
TrueFin — 本地预计算脚本 precompute.py
=======================================
用途：在本地电脑上跑，把所有重计算结果存成JSON，
      再上传到 Hugging Face Spaces 的 data/precomputed/ 目录。

运行方式：
    cd truefin/
    python precompute.py

输出文件：
    data/precomputed/monthly_stats.json      # 12个月×4资产的统计数据
    data/precomputed/heatmap_matrix.json     # 年×月热力图矩阵
    data/precomputed/similarity_cache.json   # 历史相似月份缓存

作者：TrueFin Development
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 路径配置
# ─────────────────────────────────────────────────────────────────────────────
RAW_DIR        = Path("data/raw")
OUTPUT_DIR     = Path("data/precomputed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# CSV文件映射（对应你本地 data/raw/ 里的实际文件名）
# ─────────────────────────────────────────────────────────────────────────────
CSV_MAP = {
    # 主要资产（用于12宫格展示）
    "gold_usd":  "us_gold_daily.csv",    # 美元计价黄金 (XAU/USD)
    "gold_jpy":  "jp_gold_daily.csv",    # 日元计价黄金 (円建て金)
    "sp500":     "sp500_daily.csv",      # S&P500
    "usdjpy":    "usjp_fx_daily.csv",    # USD/JPY
    "eurjpy":    "eujp_fx_daily.csv",    # EUR/JPY
    # 辅助数据（用于宏观标签和相似度）
    "dxy":       "dxy_daily.csv",        # 美元指数 DXY
    "wti":       "wti_daily.csv",        # WTI原油
    "cftc_gold": "cftc_cot_gold.csv",    # CFTC黄金COT持仓
    "wgc_cb":    "wgc_central_bank.csv", # 世界黄金协会央行购金
}

# 12宫格展示的主资产列表（对应app.py里的资产切换按钮）
MAIN_ASSETS = ["gold_usd", "gold_jpy", "sp500", "usdjpy", "eurjpy"]

# 日语/英语显示名
ASSET_META = {
    "gold_usd": {"jp": "ゴールド(USD)", "en": "Gold (USD)", "color": "#F5C842", "symbol": "XAU/USD"},
    "gold_jpy": {"jp": "ゴールド(円)",  "en": "Gold (JPY)", "color": "#FFB300", "symbol": "円建て金"},
    "sp500":    {"jp": "S&P500",        "en": "S&P 500",   "color": "#4ECDC4", "symbol": "SPX"},
    "usdjpy":   {"jp": "ドル円",         "en": "USD/JPY",   "color": "#FF6B6B", "symbol": "USD/JPY"},
    "eurjpy":   {"jp": "ユーロ円",       "en": "EUR/JPY",   "color": "#A8DADC", "symbol": "EUR/JPY"},
}

MONTHS_JP = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
MONTHS_EN = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: 数据加载工具函数
# ─────────────────────────────────────────────────────────────────────────────
def load_csv(key: str) -> pd.DataFrame:
    """
    加载单个CSV文件，自动处理列名、日期解析。
    返回包含 date + close 列的 DataFrame（按日期升序）。
    """
    fname = CSV_MAP.get(key)
    if not fname:
        print(f"  ⚠️  未找到 {key} 的文件映射")
        return pd.DataFrame()

    fpath = RAW_DIR / fname
    if not fpath.exists():
        print(f"  ⚠️  文件不存在: {fpath}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(fpath)
    except Exception as e:
        print(f"  ❌ 读取失败 {fpath}: {e}")
        return pd.DataFrame()

    # --- 标准化列名（全小写，去除空格）---
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    # --- 自动识别日期列 ---
    date_col = next(
        (c for c in df.columns if c in ["date","time","datetime","timestamp","Date"]),
        df.columns[0]
    )
    df = df.rename(columns={date_col: "date"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # --- 自动识别价格列 ---
    # 优先顺序：close → price → adj_close → last → settle
    price_candidates = ["close", "price", "adj_close", "adj close", "last", "settle",
                        "close_price", "closing_price"]
    close_col = next((c for c in price_candidates if c in df.columns), None)
    if close_col is None:
        # 退而求其次：找第一个数字列（非日期）
        for c in df.columns:
            if c != "date":
                try:
                    pd.to_numeric(df[c], errors="raise")
                    close_col = c
                    break
                except Exception:
                    continue

    if close_col is None:
        print(f"  ⚠️  {fname} 找不到价格列，可用列: {df.columns.tolist()}")
        return pd.DataFrame()

    if close_col != "close":
        df = df.rename(columns={close_col: "close"})

    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])

    # 保留OHLC（如果有）
    ohlc_map = {}
    for col in ["open","high","low","volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            ohlc_map[col] = True

    keep_cols = ["date","close"] + [c for c in ["open","high","low","volume"] if c in df.columns]
    df = df[keep_cols]

    print(f"  ✅ {key:12s} → {fname:30s} | {len(df):6,d} 行 | "
          f"{df['date'].min().date()} ~ {df['date'].max().date()}")
    return df

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: 月度统计计算（monthly_stats.json）
# ─────────────────────────────────────────────────────────────────────────────
def compute_monthly_stats(df: pd.DataFrame) -> list:
    """
    计算每个自然月（1-12）的历史统计指标。
    返回12条记录的列表。
    """
    if df.empty:
        return []

    df = df[df["date"] >= "1970-01-01"].copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    # 取每月最后一个交易日的收盘价
    monthly = (
        df.groupby(["year","month"])["close"]
        .last().reset_index()
        .sort_values(["year","month"])
    )
    # 计算月度涨跌幅
    monthly["prev_close"] = monthly.groupby("year")["close"].shift(1)
    monthly["ret"] = (monthly["close"] - monthly["prev_close"]) / monthly["prev_close"] * 100
    monthly = monthly.dropna(subset=["ret"])

    stats = []
    for m in range(1, 13):
        sub = monthly[monthly["month"] == m]["ret"]
        if len(sub) < 3:
            continue
        stats.append({
            "month":          m,
            "month_jp":       MONTHS_JP[m-1],
            "month_en":       MONTHS_EN[m-1],
            "avg_return":     round(float(sub.mean()), 3),
            "win_rate":       round(float((sub > 0).mean() * 100), 1),
            "median_return":  round(float(sub.median()), 3),
            "max_return":     round(float(sub.max()), 3),
            "min_return":     round(float(sub.min()), 3),
            "std_return":     round(float(sub.std()), 3),
            "sample_count":   int(len(sub)),
            # 最近5年数据（用于tooltip展示趋势）
            "recent_5y":      [
                round(float(v), 2)
                for v in monthly[monthly["month"] == m].tail(5)["ret"].tolist()
            ],
            # 最近5年对应的年份
            "recent_5y_years": [
                int(v)
                for v in monthly[monthly["month"] == m].tail(5)["year"].tolist()
            ],
        })
    return stats

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: 热力图矩阵（heatmap_matrix.json）
# ─────────────────────────────────────────────────────────────────────────────
def compute_heatmap_matrix(df: pd.DataFrame, start_year: int = 1990) -> dict:
    """
    生成年×月的涨跌幅矩阵，用于热力图展示。
    返回格式：{ "years": [...], "months": [...], "values": [[row], [row]...] }
    """
    if df.empty:
        return {}

    df = df[df["date"] >= f"{start_year}-01-01"].copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    monthly = (
        df.groupby(["year","month"])["close"]
        .last().reset_index()
        .sort_values(["year","month"])
    )
    monthly["prev_close"] = monthly.groupby("year")["close"].shift(1)
    monthly["ret"] = (monthly["close"] - monthly["prev_close"]) / monthly["prev_close"] * 100

    pivot = monthly.pivot(index="year", columns="month", values="ret")
    pivot = pivot.sort_index(ascending=False)

    years  = [int(y) for y in pivot.index.tolist()]
    months = list(range(1, 13))

    # 转成嵌套列表，NaN转None（JSON兼容）
    values = []
    for y in pivot.index:
        row = []
        for m in range(1, 13):
            val = pivot.loc[y, m] if m in pivot.columns else np.nan
            row.append(round(float(val), 2) if not np.isnan(val) else None)
        values.append(row)

    return {
        "years":       years,
        "months_jp":   MONTHS_JP,
        "months_en":   MONTHS_EN,
        "values":      values,
        "start_year":  start_year,
    }

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: 宏观环境标签库（内嵌，用于相似度计算）
# ─────────────────────────────────────────────────────────────────────────────
MACRO_REGIMES = {
    # (起始年, 结束年): 宏观标签
    (1970, 1972): {"rates":"rising",  "usd":"weak",   "geo":"medium", "jp":"石油危機前夜",       "en":"Pre-Oil Crisis"},
    (1973, 1974): {"rates":"rising",  "usd":"weak",   "geo":"high",   "jp":"第1次石油危機",      "en":"Oil Crisis I"},
    (1975, 1977): {"rates":"high",    "usd":"weak",   "geo":"medium", "jp":"スタグフレーション", "en":"Stagflation"},
    (1978, 1979): {"rates":"rising",  "usd":"weak",   "geo":"high",   "jp":"第2次石油危機",      "en":"Oil Crisis II"},
    (1980, 1981): {"rates":"peak",    "usd":"strong", "geo":"high",   "jp":"ボルカーショック",   "en":"Volcker Shock"},
    (1982, 1984): {"rates":"falling", "usd":"strong", "geo":"medium", "jp":"レーガノミクス",     "en":"Reaganomics"},
    (1985, 1987): {"rates":"high",    "usd":"weak",   "geo":"low",    "jp":"プラザ合意",         "en":"Plaza Accord"},
    (1988, 1989): {"rates":"rising",  "usd":"stable", "geo":"low",    "jp":"日本バブル",         "en":"Japan Bubble"},
    (1990, 1991): {"rates":"falling", "usd":"stable", "geo":"high",   "jp":"バブル崩壊・湾岸",   "en":"Bubble Burst/Gulf War"},
    (1992, 1994): {"rates":"falling", "usd":"weak",   "geo":"medium", "jp":"平成不況",           "en":"Heisei Recession"},
    (1995, 1997): {"rates":"stable",  "usd":"strong", "geo":"medium", "jp":"阪神・アジア通貨",   "en":"Asian Currency Crisis"},
    (1998, 1999): {"rates":"falling", "usd":"strong", "geo":"medium", "jp":"ロシア危機・LTCM",   "en":"LTCM/Russia Crisis"},
    (2000, 2001): {"rates":"falling", "usd":"strong", "geo":"high",   "jp":"ITバブル崩壊・9.11", "en":"Dotcom Bust/9.11"},
    (2002, 2003): {"rates":"low",     "usd":"weak",   "geo":"high",   "jp":"イラク戦争",         "en":"Iraq War"},
    (2004, 2006): {"rates":"rising",  "usd":"weak",   "geo":"medium", "jp":"住宅バブル",         "en":"Housing Bubble"},
    (2007, 2008): {"rates":"falling", "usd":"weak",   "geo":"high",   "jp":"リーマンショック",   "en":"Global Financial Crisis"},
    (2009, 2010): {"rates":"zero",    "usd":"weak",   "geo":"medium", "jp":"量的緩和開始",       "en":"QE Begins"},
    (2011, 2012): {"rates":"zero",    "usd":"stable", "geo":"high",   "jp":"東日本大震災・欧州債務", "en":"EU Debt Crisis"},
    (2013, 2015): {"rates":"zero",    "usd":"strong", "geo":"medium", "jp":"アベノミクス",       "en":"Abenomics"},
    (2016, 2017): {"rates":"rising",  "usd":"strong", "geo":"medium", "jp":"トランプ相場",       "en":"Trump Rally"},
    (2018, 2019): {"rates":"peak",    "usd":"strong", "geo":"medium", "jp":"米中貿易摩擦",       "en":"US-China Trade War"},
    (2020, 2020): {"rates":"zero",    "usd":"weak",   "geo":"high",   "jp":"コロナパンデミック", "en":"COVID Pandemic"},
    (2021, 2021): {"rates":"zero",    "usd":"weak",   "geo":"medium", "jp":"コロナ回復",         "en":"COVID Recovery"},
    (2022, 2022): {"rates":"rising",  "usd":"strong", "geo":"high",   "jp":"利上げ・ウクライナ", "en":"Rate Hikes/Ukraine"},
    (2023, 2023): {"rates":"peak",    "usd":"strong", "geo":"high",   "jp":"高金利継続",         "en":"High Rate Plateau"},
    (2024, 2025): {"rates":"falling", "usd":"strong", "geo":"high",   "jp":"利下げ模索",         "en":"Rate Cut Watch"},
}

def get_regime(year: int) -> dict:
    for (y0, y1), regime in MACRO_REGIMES.items():
        if y0 <= year <= y1:
            return {**regime, "year_range": f"{y0}-{y1}"}
    return {"rates":"stable","usd":"stable","geo":"medium",
            "jp":"データなし","en":"Unknown","year_range":"N/A"}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: 相似度评分（similarity_cache.json）
# ─────────────────────────────────────────────────────────────────────────────
def compute_similarity_score(year1: int, year2: int,
                              df: pd.DataFrame, month: int) -> float:
    """
    综合相似度评分 = 宏观环境(40%) + 价格形态相关性(60%)
    """
    r1, r2 = get_regime(year1), get_regime(year2)
    score = 0.0

    # --- 宏观环境匹配（40%）---
    if r1["rates"] == r2["rates"]: score += 0.20
    if r1["usd"]   == r2["usd"]:   score += 0.10
    if r1["geo"]   == r2["geo"]:   score += 0.10

    # --- 价格形态相关性（60%）---
    def get_norm_series(y, m):
        mask = (df["date"].dt.year == y) & (df["date"].dt.month == m)
        s = df[mask]["close"].dropna().values
        if len(s) < 5:
            return None
        mn, mx = s.min(), s.max()
        if mx - mn < 1e-10:
            return None
        return (s - mn) / (mx - mn)

    s1 = get_norm_series(year1, month)
    s2 = get_norm_series(year2, month)

    if s1 is not None and s2 is not None:
        min_len = min(len(s1), len(s2))
        s1, s2 = s1[:min_len], s2[:min_len]
        corr = np.corrcoef(s1, s2)[0, 1]
        if not np.isnan(corr):
            score += 0.60 * max(0.0, float(corr))

    return round(min(score, 1.0), 4)


def build_similarity_cache(all_data: dict, top_n: int = 8) -> dict:
    """
    为每个（资产, 月份）组合，预计算历史最相似的N个年份。
    缓存结构：
    {
        "gold_usd": {
            "1": [ {year, similarity, return, regime, ...}, ... ],  # 1月
            "2": [ ... ],
            ...
        },
        "sp500": { ... },
        ...
    }
    """
    cache = {}
    current_year = datetime.now().year

    for asset_key in MAIN_ASSETS:
        df = all_data.get(asset_key, pd.DataFrame())
        if df.empty:
            print(f"  ⚠️  {asset_key} 无数据，跳过相似度计算")
            continue

        print(f"\n  🔍 计算 {asset_key} 相似度...")
        cache[asset_key] = {}

        available_years = sorted(df["date"].dt.year.unique())
        candidate_years = [y for y in available_years if 1970 <= y < current_year]

        for month in range(1, 13):
            print(f"     月份 {month:2d}/12 ...", end="\r")
            results = []

            for hist_year in candidate_years:
                # 检查该年该月有没有足够数据
                mask = ((df["date"].dt.year == hist_year) &
                        (df["date"].dt.month == month))
                month_data = df[mask]
                if len(month_data) < 3:
                    continue

                sim = compute_similarity_score(current_year, hist_year, df, month)

                # 月度涨跌幅
                first_close = month_data["close"].iloc[0]
                last_close  = month_data["close"].iloc[-1]
                monthly_ret = round((last_close / first_close - 1) * 100, 3)

                # 日线序列（标准化为涨跌幅%）
                pct_series = ((month_data["close"] / first_close - 1) * 100).tolist()
                pct_series = [round(v, 3) for v in pct_series]
                dates_series = month_data["date"].dt.strftime("%Y-%m-%d").tolist()

                regime = get_regime(hist_year)

                results.append({
                    "year":       int(hist_year),
                    "similarity": float(sim),
                    "return":     float(monthly_ret),
                    "regime": {
                        "rates":      regime["rates"],
                        "usd":        regime["usd"],
                        "geo":        regime["geo"],
                        "label_jp":   regime["jp"],
                        "label_en":   regime["en"],
                        "year_range": regime["year_range"],
                    },
                    # 日线走势数据（用于图表）
                    "dates":  dates_series,
                    "series": pct_series,
                })

            # 按相似度降序，取TOP N
            results.sort(key=lambda x: x["similarity"], reverse=True)
            cache[asset_key][str(month)] = results[:top_n]

        print(f"  ✅ {asset_key} 完成，共 12 个月")

    return cache


def build_current_year_data(all_data: dict) -> dict:
    """
    提取当年每个月的日线数据，存入JSON，供 app.py 右侧面板使用。
    """
    current_year = datetime.now().year
    result = {}

    for asset_key in MAIN_ASSETS:
        df = all_data.get(asset_key, pd.DataFrame())
        if df.empty:
            continue
        result[asset_key] = {}

        for month in range(1, 13):
            mask = ((df["date"].dt.year == current_year) &
                    (df["date"].dt.month == month))
            month_data = df[mask]
            if len(month_data) < 1:
                result[asset_key][str(month)] = None
                continue

            first_close = month_data["close"].iloc[0]
            last_close  = month_data["close"].iloc[-1]
            monthly_ret = round((last_close / first_close - 1) * 100, 3)

            result[asset_key][str(month)] = {
                "dates":   month_data["date"].dt.strftime("%Y-%m-%d").tolist(),
                "closes":  [round(float(v), 4) for v in month_data["close"].tolist()],
                "series":  [round(float((v / first_close - 1) * 100), 3)
                            for v in month_data["close"].tolist()],
                "return":  float(monthly_ret),
                "latest_close": round(float(last_close), 4),
                "latest_date":  month_data["date"].iloc[-1].strftime("%Y-%m-%d"),
            }

    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: 辅助数据处理（DXY、WTI、CFTC、央行购金）
# ─────────────────────────────────────────────────────────────────────────────
def process_auxiliary_data(all_data: dict) -> dict:
    """
    处理辅助数据，生成 ticker 和 宏观指标摘要。
    """
    result = {}

    # --- DXY 美元指数 ---
    dxy = all_data.get("dxy", pd.DataFrame())
    if not dxy.empty:
        latest_dxy = dxy.iloc[-1]
        prev_dxy   = dxy.iloc[-2] if len(dxy) > 1 else latest_dxy
        chg_dxy    = (latest_dxy["close"] / prev_dxy["close"] - 1) * 100
        result["dxy"] = {
            "latest": round(float(latest_dxy["close"]), 2),
            "date":   latest_dxy["date"].strftime("%Y-%m-%d"),
            "change_pct": round(float(chg_dxy), 3),
        }

    # --- WTI 原油 ---
    wti = all_data.get("wti", pd.DataFrame())
    if not wti.empty:
        latest_wti = wti.iloc[-1]
        prev_wti   = wti.iloc[-2] if len(wti) > 1 else latest_wti
        chg_wti    = (latest_wti["close"] / prev_wti["close"] - 1) * 100
        result["wti"] = {
            "latest": round(float(latest_wti["close"]), 2),
            "date":   latest_wti["date"].strftime("%Y-%m-%d"),
            "change_pct": round(float(chg_wti), 3),
        }

    # --- 金油比 (Gold/Oil Ratio) ---
    gold = all_data.get("gold_usd", pd.DataFrame())
    if not gold.empty and not wti.empty:
        # 按日期对齐后计算比值
        g = gold[["date","close"]].rename(columns={"close":"gold_close"})
        w = wti[["date","close"]].rename(columns={"close":"wti_close"})
        merged = pd.merge(g, w, on="date", how="inner")
        if not merged.empty:
            merged["ratio"] = merged["gold_close"] / merged["wti_close"]
            latest_ratio = merged.iloc[-1]
            avg_5y = merged.tail(5*252)["ratio"].mean()  # 近5年均值
            result["gold_oil_ratio"] = {
                "latest": round(float(latest_ratio["ratio"]), 2),
                "avg_5y": round(float(avg_5y), 2),
                "date":   latest_ratio["date"].strftime("%Y-%m-%d"),
                "status": "high" if latest_ratio["ratio"] > avg_5y * 1.1 else
                          ("low" if latest_ratio["ratio"] < avg_5y * 0.9 else "normal"),
            }

    # --- CFTC 黄金持仓 ---
    cftc = all_data.get("cftc_gold", pd.DataFrame())
    if not cftc.empty:
        # 找净多头列
        net_col = next(
            (c for c in cftc.columns if "net" in c.lower() or "noncomm" in c.lower()),
            None
        )
        if net_col:
            latest_cftc = cftc.dropna(subset=[net_col]).iloc[-1]
            result["cftc_gold"] = {
                "net_long": round(float(latest_cftc[net_col]), 0),
                "date":     latest_cftc["date"].strftime("%Y-%m-%d"),
                "column_used": net_col,
            }

    # --- 央行购金 ---
    wgc = all_data.get("wgc_cb", pd.DataFrame())
    if not wgc.empty:
        # 找购金量列
        qty_col = next(
            (c for c in wgc.columns if "ton" in c.lower() or "purchase" in c.lower()
             or "demand" in c.lower() or "net" in c.lower()),
            None
        )
        if qty_col:
            annual_cb = (
                wgc.dropna(subset=[qty_col])
                .groupby(wgc["date"].dt.year)[qty_col]
                .sum()
                .tail(5)
                .reset_index()
            )
            annual_cb.columns = ["year","tonnes"]
            result["central_bank_gold"] = {
                "annual_data": [
                    {"year": int(r["year"]), "tonnes": round(float(r["tonnes"]), 1)}
                    for _, r in annual_cb.iterrows()
                ],
                "column_used": qty_col,
            }

    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: Ticker 最新价格快照
# ─────────────────────────────────────────────────────────────────────────────
def build_ticker_snapshot(all_data: dict) -> list:
    """
    提取所有资产的最新收盘价和日涨跌幅，用于顶部 ticker 栏。
    """
    ticker_assets = [
        ("gold_usd", "XAU/USD"),
        ("gold_jpy", "円建て金"),
        ("sp500",    "SPX"),
        ("usdjpy",   "USD/JPY"),
        ("eurjpy",   "EUR/JPY"),
        ("dxy",      "DXY"),
        ("wti",      "WTI"),
    ]
    snapshot = []
    for asset_key, symbol in ticker_assets:
        df = all_data.get(asset_key, pd.DataFrame())
        if df.empty or len(df) < 2:
            continue
        latest = df.iloc[-1]
        prev   = df.iloc[-2]
        chg_pct = (latest["close"] / prev["close"] - 1) * 100
        snapshot.append({
            "asset":      asset_key,
            "symbol":     symbol,
            "price":      round(float(latest["close"]), 4),
            "change_pct": round(float(chg_pct), 3),
            "date":       latest["date"].strftime("%Y-%m-%d"),
            "positive":   bool(chg_pct >= 0),
        })
    return snapshot


# ─────────────────────────────────────────────────────────────────────────────
# MAIN: 主函数
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  TrueFin precompute.py")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── 1. 加载所有CSV ──────────────────────────────
    print("\n📁 加载原始数据...")
    all_data = {}
    for key in CSV_MAP:
        all_data[key] = load_csv(key)

    # ── 2. 月度统计 (monthly_stats.json) ──────────
    print("\n📊 计算月度统计...")
    monthly_stats_all = {}
    heatmap_all       = {}

    for asset_key in MAIN_ASSETS:
        df = all_data.get(asset_key, pd.DataFrame())
        print(f"  处理 {asset_key}...")
        monthly_stats_all[asset_key] = compute_monthly_stats(df)
        heatmap_all[asset_key]       = compute_heatmap_matrix(df)

    output_monthly = {
        "generated_at": datetime.now().isoformat(),
        "assets":       ASSET_META,
        "data":         monthly_stats_all,
    }
    out_path = OUTPUT_DIR / "monthly_stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_monthly, f, ensure_ascii=False, indent=2)
    print(f"\n  ✅ 写入 {out_path}")

    # ── 3. 热力图矩阵 (heatmap_matrix.json) ───────
    output_heatmap = {
        "generated_at": datetime.now().isoformat(),
        "data":         heatmap_all,
    }
    out_path = OUTPUT_DIR / "heatmap_matrix.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_heatmap, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 写入 {out_path}")

    # ── 4. Ticker 快照 ──────────────────────────────
    ticker_snapshot = build_ticker_snapshot(all_data)

    # ── 5. 当年数据 ─────────────────────────────────
    print("\n📅 提取当年数据...")
    current_year_data = build_current_year_data(all_data)

    # ── 6. 辅助数据（金油比、CFTC、央行购金）─────
    print("\n🔧 处理辅助数据...")
    aux_data = process_auxiliary_data(all_data)
    print("  辅助数据项目:", list(aux_data.keys()))

    # ── 7. 相似度缓存 (similarity_cache.json) ─────
    print("\n🤖 计算历史相似度（最慢步骤，约1-3分钟）...")
    similarity_cache = build_similarity_cache(all_data, top_n=8)

    output_similarity = {
        "generated_at":    datetime.now().isoformat(),
        "current_year":    datetime.now().year,
        "ticker":          ticker_snapshot,
        "current_year_data": current_year_data,
        "auxiliary":       aux_data,
        "similarity":      similarity_cache,
    }
    out_path = OUTPUT_DIR / "similarity_cache.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_similarity, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 写入 {out_path}")

    # ── 完成 ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  🎉 预计算完成！")
    print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n  输出文件：")
    for f in sorted(OUTPUT_DIR.glob("*.json")):
        size_kb = f.stat().st_size / 1024
        print(f"    {f.name:30s} {size_kb:8.1f} KB")
    print("\n  下一步：将 data/precomputed/*.json 上传到 Hugging Face")
    print("=" * 60)


if __name__ == "__main__":
    main()
