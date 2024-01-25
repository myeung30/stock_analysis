from flask import Flask, render_template, request, redirect, url_for, session, jsonify, render_template_string
from pymongo import MongoClient
from risk_return_analysis import calculate_risk_return, generate_risk_return_plot, sort_watchlist
from day3_trade import get_stock_data, plot_signals, get_trade_data, calculate_cumulative_percentage_gain
from predict import load_data, preprocess_data, get_last_10_day_predictions
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta
import yfinance as yf

app = Flask(__name__)
app.secret_key = 'your_secret_key'
client = MongoClient('mongodb+srv://9010boris:nHf5FrVDjY1wHBip@cluster0.zrhy4lb.mongodb.net/')
db = client['stock_app']
users_collection = db['users']

def read_stock_list(stock_market):
    file_path = 'stock_market.xlsx'
    market_symbol = pd.read_excel(file_path)
    stock_list = market_symbol[stock_market].dropna().tolist()
    return stock_list

def is_valid_stock(stock_symbol):
    try:
        stock_data = yf.download(stock_symbol, period='1d')
        return not stock_data.empty
    except:
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        user = users_collection.find_one({'username': username, 'password': password})
        if user:
            session['username'] = username

            if 'next' in request.args:
                return redirect(request.args['next'])
            else:
                return redirect(url_for('watchlist', username=username))
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    username = request.form.get('username')
    password = request.form.get('password')

    if users_collection.find_one({'username': username}):
        return render_template('signup.html', error='Username already exists')

    users_collection.insert_one({'username': username, 'password': password, 'watchlist': []})

    return redirect(url_for('watchlist', username=username))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/watchlist/<username>', methods=['GET'])
def watchlist(username):
    user = users_collection.find_one({'username': username})

    if user:
        watchlist = user.get('watchlist', [])
        sp500_tickers = read_stock_list('sp500')
        hk_tickers = read_stock_list('hk_market')

        return render_template('watchlist.html', username=username, watchlist=watchlist, sp500_tickers=sp500_tickers, hk_tickers=hk_tickers)
    else:
        return redirect(url_for('login'))

@app.route('/watchlist', methods=['GET'])
def watchlist_redirect():
    if 'username' in session:
        return redirect(url_for('watchlist', username=session['username']))
    else:
        return redirect(url_for('login'))

@app.route('/add_stock', methods=['POST'])
def add_stock():
    username = request.form.get('username')
    stock_symbol = request.form.get('stock_symbol').upper()

    if not is_valid_stock(stock_symbol):
        return redirect(url_for('watchlist', username=username, error='Invalid stock symbol'))

    user = users_collection.find_one({'username': username, 'watchlist': stock_symbol})

    if user:
        return redirect(url_for('watchlist', username=username, error='Stock already in watchlist'))

    users_collection.update_one({'username': username}, {'$push': {'watchlist': stock_symbol}})

    return redirect(url_for('watchlist', username=username))

@app.route('/add_risk_return_stock', methods=['POST'])
def add_risk_return_stock():
    username = request.form.get('username')
    stock_symbol = request.form.get('stock_symbol').upper()

    if not is_valid_stock(stock_symbol):
        return redirect(url_for('watchlist', username=username, error='Invalid stock symbol'))

    user = users_collection.find_one({'username': username, 'watchlist': stock_symbol})

    if user:
        return redirect(url_for('watchlist', username=username, error='Stock already in watchlist'))

    users_collection.update_one({'username': username}, {'$push': {'watchlist': stock_symbol}})

    return redirect(url_for('risk_return', username=username))

@app.route('/remove_stock', methods=['POST'])
def remove_stock():
    username = request.form.get('username')
    stock_symbol = request.form.get('stock_symbol')

    users_collection.update_one({'username': username}, {'$pull': {'watchlist': stock_symbol}})

    return redirect(url_for('watchlist', username=username))

