import pandas as pd
import numpy as np
import yfinance as yf

from collections import defaultdict
from sklearn.mixture import GaussianMixture


def cluster_trading_universe(securities, current_time, lookback, number_of_clusters,
                             method='GaussianMixture', random_state=None):
    """
    Clusters securities in the trading universe based on historical price series data.

    Args:
        securities (List (Symbol (str)): list of security symbols
        current_time (datetime.datetime): current_time
        lookback (int): number of days to look back and download historical data
        number_of_clusters (int): how many clusters to create
        method (str): clustering algorithm to use. Default: 'GaussianMixture'
        random_state (int): random state for clustering algorithm. Default: None

    Returns:
        clusters_of_securities (Dict {cluster_tag (int): cluster (List (str))})
    """
    # Downloads historical data
    historical_data = yf.download(tickers=securities,
                                  start=current_time - pd.Timedelta(days=lookback),
                                  end=current_time)['Adj Close']

    # Preprocess data
    smoothed_returns = _preprocess_price_data(historical_data)

    # Clustering
    clusters_of_securities = _cluster_securities(smoothed_returns,
                                                 number_of_clusters,
                                                 method,
                                                 random_state)

    return clusters_of_securities


def _preprocess_price_data(historical_data):
    """
    Calculates the "smoothed returns" of securities from historical data, using the formulas
    provided by Zura Kakushadze and Willie Yu. (Reference: https://arxiv.org/pdf/1607.04883.pdf)

    Args:
        historical_data (pd.DataFrame
            {Date (datetime.datetime): {symbol (str): close_prices (List(float))}}

    Returns:
        smoothed_returns (pd.DataFrame
            {Date (datetime.datetime): {symbol (str): returns (List(float))}}
    """
    # calculate returns
    returns = historical_data.pct_change()
    returns = returns.dropna()

    # normalising returns
    standard_deviation = returns.std(axis=0)
    normalised_returns = returns / standard_deviation

    # smoothing_returns
    log_standard_deviation = np.log(standard_deviation)
    smoothing_factor = log_standard_deviation - (log_standard_deviation.median() - 3 * log_standard_deviation.mad())
    smoothing_factor = np.exp(smoothing_factor)
    smoothing_factor[smoothing_factor < 1] = 1
    smoothed_returns = normalised_returns / smoothing_factor

    return smoothed_returns


def _cluster_securities(smoothed_returns, number_of_clusters, method, random_state):
    """
    Clusters securities, using their smoothed returns as observation values.

    Args:
        smoothed_returns (pd.DataFrame)
        number_of_clusters (int)
        method (str)
        random_state (int)

    Returns:
        clusters_of_securities (Dict)
    """
    # Creating inputs for clustering algorithm
    securities = smoothed_returns.columns
    observations = smoothed_returns.values.T

    if method == "GaussianMixture":
        model = GaussianMixture(n_components=number_of_clusters,
                                random_state=random_state)
        model.fit(observations)
        cluster_tags = model.predict(observations)

    else:
        raise NotImplementedError(f"Method {method} is not supported!")

    clusters_of_securities = defaultdict(list)
    for i in range(smoothed_returns.shape[1]):
        clusters_of_securities[cluster_tags[i]].append(securities[i])

    return clusters_of_securities


