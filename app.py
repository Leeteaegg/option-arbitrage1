import streamlit as st
import pandas as pd
import numpy as np
import shioaji as sj
import os
from dotenv import load_dotenv
from datetime import datetime

# 載入 .env 環境變數
load_dotenv()

# === 登入 Shioaji API（永豐證券）=== #
def login_shioaji():
    try:
        api = sj.Shioaji(simulation=True)  # 建議先用模擬帳號測試
        person_id = os.getenv("SHIOAJI_PERSON_ID")
        password = os.getenv("SHIOAJI_PASSWORD")
        if not person_id or not password:
            st.error("❌ 尚未設定 API 登入資訊，請檢查 .env 檔案。")
            return None
        login_info = api.login(person_id=person_id, password=password)
        st.success("✅ 成功登入 Shioaji")
        return api
    except Exception as e:
        st.error(f"❌ Shioaji 登入失敗: {e}")
        return None

api = login_shioaji()

# === 使用者輸入參數 === #
st.sidebar.title("選擇權套利回測工具（Shioaji API 即時資料）")
STRIKE_PRICE = st.sidebar.number_input("履約價 (Strike Price)", value=18970)
DAYS_TO_EXPIRATION = st.sidebar.number_input("剩餘天數 (Days to Expiration)", value=7)
OPTION_TYPE = st.sidebar.selectbox("選擇權類型 (Option Type)", ["call", "put"])
ARBITRAGE_THRESHOLD = st.sidebar.slider("套利門檻 (%)", 0.01, 0.50, 0.1)

# === 即時取得台指期價格（TXF 近月合約）=== #
def fetch_realtime_futures_price():
    if api is None:
        return None
    try:
        contracts = api.Contracts.Futures.TXF
        contract = [c for c in contracts.values()][0]  # 自動抓最近月合約
        quote = api.quote(contract)
        return float(quote.close)
    except Exception as e:
        st.error(f"❌ 無法取得報價: {e}")
        return None

# === 建立即時資料格式 === #
def fetch_historical_data():
    price = fetch_realtime_futures_price()
    if price is None:
        return pd.DataFrame()
    now = pd.Timestamp.now()
    return pd.DataFrame({"日期": [now], "期貨價格": [price]})

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
st.title("📈 選擇權套利策略回測（Shioaji 即時資料）")
result_df = backtest()
if not result_df.empty:
    st.dataframe(result_df, use_container_width=True)
    st.line_chart(result_df.set_index("日期")["期貨價格"], height=300)
