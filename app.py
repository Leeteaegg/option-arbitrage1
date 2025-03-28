import streamlit as st
import pandas as pd
import numpy as np

# === 使用者輸入參數 === #
st.sidebar.title("選擇權套利回測工具")
STRIKE_PRICE = st.sidebar.number_input("履約價 (Strike Price)", value=18970)
DAYS_TO_EXPIRATION = st.sidebar.number_input("剩餘天數 (Days to Expiration)", value=7)
OPTION_TYPE = st.sidebar.selectbox("選擇權類型 (Option Type)", ["call", "put"])
ARBITRAGE_THRESHOLD = st.sidebar.slider("套利門檻 (%)", 0.01, 0.50, 0.1)

# === 選擇權價格估算（簡易模型） === #
def calculate_fair_price(futures_price, strike_price, days_to_expiration, option_type):
    if option_type == "call":
        return max(futures_price - strike_price, 0)
    elif option_type == "put":
        return max(strike_price - futures_price, 0)
    else:
        return 0

# === 模擬歷史資料 === #
def fetch_historical_data():
    dates = pd.date_range(start="2024-03-01", periods=10, freq="D")
    prices = np.linspace(18800, 19100, len(dates))  # 模擬期貨價格上漲
    return pd.DataFrame({"日期": dates, "期貨價格": prices})

# === 執行回測 === #
def backtest():
    data = fetch_historical_data()
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
st.title("📈 選擇權套利策略回測")
result_df = backtest()
st.dataframe(result_df, use_container_width=True)

# 繪圖
st.line_chart(result_df.set_index("日期")["期貨價格"], height=300)
