import pandas as pd
import numpy as np
import yfinance as yf


def filter_universe(securities, current_time, lookback, percentile):
    """
    Filters liquid securities from the full universe, by referencing historical data
    and quantiling market value and relative spreads of securities.

    Args:
        securities (List (Symbol (str)): list of security symbols
        current_time (datetime.datetime): current_time
        lookback (int): number of days to look back and download historical data
        percentile (float): quantile threshold to be considered liquid

    Returns:
        filtered_securities (List (Symbol (str))
    """
    # Downloads historical data and preprocess
    close, high, low, volume = _download_and_preprocess_data(securities, current_time, lookback)

    # Calculating market value and relative spreads
    securities_and_market_values, securities_and_relative_spread =\
        _calculate_filtering_indicators(close, high, low, volume)

    # Quantile filtering securities by market values and relative spreads
    filtered_securities = _filter_by_quantile(securities,
                                              securities_and_market_values,
                                              securities_and_relative_spread,
                                              percentile)

    return filtered_securities


def _download_and_preprocess_data(securities, current_time, lookback):
    """
    Calls yfinance to download historical daily bars for securities, and perform some basic cleaning.

    Args:
        securities (List (Symbol (str)): list of security symbols
        current_time (datetime.datetime): current_time
        lookback (int): number of days to look back and download historical data

    Returns:
        Data (Tuple (close (pd.DataFrame), high(pd.DataFrame), low(pd.DataFrame), volume(pd.DataFrame))
    """
    # Downloading data
    historical_data = yf.download(tickers=securities,
                                  start=current_time - pd.Timedelta(days=lookback),
                                  end=current_time,
                                  show_errors=False)

    historical_data = historical_data.dropna(axis=1)

    # Extracting raw data for processing
    close = historical_data['Adj Close']
    high = historical_data['High']
    low = historical_data['Low']
    volume = historical_data['Volume']

    return close, high, low, volume


def _calculate_filtering_indicators(close, high, low, volume):
    """
    Calculate market value and relative spread indicators to be used for filtering.

    Args:
        close (pd.DataFrame
            {Date (datetime.datetime): {security(str): close_prices (List(float))}}

        high (pd.DataFrame)
        low (pd.DataFrame)
        volume (pd.DataFrame)

    Returns:
        indicators (Tuple
         (securities_and_market_values (pd.Series), securities_and_relative_spread (pd.Series)))
    """
    market_value = close * volume
    log_close = np.log(close)
    log_mid = (np.log(high) + np.log(low)) / 2
    log_mid_shifted = log_mid.shift(-1)  # eta_{t+1}

    raw_indicator = 4 * (log_close - log_mid) * (log_close - log_mid_shifted)
    raw_indicator = raw_indicator.applymap(lambda x: max(x, 0))
    securities_and_market_values = market_value.sum(axis=0)
    securities_and_relative_spread = raw_indicator.mean(axis=0)

    return securities_and_market_values, securities_and_relative_spread


def _filter_by_quantile(securities, securities_and_market_values,
                        securities_and_relative_spread, percentile):
    """
    Filters securities which satisfy top percentile for traded market value in the historical period,
    and satisfy top percentile for narrowest relative spread.

    Args:
        securities (List (str))
        securities_and_market_values (pd.Series)
        securities_and_relative_spread (pd.Series)
        percentile (float)

    Returns:
        filtered_securities (List (str))
    """
    # Calculate quantiles
    market_value_threshold = securities_and_market_values.quantile(1 - percentile)

    # Daily bar estimation errors for relative spread are quite high,
    # so use a less strict quantile for relative spread
    relative_spread_threshold = securities_and_relative_spread.quantile(.5)

    filtered_securities = []
    for security in securities:
        # remove securities that are delisted and have no historical data
        # or fail to meet market value / relative spread criterias
        if securities_and_market_values.get(security) is None or \
                securities_and_relative_spread.get(security) is None or \
                securities_and_market_values.get(security) < market_value_threshold or \
                securities_and_relative_spread.get(security) > relative_spread_threshold:
            continue

        filtered_securities.append(security)

    return filtered_securities
