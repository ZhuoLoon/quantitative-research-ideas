import numpy as np
import pandas as pd


def get_hedge_ratios_from_kalman_filter(security_1_prices, security_2_prices,
                                        learning_rate, covariance):
    """
    Estimates the hedge ratio between price series for two securities using Kalman filter algorithm.

    Kalman filter assumes a linear relation: y = beta^T X + epsilon, epsilon follows a normal
    distribution with zero mean. Beta is updated using a Bayesian method, by comparing predicted
    and observed values of y.

    Args:
        security_1_prices (np.array[float])
        security_2_prices (np.array[float])
        learning_rate (float): controls rate of updating hedge ratios
        covariance (float): serial covariance of linear regression error term.

    Returns:
        beta (np.array[float]): regression coefficients (used for hedge ratios)
        error (np.array[float]): prediction error (y - yhat)
        error_variance (np.array[float]): prediction error variance
    """
    # Kalman filter variables
    x = np.stack([security_1_prices,
                  np.ones(security_1_prices.size)],
                 axis=1)  # Augment x with ones for regression 'intercept'
    y = security_2_prices

    beta = np.zeros((y.size, 2))  # regression coefficients
    yhat = np.zeros(y.size)  # linear regression prediction

    e = np.zeros(y.size)  # prediction error
    Q = np.zeros(y.size)  # prediction error variance

    R = np.zeros((2, 2))  # beta error covariance
    P = np.zeros((2, 2))  # predicted beta error covariance

    Vw = learning_rate / (1 - learning_rate) * np.eye(2)  # state transition covariance

    # Kalman filter algorithm
    for t in range(len(y)):
        if t > 0:
            beta[t] = beta[t - 1]
            R = P + Vw

        # calculating prediction error and error variance
        yhat[t] = np.dot(x[t], beta[t])
        e[t] = y[t] - yhat[t]
        Q[t] = np.dot(np.dot(x[t], R), x[t].T) + covariance

        # updating beta (hedge ratios)
        K = np.dot(R, x[t].T) / Q[t]
        beta[t] = beta[t] + np.dot(K, e[t])
        P = R - np.dot(np.outer(K, x[t]), R)

    return beta, e, Q


def get_bollinger_bands_positions(error, error_variance, zscore_threshold):
    """
    Creates a portfolio based on a Bollinger Bands strategy.

    Zscores are calculated at each time step, and we enter long position when
    zscore < -zscore_threshold, and short positions when zscore > zscore_threshold.
    We exit positions when spread reverts (zscore crosses 0)

    Args:
        error (np.array[float]): linear regression error term
        error_variance (np.array[float])
        zscore_threshold (float): threshold to enter positions

    Returns:
        positions (pd.Series): entry and exit behaviour
    """
    zscores = error / np.sqrt(error_variance)

    long_positions = pd.Series(np.nan, index=range(error.size))
    long_positions[zscores < -zscore_threshold] = 1
    long_positions[zscores > 0] = 0
    long_positions = long_positions.ffill()

    short_positions = pd.Series(np.nan, index=range(error.size))
    short_positions[zscores > zscore_threshold] = -1
    short_positions[zscores < 0] = 0
    short_positions = short_positions.ffill()

    positions = long_positions + short_positions
    # burn-in to allow hedge ratios to stabilise
    positions.iloc[:100] = 0

    return positions


def kalman_filter_strategy(price_data, learning_rate, covariance, zscore_threshold):
    """
    Calculates hedge ratios and creates portfolio positions by tying up both functions
    together. Used for grid searching.

    Args:
        price_data (pd.DataFrame
            {Date (datetime.datetime): {security_1 (str): prices (List[float]),
                                        security_2 (str): prices (List[float])}})
        learning_rate (float): controls rate of updating hedge ratios
        covariance (float): serial covariance of linear regression error term.
        zscore_threshold (float): threshold to enter positions

    Returns:
          positions (pd.Series): entry and exit behaviour
          hedge_ratios (pd.DataFrame): ratios of each security in the pair
    """
    # preprocess data
    security_1_prices = price_data.iloc[:, 0].values
    security_2_prices = price_data.iloc[:, 1].values

    # get hedge ratios
    beta, error, error_variance =\
        get_hedge_ratios_from_kalman_filter(security_1_prices,
                                            security_2_prices,
                                            learning_rate=learning_rate,
                                            covariance=covariance)

    hedge_ratios = pd.DataFrame(np.stack([-np.round(beta[:, 0]), np.ones(error.size)], axis=1))

    # creating positions
    positions = get_bollinger_bands_positions(error=error,
                                              error_variance=error_variance,
                                              zscore_threshold=zscore_threshold)

    return positions, hedge_ratios
