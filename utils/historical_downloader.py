import pandas as pd
import os
import csv
import requests

ALPHAVANTAGE_BASE_URL = 'https://www.alphavantage.co/query?'
API_KEY = os.environ.get('ALPHAVANTAGE_API_KEY')


def download_historical_bar_data(symbol, barsize, lookback):
    """
    Downloads historical time bars and parses data as a pandas DataFrame.

    Internally, "alphavantage.timeseres.TimeSeries.get_intraday_extended" method
    is called, and official documentation can be found at:
        - https://www.alphavantage.co/documentation/#intraday-extended

    Args:
        symbol (str): security symbol to download data for
        bar_size (str): size of each time bar, e.g. '1min', '5min', '15min', '30min, '60min'
        lookback (str): how far back to look back. This function always downloads 30 day data,
            up to 2 years back in time. Accepts 'year1month1' to 'year2month12' as arguments,
            'year1month1' being the most recent and 'year2month12' being the farthest from today.

    Returns:
        bar_data_df (pd.DataFrame
            {'time' (datetime.datetime): {'open': List(float),
                                        'high': List(float),
                                        'low': List(float),
                                        'close': List(float),
                                        'volume': List(float)}})
    """
    # Initialising parameters and requesting raw data
    params = {'function': 'TIME_SERIES_INTRADAY_EXTENDED',
              'symbol': symbol,
              'interval': barsize,
              'slice': lookback,
              'apikey': API_KEY}

    response = requests.get(ALPHAVANTAGE_BASE_URL, params=params)

    # Parsing raw data into DataFrame
    decoded_content = response.content.decode('utf-8')
    reader = csv.reader(decoded_content.splitlines(), delimiter=',')
    bar_data_df = pd.DataFrame(reader)

    # Final touches and cleaning
    bar_data_df.columns = bar_data_df.loc[0]
    bar_data_df = bar_data_df.drop(0).set_index('time')
    bar_data_df = bar_data_df.applymap(lambda x: round(float(x), 2))
    bar_data_df = bar_data_df.sort_index()
    bar_data_df.index = bar_data_df.index.map(pd.to_datetime)

    return bar_data_df
