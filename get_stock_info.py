import yfinance

def get_stock_info(symbol):
    try:
        stock = yfinance.Ticker(symbol)

        latest_info = stock.history(period="1d")['Close'].iloc[0]

        return round(latest_info, 2)
    except:
        return None