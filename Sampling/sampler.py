import pandas as pd
import numpy as np
import yfinance as yf


def resample_by_volume_clock(time_sampled_data, security, start_date,
                             end_date, trading_intervals, method):
    """
    Resamples data by the volume clock, creating either volume sampled or dollar sampled bars.
    The sampling sizes are determined from historical trading activity.

    Args:
        time_sampled_data (pd.DataFrame
            {'time' (datetime.datetime): {'open': List(float),
                                          'high': List(float),
                                          'low': List(float),
                                          'close': List(float),
                                          'volume': List(float)}}): data sampled by time

        security (str): security symbol
        start_date (str): yfinance start date
        end_date (str): yfinance end date
        trading_intervals (List(tuple(datetime.time(), datetime.time())):
            each pair represents a trading interval for the security.

        method (str): method to do resampling, either 'VOLUME' or 'DOLLAR'

    Returns:
        resampled_data (pd.DataFrame
            {index (int): {'open': List(float),
                           'high': List(float),
                           'low': List(float),
                           'close': List(float),
                           'volume': List(float)}})
    """
    # Downloads historical data
    historical_data = yf.download(tickers=security, start=start_date, end=end_date)

    # Calculate the sampling size
    sampling_size = _calculate_sampling_size(historical_data, trading_intervals, method)

    # Resampling the data
    resampled_data = _resample_by_sampling_size(time_sampled_data, sampling_size, method)

    return resampled_data


def _calculate_sampling_size(historical_data, trading_intervals, method):
    """
    Calculates sampling size to use for each stochastic bar.

    Args:
        historical_data (pd.DataFrame
            {'Date' (datetime.datetime): {'Open': List(float),
                                          'High': List(float),
                                          'Low': List(float),
                                          'Close': List(float),
                                          'Adj Close': List(float),
                                          'Volume': List(float)}})
        trading_intervals (List(tuple(datetime.time(), datetime.time()))
        method (str)

    Returns:
        sampling_size (int): amount of volume/market value to collect before sampling 1 bar
    """
    # calculate total trading minutes in the historical period
    total_days = historical_data.shape[0]
    total_minutes = _calculate_minutes_in_historical_period(trading_intervals, total_days)

    if method.upper() == 'VOLUME':
        total_volume = historical_data.Volume.sum()
        sampling_size = int(total_volume / total_minutes)
    elif method.upper() == 'DOLLAR':
        historical_data['market_value'] = historical_data['Volume'] * historical_data['Adj Close']
        total_market_value = historical_data.market_value.sum()
        sampling_size = int(total_market_value / total_minutes)
    else:
        raise NotImplementedError(f"Resampling method: {method} is not supported!")

    return sampling_size


def _calculate_minutes_in_historical_period(trading_intervals, total_days):
    """
    Helper function to calculate total number of trading minutes in the period used
    for downloading historical data.

    Args:
        trading_intervals (List(tuple(datetime.time(), datetime.time()))
        total_days (int)

    Returns:
        total_minutes (int)
    """
    # calculate number of trading minutes in a day
    minutes_in_a_day = 0
    for interval in trading_intervals:
        # if trading day bleeds over to the next day
        if interval[1] < interval[0]:
            hours = (interval[1].hour - 0) + (24 - interval[0].hour)
        else:
            hours = interval[1].hour - interval[0].hour
        minutes = interval[1].minute - interval[0].minute

        minutes_in_a_day += 60 * hours + minutes

    total_minutes = total_days * minutes_in_a_day
    return total_minutes


def _resample_by_sampling_size(time_sampled_data, sampling_size, method):
    """
    Resamples time sampled data by volume clock, based on the calculated pre-defined
    amount to sample each bar, and the method provided.

    Args:
        time_sampled_data (pd.DataFrame)
        sampling_size (int)
        method (str)

    Returns:
        resampled_data (pd.DataFrame)
    """
    # data structures used to calculate OHLCV for each bar
    # 'sampling' represents either VOLUME or DOLLAR, depending on method.
    prices = time_sampled_data['close'].values
    if method.upper() == 'VOLUME':
        sampling_data = time_sampled_data['volume'].values
    elif method.upper() == 'DOLLAR':
        sampling_data = prices * time_sampled_data['volume'].values
    else:
        raise NotImplementedError(f"Resampling method: {method} is not supported!")

    sampling_counter = 0  # volume/dollar counter
    start_index = 0

    resampled_bars = []
    for current_index in range(len(prices)):
        sampling_counter += sampling_data[current_index]

        number_of_bars_created = int(sampling_counter/ sampling_size)
        if number_of_bars_created > 0:
            for _ in range(number_of_bars_created):
                resampled_bars.append(
                    {'open': prices[start_index: current_index + 1][0],
                     'high': np.max(prices[start_index: current_index + 1]),
                     'low': np.min(prices[start_index: current_index + 1]),
                     'close': prices[start_index: current_index + 1][-1]})

            # Once a bar is created, we update the starting index to be the next data point.
            # This is equivalent to "clearing" the list of trades that is collected one at a time,
            # for bar creation in the events-based version.
            start_index = current_index + 1
            sampling_counter -= number_of_bars_created * sampling_size

    resampled_data = pd.DataFrame(resampled_bars)
    return resampled_data
