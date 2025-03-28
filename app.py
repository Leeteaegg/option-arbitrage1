import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# === 串接永豐 API === #
from sinotrade import SinopacAPI
import os

# 從環境變數讀取 API 金鑰與帳號（請自行在 Replit / 本地設定）
api_key = os.getenv("SINOTRADE_API_KEY")
secret_key = os.getenv("SINOTRADE_SECRET_KEY")
account_id = os.getenv("SINOTRADE_ACCOUNT_ID")

# 登入永豐 API（請確保環境變數已正確設定）
api = SinopacAPI(api_key, secret_key, account_id)
api.login()

# === 使用者輸入參數 === #
st.sidebar.title("選擇權套利回測工具（即時資料）")
STRIKE_PRICE = st.sidebar.number_input("履約價 (Strike Price)", value=18970)
DAYS_TO_EXPIRATION = st.sidebar.number_input("剩餘天數 (Days to Expiration)", value=7)
OPTION_TYPE = st.sidebar.selectbox("選擇權類型 (Option Type)", ["call", "put"])
ARBITRAGE_THRESHOLD = st.sidebar.slider("套利門檻 (%)", 0.01, 0.50, 0.1)

# === 即時取得期貨價格 === #
def fetch_realtime_futures_price():
    futures_data = api.get_futures_price("TXF")  # 台指期近月合約
    return float(futures_data["price"])

# === 建立即時資料格式 === #
def fetch_historical_data():
    try:
        price = fetch_realtime_futures_price()
        now = pd.Timestamp.now()
        return pd.DataFrame({
            "日期": [now],
            "期貨價格": [price]
        })
    except Exception as e:
        st.error(f"❌ 無法取得即時資料：{e}")
        return pd.DataFrame()

# === 選擇權價格估算（簡易模型） === #
def calculate_fair_price(futures_price, strike_price, days_to_expiration, option_type):
    if option_type == "call":
        return max(futures_price - strike_price, 0)
    elif option_type == "put":
        return max(strike_price - futures_price, 0)
    else:
        return 0

# === 執行回測 === #
def backtest():
    data = fetch_historical_data()
    if data.empty:
        return pd.DataFrame()

    result = []
    for _, row in data.iterrows():
        futures_price = row["期貨價格"]
        fair_price = calculate_fair_price(
            futures_price,
            STRIKE_PRICE,
            DAYS_TO_EXPIRATION,
            OPTION_TYPE
        )

        signal = "無套利機會"
        if futures_price < fair_price * (1 - ARBITRAGE_THRESHOLD):
            signal = "建議買入選擇權"
        elif futures_price > fair_price * (1 + ARBITRAGE_THRESHOLD):
            signal = "建議賣出選擇權"

        result.append({
            "日期": row["日期"],
            "期貨價格": futures_price,
            "合理價格": fair_price,
            "套利建議": signal
        })

    return pd.DataFrame(result)

# === 顯示結果 === #
st.title("📈 選擇權套利策略回測（即時版）")
result_df = backtest()
if not result_df.empty:
    st.dataframe(result_df, use_container_width=True)
    st.line_chart(result_df.set_index("日期")["期貨價格"], height=300)