@app.route('/remove_risk_return_stock', methods=['POST'])
def remove_risk_return_stock():
    username = request.form.get('username')
    stock_symbol = request.form.get('stock_symbol')

    users_collection.update_one({'username': username}, {'$pull': {'watchlist': stock_symbol}})

    return redirect(url_for('risk_return', username=username))

@app.route('/risk_return', methods=['GET'])
def risk_return_redirect():
    if 'username' in session:
        return redirect(url_for('risk_return', username=session['username']))
    else:
        return redirect(url_for('login'))

@app.route('/risk_return/<username>', methods=['GET', 'POST'])
def risk_return(username):
    user = users_collection.find_one({'username': username})

    if user:
        

        if request.method == 'POST':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
        else:
            # Default to the past one year if not provided in the form
            start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = datetime.today().strftime('%Y-%m-%d')

        watchlist = user.get('watchlist', [])
        sorted_watchlist = sort_watchlist(watchlist, start_date, end_date)
        risk_return_plot = generate_risk_return_plot(watchlist, start_date, end_date)

        return render_template('risk_return.html', username=username, sorted_watchlist=sorted_watchlist,
                               risk_return_plot=risk_return_plot, start_date=start_date, end_date=end_date)
    else:
        return redirect(url_for('login'))

@app.route('/day3_trade', methods=['GET', 'POST'])
def day3_trade():
    if request.method == 'POST':
        username = session.get('username')
        stock_symbol = request.form.get('stock_symbol')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        change1day = float(request.form.get('change1day'))
        change2day = float(request.form.get('change2day'))

        stock_data = get_stock_data(stock_symbol, start_date, end_date, change2day, change1day)
        img_buf = io.BytesIO()
        plot_signals(stock_data, img_buf)

        trade_data = get_trade_data(stock_data)
        num_trades = len(trade_data)
        cumulative_percentage_gain = calculate_cumulative_percentage_gain(trade_data)

        img_base64 = base64.b64encode(img_buf.getvalue()).decode('utf-8')

        return render_template('day3_trade.html', username=username, result=True,
                               num_trades=num_trades, cumulative_percentage_gain=cumulative_percentage_gain,
                               day3_chart=img_base64, trade_data=trade_data)

    return render_template('day3_trade.html', result=False)

@app.route('/check_stock_data')
def check_stock_data():
    symbol = request.args.get('symbol', '')

    if not symbol:
        return jsonify({'available': False})

    try:
        # Use yfinance to check if data is available for the given stock symbol
        stock_data = yf.download(symbol, start=(datetime.today() - timedelta(days=10)), end=datetime.today())
        if stock_data.empty:
            return jsonify({'available': False})
        else:
            return jsonify({'available': True})
    except Exception as e:
        # Handle exceptions (e.g., invalid stock symbol)
        print(f"Error checking stock data: {e}")
        return jsonify({'available': False})


@app.route('/price_predict', methods=['GET', 'POST'])
def price_predict():
    
    if request.method == 'POST':
        symbol_for_predictions = request.form['symbol']

        start_date_for_training = '2018-01-01'
        end_date_for_training = '2024-01-01'
        data_for_training = load_data(symbol_for_predictions, start_date_for_training, end_date_for_training)
        data_for_training, scaler_tmr, scaler_overnight, model_tmr, model_overnight = preprocess_data(data_for_training)

        last_10_day_predictions, mse_tmr, mse_overnight = get_last_10_day_predictions(symbol_for_predictions, data_for_training.copy(), scaler_tmr, scaler_overnight, model_tmr, model_overnight)

        return render_template('price_predict.html', symbol=symbol_for_predictions, last_10_rows=last_10_day_predictions, mse_tmr=mse_tmr, mse_overnight=mse_overnight)
    else:
        # Define last_10_rows for the initial page load
        last_10_rows = None  # You can set it to an empty DataFrame if you prefer
        return render_template('price_predict.html', last_10_rows=last_10_rows)


if __name__ == '__main__':
    app.run(host="0.0.0.0",port=5000, debug=True)
