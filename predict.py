import yfinance as yf
import datetime
import ta
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
import pytz

def load_data(symbol, start_date, end_date):
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    data = yf.download(symbol, start=start_date, end=end_date)
    data['pct_today'] = data['Close'].pct_change() + 1
    data['pct_tmr'] = data['pct_today'].shift(-1)
    data.at[data.index[-1], 'pct_tmr'] = data['pct_today'].iloc[-2]

    data['pct_overnight'] = (data['Open'].shift(-1)) / data['Close']
    data.at[data.index[-1], 'pct_overnight'] = data['pct_overnight'].iloc[-2]

    data['pct_1day'] = data['pct_today'].shift(1)
    data['pct_2day'] = data['pct_today'].shift(2)
    data['10/30_sma'] = (data['Close'].rolling(window=10).mean()) / (data['Close'].rolling(window=30).mean())
    data['50/100_ema'] = (data['Close'].ewm(span=50, adjust=False).mean()) / (data['Close'].ewm(span=100, adjust=False).mean())
    data['100/250_ema'] = (data['Close'].ewm(span=100, adjust=False).mean()) / (data['Close'].ewm(span=250, adjust=False).mean())
    data['low_to_close_pct'] = (data['Low'] - data['Close']) / data['Close']
    data['high_to_close_pct'] = (data['High'] - data['Close']) / data['Close']
    data['momentum_rsi'] = ta.momentum.RSIIndicator(data['Close']).rsi()
    data['macd'] = ta.trend.macd_diff(data['Close'])
    data = data.dropna()

    return data

def preprocess_data(data):
    X = data[
        ['pct_today', 'pct_1day', 'pct_2day', '10/30_sma', '50/100_ema', '100/250_ema', 'low_to_close_pct', 'high_to_close_pct',
         'momentum_rsi', 'macd']]
    y_tmr = data['pct_tmr']
    y_overnight = data['pct_overnight']

    scaler_tmr = StandardScaler()

    # Scale the data for pct_tmr
    X_scaled_tmr = scaler_tmr.fit_transform(X)

    # Train the model for pct_tmr
    model_tmr = RandomForestRegressor(n_estimators=100, random_state=42)
    model_tmr.fit(X_scaled_tmr, y_tmr)

    # Now, similar steps for pct_overnight...
    scaler_overnight = StandardScaler()

    # Scale the data for pct_overnight
    X_scaled_overnight = scaler_overnight.fit_transform(X)

    # Train the model for pct_overnight
    model_overnight = RandomForestRegressor(n_estimators=100, random_state=42)
    model_overnight.fit(X_scaled_overnight, y_overnight)

    return data, scaler_tmr, scaler_overnight, model_tmr, model_overnight

def get_last_10_day_predictions(symbol, data, scaler_tmr, scaler_overnight, model_tmr, model_overnight):
    end_date = datetime.datetime.now(tz=pytz.timezone('Asia/Hong_Kong')).strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=300)).strftime("%Y-%m-%d")
    recent_data = load_data(symbol, start_date, end_date)

    # Preprocess the recent data
    X_recent = recent_data[
        ['pct_today', 'pct_1day', 'pct_2day', '10/30_sma', '50/100_ema', '100/250_ema', 'low_to_close_pct', 'high_to_close_pct',
         'momentum_rsi', 'macd']]
    X_recent_scaled_tmr = scaler_tmr.transform(X_recent)
    X_recent_scaled_overnight = scaler_overnight.transform(X_recent)

    # Make predictions for pct_tmr and pct_overnight
    pct_tmr_prediction = model_tmr.predict(X_recent_scaled_tmr)
    pct_overnight_prediction = model_overnight.predict(X_recent_scaled_overnight)

    # Combine predictions with the original data
    recent_data['Est_pct_close'] = (pct_tmr_prediction - 1) * 100
    recent_data['Est_pct_open'] = (pct_overnight_prediction - 1) * 100
    recent_data['Est_tmr_open'] = recent_data['Close'] * (1 + recent_data['Est_pct_open'] / 100)
    recent_data['Est_tmr_close'] = recent_data['Close'] * (1 + recent_data['Est_pct_close'] / 100)
    recent_data['Real_pct_open'] = ((recent_data['Open'].shift(-1))/recent_data['Close'] - 1) * 100
    recent_data['Real_pct_close'] = ((recent_data['Close'].shift(-1))/recent_data['Close'] - 1) * 100
    recent_data['Real_tmr_open'] = recent_data['Open'].shift(-1)
    recent_data['Real_tmr_close'] = recent_data['Close'].shift(-1)
    dropna_data = recent_data.dropna()

    # Return the last 10 rows of the data and MSE
    last_10_rows = recent_data.tail(10)[['Open', 'Close', 'Est_pct_open', 'Real_pct_open', 'Est_tmr_open', 'Real_tmr_open', 'Est_pct_close', 'Real_pct_close', 'Est_tmr_close', 'Real_tmr_close']]
    mse_tmr = mean_squared_error(dropna_data['Real_pct_close'], dropna_data['Est_pct_close'])
    mse_overnight = mean_squared_error(dropna_data['Real_pct_open'], dropna_data['Est_pct_open'])

    # Return the last 10 rows and MSE
    return last_10_rows, mse_tmr, mse_overnight

