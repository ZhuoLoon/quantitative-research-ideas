import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tqdm import tqdm
from functools import partial
from itertools import product as cartesian_product


def calculate_pnl_with_transaction_costs(price_data, positions, portfolio_ratios,
                                         commissions_in_percent, bid_ask_spread, plot=True):
    """
    Calculates performance metrics (annualised returns, sharpe ratio) of a strategy,
    including transactions costs and slippages.

    Args:
        price_data (pd.DataFrame
            {Date (datetime.datetime): {security_1 (str): prices (List[float]),
                                        security_2 (str): prices (List[float]),
                                                        .
                                                        .
                                                        .}})
        positions (pd.Series): positions to take in the unit portfolio
        portfolio_ratios (pd.DataFrame): ratios of each security in the unit portfolio
        commissions_in_percent (float): to model transaction costs
        bid_ask_spread (float): to model transaction costs
        plot (bool): whether to plot daily returns

    Returns:
        annualised_returns (float)
        sharpe_ratio (float)
    """
    # standardise index
    positions.index = price_data.index
    portfolio_ratios.index = price_data.index

    # calculate transaction costs
    transaction_costs = _calculate_transaction_costs(price_data, positions, portfolio_ratios,
                                                     commissions_in_percent, bid_ask_spread)

    # calculate raw pnl
    portfolio_market_values = positions.to_frame().values * portfolio_ratios.values * price_data
    raw_pnl = np.sum(portfolio_market_values.shift().values *
                     price_data.pct_change().values, axis=1)
    raw_pnl = pd.Series(raw_pnl, index=price_data.index)

    # apply transaction costs and calculate performance metrics
    daily_pnl = raw_pnl - transaction_costs
    daily_returns = daily_pnl / np.sum(np.abs(portfolio_market_values .shift()), axis=1)
    daily_returns = daily_returns.replace(-np.inf, np.nan)

    annual_returns = np.prod(1 + daily_returns) ** (252 / len(daily_returns)) - 1
    annual_returns = np.round(annual_returns, 3)
    sharpe_ratio = np.sqrt(252) * np.mean(daily_returns) / np.std(daily_returns)
    sharpe_ratio = np.round(sharpe_ratio, 3)

    if plot:
        plt.plot((1+daily_returns).cumprod().ffill() - 1)
        plt.title("Daily returns")

    return annual_returns, sharpe_ratio


def grid_search(price_data, strategy, hyperparameters, commissions_in_percent, bid_ask_spread):
    """
    Tunes hyperparameters for a strategy by running a grid search. Each combination of
    hyperparameter is fed into the strategy, positions and portfolio ratios are returned,
    pnl is calculated and results are tabulated.

    Args:
        price_data (pd.DataFrame
            {Date (datetime.datetime): {security_1 (str): prices (List[float]),
                                        security_2 (str): prices (List[float]),
                                                        .
                                                        .
                                                        .}})

        strategy (function): main strategy logic to output positions and portfolio ratios
            based on input data and hyperparameters

        hyperparameters (dict {parameter_name (str): parameter_values (List)}):
            each hyperparameter and set of values to use for grid search.

        commissions_in_percent (float): to model transaction costs
        bid_ask_spread (float): to model transaction costs

    Returns:
        results (pd.DataFrame): results of the grid search.
    """
    # Create a partial function so that only hyperparameters need to be fed.
    strategy = partial(strategy, price_data=price_data)

    # Grid search
    results = []
    keys = hyperparameters.keys()
    for combination in tqdm(set(cartesian_product(*hyperparameters.values()))):
        # creating positions and portfolio ratios
        parameter_combination = dict(zip(keys, combination))
        positions, portfolio_ratios = strategy(**parameter_combination)

        # evaluating performance
        annual_returns, sharpe_ratio = \
            calculate_pnl_with_transaction_costs(price_data, positions, portfolio_ratios,
                                                 commissions_in_percent, bid_ask_spread,
                                                 plot=False)

        parameter_combination['annual_returns'] = annual_returns
        parameter_combination['sharpe_ratio'] = sharpe_ratio

        results.append(parameter_combination)

    # convert results into a tabular form
    results = pd.DataFrame(results)
    results = results.fillna(0)
    return results


def _calculate_transaction_costs(price_data, positions, portfolio_ratios,
                                 commissions_in_percent, bid_ask_spread):
    """
    Models transaction costs as a form of commissions + slippage.

    Slippage is assumed to be half bid ask spread, and commissions is a percentage
    of the market value of each trade.

    Args:
        price_data (pd.DataFrame)
        positions (np.array([int]))
        portfolio_ratios (np.array([float]))
        commissions_in_percent (float)
        bid_ask_spread (float)

    Returns:
        transaction_costs (pd.Series({Date (datetime.datetime): cost (List[float])})
    """
    position_change = positions.diff()
    portfolio_ratios_change = portfolio_ratios.diff()

    # when entering positions in the unit portfolio
    commissions = abs(commissions_in_percent / 100 * position_change *
                      (portfolio_ratios.values * price_data.shift()).sum(axis=1))

    # when re-balancing unit portfolio security ratios
    commissions += abs(commissions_in_percent / 100 * positions *
                       (portfolio_ratios_change.values * price_data.shift()).sum(axis=1))

    # when entering positions in the unit portfolio
    slippages = abs(0.5 * bid_ask_spread *
                    position_change *
                    portfolio_ratios.sum(axis=1))

    # when re-balancing unit portfolio security ratios
    slippages += abs(0.5 * bid_ask_spread *
                     positions *
                     portfolio_ratios_change.sum(axis=1))

    return slippages + commissions
