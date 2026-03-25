import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as fgo
from plotly.subplots import make_subplots

# --- 頁面配置 ---
st.set_page_config(page_title="底部起漲訊號偵測器", layout="wide")
st.title("📈 底部起漲訊號偵測助手")

# --- 側邊欄參數設定 ---
st.sidebar.header("搜尋與參數設定")
ticker = st.sidebar.text_input("輸入股票代碼 (例如: 2330.TW 或 TSLA)", value="2330.TW")
period = st.sidebar.selectbox("資料時間範圍", ["6mo", "1y", "2y"], index=0)

st.sidebar.subheader("技術指標參數")
ma_short = st.sidebar.slider("短期均線 (EMA)", 5, 20, 5)
ma_long = st.sidebar.slider("長期均線 (EMA)", 10, 60, 20)
rsi_low = st.sidebar.slider("RSI 低檔區間", 20, 40, 30)
vol_factor = st.sidebar.slider("成交量放大倍數", 1.0, 3.0, 1.5)

# --- 數據抓取與計算 ---
@st.cache_data
def load_data(symbol, p):
    df = yf.download(symbol, period=p)
    if df.empty:
        return None
    # 確保欄位名稱正確
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df

data = load_data(ticker, period)

if data is not None:
    # 計算指標
    data['EMA_S'] = ta.ema(data['Close'], length=ma_short)
    data['EMA_L'] = ta.ema(data['Close'], length=ma_long)
    data['RSI'] = ta.rsi(data['Close'], length=14)
    data['Vol_MA'] = ta.sma(data['Volume'], length=5)

    # 判定起漲訊號
    # 1. EMA 金叉
    cond1 = (data['EMA_S'] > data['EMA_L']) & (data['EMA_S'].shift(1) <= data['EMA_L'].shift(1))
    # 2. RSI 脫離低檔
    cond2 = (data['RSI'] > rsi_low) & (data['RSI'].shift(1) < rsi_low)
    # 3. 量能放大
    cond3 = data['Volume'] > (data['Vol_MA'] * vol_factor)

    data['Buy_Signal'] = cond1 & cond2 & cond3

    # --- 視覺化看板 ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=(f'{ticker} 走勢與訊號', 'RSI 指標'),
                        row_width=[0.3, 0.7])

    # K線圖
    fig.add_trace(fgo.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                 low=data['Low'], close=data['Close'], name='K線'), row=1, col=1)
    
    # 均線
    fig.add_trace(fgo.Scatter(x=data.index, y=data['EMA_S'], name=f'EMA {ma_short}', line=dict(width=1)), row=1, col=1)
    fig.add_trace(fgo.Scatter(x=data.index, y=data['EMA_L'], name=f'EMA {ma_long}', line=dict(width=1)), row=1, col=1)

    # 標記訊號點
    signals = data[data['Buy_Signal'] == True]
    fig.add_trace(fgo.Scatter(x=signals.index, y=signals['Low'] * 0.98, mode='markers',
                             marker=dict(symbol='triangle-up', size=12, color='#00FF00'),
                             name='起漲訊號'), row=1, col=1)

    # RSI 圖
    fig.add_trace(fgo.Scatter(x=data.index, y=data['RSI'], name='RSI', line=dict(color='purple')), row=2, col=1)
    fig.add_hline(y=rsi_low, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- 訊號清單 ---
    st.subheader("📋 近期觸發訊號清單")
    if not signals.empty:
        display_df = signals[['Close', 'Volume', 'RSI']].tail(10).sort_index(ascending=False)
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("目前設定參數下無符合之起漲訊號。")

else:
    st.error("無法取得數據，請檢查代碼是否正確。")
