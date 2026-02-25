---
title: TrueFin
emoji: 🟡
colorFrom: yellow
colorTo: yellow
sdk: streamlit
sdk_version: 1.32.0
app_file: app.py
pinned: true
license: mit
short_description: 季節型金融インテリジェンス | Seasonal Financial Intelligence
---

# TrueFin v2.0 — 季節型金融インテリジェンス

**Seasonal Financial Intelligence Platform for Japanese Investors**

## 機能 Features

### 📅 12宮格 季節ヒートマップ
- 1970年〜現在の全月次データを集計
- 月別平均騰落率、勝率、標準偏差を表示
- ゴールド / S&P500 / USD/JPY / EUR/JPY を切替可能

### 🔍 AI 類似相場マッチング (二次画面)
- 月クリックで詳細分析へ遷移
- 金利環境・米ドル強弱・地政学リスクで類似度スコアリング
- 左右分割画面：左＝歴史類似相場、右＝当年データ

### 🌐 多言語 & テーマ
- 日本語 / 英語切替
- ダーク / ライトモード

## データ配置
`data/` フォルダに以下のCSVを配置してください：
- `gold.csv` (date, close)
- `sp500.csv` (date, close)
- `usdjpy.csv` (date, close)
- `eurjpy.csv` (date, close)

データがない場合は合成データで動作します。

## Deploy on Hugging Face Spaces
1. New Space → SDK: Streamlit
2. Upload `app.py`, `requirements.txt`
3. Upload your data files to `data/`
4. Space auto-deploys!
