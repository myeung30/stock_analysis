import yfinance as yf
from datetime import datetime
import pytz

end_date = datetime.now(tz=pytz.timezone('US/Eastern')).strftime("%Y-%m-%d")
data_aapl= yf.download('AAPL', start='2024-01-01', end=end_date)
print(data_aapl.iloc[-1])

data_aapl= yf.download('AAPL', start='2024-01-01', end=datetime.now())
print(data_aapl.iloc[-1])

current_datetime = datetime.now()
print(current_datetime.tzinfo)