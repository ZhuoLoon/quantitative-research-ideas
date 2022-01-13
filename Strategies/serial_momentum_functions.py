import numpy as np
import pandas as pd

from itertools import product as cartesian_product
from functools import partial
from scipy.stats import pearsonr
from numpy_ext import rolling_apply
from multiprocessing import cpu_count


def create_portfolio_positions(price_data, past_returns, hurst_exponents,
                               forward, entry_hurst, exit_hurst):
    """
    Creates a portfolio based on a lookback-forward period pair. The idea is that
    if past returns are +ve (-ve), then we bet that future returns are also +ve (-ve).

    Hurst exponents are also used to check the behaviour of the current regime.
    We enter trades if we believe regime is trending, and exit when its mean-reverting.

    Args:
        price_data (pd.DataFrame)
        past_returns (pd.Series): past returns based on a lookback period
        hurst_exponents (np.array[float]):
            rolling hurst exponent calculations using lookback as window size.
        forward (int): holding period (A.K.A time stop)
        entry_hurst (float): hurst threshold to consider regime as trending
        exit_hurst (float): hurst threshold to consider regime as mean-reverting.

    Returns:
        portfolio_positions (pd.Series): entry and exit behaviour
        portfolio_ratios (pd.DataFrame): ratios of securities in unit portfolio
    """
    portfolio_positions = np.zeros(past_returns.size)
    trade_entry_index = 0

    for index in range(1, portfolio_positions.size):
        # hurst exponent above entry threshold, regime likely to be trending, enter trade
        if hurst_exponents[index] > entry_hurst and not trade_entry_index:
            # long if past returns positive, short if negative
            portfolio_positions[index] = np.sign(past_returns[index])
            trade_entry_index = index

        # hurst exponent below exit threshold, regime likely changed to mean reverting, exit trade
        if hurst_exponents[index] < exit_hurst:
            portfolio_positions[index] = 0
            trade_entry_index = 0

        # hurst exponent doesn't hit any threshold, but reached maximum holding period
        if portfolio_positions[index - 1] != 0 and (index - trade_entry_index) > forward:
            portfolio_positions[index] = 0
            trade_entry_index = 0

        # forward filling positions when time/pnl stops not hit
        if portfolio_positions[index - 1] != 0 and trade_entry_index:
            portfolio_positions[index] = portfolio_positions[index - 1]

    # convert data structures to necessary formats for grid search
    portfolio_positions = pd.Series(portfolio_positions, index=price_data.index)
    portfolio_ratios = np.sign(price_data)

    return portfolio_positions, portfolio_ratios


def gridsearch_lookback_forward_periods(prices, parameters):
    """
    Performs a grid search for various lookback and holding periods,
    obtaining corresponding Pearson correlation coefficient values and p values.

    Args:
        prices (np.array[float])
        parameters(Dict{'lookback': array[int],
                        'forward': array[int]})

    Returns:
        results (pd.DataFrame): tabular results of grid search.
    """
    # Create a partial function so that only parameters need to be fed.
    calculate_correlation =\
        partial(_calculate_past_future_returns_correlation, prices=prices)

    # Grid search
    results = []
    keys = parameters.keys()
    for combination in cartesian_product(*parameters.values()):
        parameter_combination = dict(zip(keys, combination))

        # calculate correlation between past and future returns
        correlation_coefficient, p_value = calculate_correlation(**parameter_combination)
        parameter_combination['correlation_coefficient'] = correlation_coefficient
        parameter_combination['p_value'] = p_value
        results.append(parameter_combination)

    # convert results into a tabular form
    results = pd.DataFrame(results)
    return results


def generate_hurst_array(log_prices, rolling_window):
    """
    Generates an array of rolling hurst exponent calculations.

    Args:
        log_prices (np.array[float]): array of log price data
        rolling_window (int): size of rolling window.

    Returns:
        hurst_values (np.array[float])
    """
    # use numpy_ext parallel rolling window calculations
    hurst_values = rolling_apply(_calculate_hurst,
                                 rolling_window,
                                 log_prices,
                                 n_jobs=cpu_count()-1)

    return hurst_values


def _calculate_past_future_returns_correlation(prices, lookback, forward):
    """
    Calculates the Pearson correlation coefficient between past and future returns,
    based on the provided lookback and forward periods.

    Args:
        prices (np.array[float])
        lookback (int): lookback period
        forward (int): forward period

    Returns:
        correlation_coefficient(float): Pearson coefficient
        p_values (float): probability of an uncorrelated system producing this result
    """
    window = min(lookback, forward)
    index = range(lookback, prices.size - forward, window)

    lookback_returns = []
    forward_returns = []

    for i in index:
        lookback_returns.append((prices[i] -  prices[i-lookback]) / prices[i-lookback])
        forward_returns.append((prices[i+forward] - prices[i]) / prices[i])

    correlation_coefficient, p_value = pearsonr(lookback_returns, forward_returns)
    return correlation_coefficient, p_value


def _calculate_hurst(log_prices):
    """
    Calculates hurst exponent of a log price series. Hurst Exponent provides
    us with a scalar value that identifies whether a series is mean reverting,
    random walking or trending.

    For an array x of n values and time lag τ, we have the following relation:
                        (1/n-τ) * Σ (x_{i+τ} - x_i)**2  ~ τ^{2H}

    The values of H can be estimated by linear regression, and the prices are
    believed to be:
                            Mean Reverting <--> H << 0.5
                            Geometric Brownian Motion <--> H ~= 0.5
                            Trending <--> H >> 0.5

    Args:
        log_prices (np.array[float])

    Returns:
        hurst_exponent (float)
    """
    lag_values = range(1, log_prices.size // 2)
    variances = []

    for lag in lag_values:
        variance = np.mean((log_prices[lag:] - log_prices[:-lag]) ** 2)
        variances.append(variance)

    regression_gradient = np.polyfit(np.log(lag_values), np.log(variances), 1)[0]
    hurst_exponent = 0.5 * regression_gradient
    return hurst_exponent
