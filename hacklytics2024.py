import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Define functions for downloading data and calculating indicators
def download_stock_data(symbol, start_date, end_date):
    return yf.download(symbol, start=start_date, end=end_date)

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(window=period).mean()
    ma_down = down.rolling(window=period).mean()
    rsi = ma_up / (ma_up + ma_down) * 100
    return rsi

def calculate_bbands(series, period=20, num_std_dev=2):
    ma = series.rolling(window=period).mean()
    std_dev = series.rolling(window=period).std()
    upper_band = ma + (std_dev * num_std_dev)
    lower_band = ma - (std_dev * num_std_dev)
    return upper_band, lower_band

def calculate_ma(series, period=20):
    return series.rolling(window=period).mean()

# Define the strategy execution function
def execute_strategy(df, params):
    cash = params.get('starting_cash', 10000)
    shares_held = 0
    trade_prices = []  # This will store the buy prices for calculating sell conditions
    df['Signal'] = ''  # Initialize a column for buy/sell signals

    # Initialize indicators as needed
    if 'Moving_Average' in params['entry_condition']:
        df['MA'] = calculate_ma(df['Close'], params.get('ma_period', 20))
    if 'Bollinger_Bands' in params['entry_condition']:
        df['upper_band'], df['lower_band'] = calculate_bbands(df['Close'], params.get('bb_period', 20), params.get('bb_std_dev', 2))
    if 'RSI_Oversold' in params['entry_condition']:
        df['RSI'] = calculate_rsi(df['Close'], params.get('rsi_period', 14))

    for index, row in df.iterrows():
        if shares_held == 0:
            # Entry conditions
            if 'RSI_Oversold' in params['entry_condition'] and row['RSI'] < params['rsi_oversold_threshold']:
                shares_to_buy = min(params.get('order_size', 10), cash // row['Close'])
                if shares_to_buy > 0:
                    shares_held += shares_to_buy
                    cash -= row['Close'] * shares_to_buy
                    df.at[index, 'Signal'] = 'buy'
                    trade_prices.append(row['Close'])  # Record buy price
            elif 'Bollinger_Bands' in params['entry_condition'] and row['Close'] < row['lower_band']:
                shares_to_buy = min(params.get('order_size', 10), cash // row['Close'])
                if shares_to_buy > 0:
                    shares_held += shares_to_buy
                    cash -= row['Close'] * shares_to_buy
                    df.at[index, 'Signal'] = 'buy'
                    trade_prices.append(row['Close'])  # Record buy price
            elif 'Moving_Average' in params['entry_condition'] and row['Close'] > row['MA']:
                shares_to_buy = min(params.get('order_size', 10), cash // row['Close'])
                if shares_to_buy > 0:
                    shares_held += shares_to_buy
                    cash -= row['Close'] * shares_to_buy
                    df.at[index, 'Signal'] = 'buy'
                    trade_prices.append(row['Close'])  # Record buy price

        elif shares_held > 0 and trade_prices:
            buy_price = trade_prices[-1]  # Use the last recorded buy price for sell conditions
            if 'Profit_Target' in params['exit_condition'] and row['Close'] >= buy_price * (1 + params['profit_target']):
                cash += row['Close'] * shares_held
                shares_held = 0
                df.at[index, 'Signal'] = 'sell'
                trade_prices.pop()  # Remove the last buy price after selling
            elif 'Stop_Loss' in params['exit_condition'] and row['Close'] <= buy_price * (1 - params['stop_loss']):
                cash += row['Close'] * shares_held
                shares_held = 0
                df.at[index, 'Signal'] = 'sell'
                trade_prices.pop()  # Remove the last buy price after selling

    final_portfolio_value = cash + (shares_held * df.iloc[-1]['Close'] if shares_held > 0 else 0)
    return df, final_portfolio_value


# Streamlit UI for input parameters
st.title('Trading Strategy Backtesting App')

starting_cash = st.number_input('Enter starting cash', value=10000, min_value=1000, step=100)

symbol = st.text_input('Enter stock symbol', value='TSLA')
start_date = st.date_input('Start date', value=pd.to_datetime('2020-01-01'))
end_date = st.date_input('End date', value=pd.to_datetime('2023-01-01'))
entry_condition = st.selectbox('Select entry condition', ['RSI_Oversold', 'Bollinger_Bands', 'Moving_Average'])
exit_condition = st.selectbox('Select exit condition', ['Profit_Target', 'Stop_Loss'])

# Display sliders for parameters based on the selected entry condition
params = {'entry_condition': entry_condition, 'exit_condition': exit_condition, 'starting_cash': starting_cash}

if entry_condition == 'RSI_Oversold':
    params['rsi_oversold_threshold'] = st.slider('RSI oversold threshold', 10, 40, 30)
    params['rsi_period'] = st.slider('RSI period', 5, 25, 14)
elif entry_condition == 'Bollinger_Bands':
    params['bb_period'] = st.slider('Bollinger Bands period', 5, 25, 20)
    params['bb_std_dev'] = st.slider('Bollinger Bands std dev', 1, 3, 2)
elif entry_condition == 'Moving_Average':
    params['ma_period'] = st.slider('Moving Average period', 5, 50, 20)

# Display sliders for parameters based on the selected exit condition
if exit_condition == 'Profit_Target':
    params['profit_target'] = st.slider('Profit target (%)', 1, 50, 10) / 100.0
elif exit_condition == 'Stop_Loss':
    params['stop_loss'] = st.slider('Stop loss (%)', 1, 50, 5) / 100.0

params['order_size'] = st.number_input('Order size', min_value=1, value=10, step=1)

# Execute strategy and display results
if st.button('Execute Strategy'):
    data = download_stock_data(symbol, start_date, end_date)
    if not data.empty:
        data, final_value = execute_strategy(data, params)
        st.write(f"Final Portfolio Value: {final_value}")

        # Plotting
        plt.figure(figsize=(14, 7))
        plt.plot(data.index, data['Close'], label='Close Price', alpha=0.5)
        buy_signals = data[data['Signal'] == 'buy']
        sell_signals = data[data['Signal'] == 'sell']
        plt.scatter(buy_signals.index, buy_signals['Close'], color='green', label='Buy', marker='^', alpha=1)
        plt.scatter(sell_signals.index, sell_signals['Close'], color='red', label='Sell', marker='v', alpha=1)
        plt.title(f'Stock Price and Trade Signals for {symbol}')
        plt.xlabel('Date')
        plt.ylabel('Stock Price')
        plt.legend(loc='upper left')
        plt.grid(True)
        st.pyplot(plt)
    else:
        st.error("Could not download stock data. Please check the stock symbol and try again.")
