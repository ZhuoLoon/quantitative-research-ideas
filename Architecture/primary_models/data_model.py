import logging
import numpy as np
from collections import deque

logging.basicConfig(format='%(asctime)s %(name)s: [%(levelname)s] %(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S',
                    level=logging.WARNING)


class DataModel:
    """
    Collects latest market data and propagates to other primary models. Checks that
    market data is clean, and performs any necessary data preprocessing.
    """
    def __init__(self):
        # internal data structures
        self.bar_object = None
        self.quote_object = None
        self.trade_object = None
        self.trading_hours = {}
        self.currencies_and_latest_bar = {}

        # data structures used to check for outliers
        self.securities_and_clean_bars = {}
        self.securities_and_clean_quotes = {}
        self.securities_and_clean_trades = {}
        self.currencies_and_clean_bars = {}

        # controls verbosity of data model
        self.logger = logging.getLogger(name=self.__class__.__name__)

        # data structures to be propagated
        self.securities_and_latest_quote = {}
        self.securities_and_latest_trade = {}
        self.securities_and_latest_bar = {}
        self.securities_and_latest_usd_price = {}
        self.current_time = None

        # data structures received from universe model
        self.securities_and_ids = {}
        self.currencies_and_ids = {}

    def assert_clean_data(self, data):
        """
        Checks that latest market data received is clean and reasonable. Some common
        checks include making sure data comes in during trading hours, and prices are
        reasonable

        Args:
            data (bar/tick/trade): latest market data received

        Returns:
            data_is_clean (bool)
        """
        # initialise boolean
        data_is_clean = False

        # Checks first for whether data is within trading hours
        within_trading_hours = self.assert_within_trading_hours(data)
        if not within_trading_hours:
            self.logger.warning(f"Data received outside trading hours | Security: {data.security} | Time: {data.datetime}\n")
            return data_is_clean

        # Outlier checks
        not_outlier = self.assert_not_outlier(data)

        data_is_clean = within_trading_hours and not_outlier
        return data_is_clean

    def assert_within_trading_hours(self, data):
        """
        Checks if latest data is received during trading hours.

        Args:
            data (bar/tick/trade): latest market data received

        Returns:
            within_trading_hours (bool)
        """
        # initialise boolean
        within_trading_hours = False

        security = data.security
        for trading_intervals in self.trading_hours[security]:
            # If trading hours spill over to next day
            if trading_intervals[1] < trading_intervals[0]:
                within_trading_hours = trading_intervals[0] < data.datetime.time() or\
                                       data.datetime.time() < trading_intervals[1]
            else:
                within_trading_hours = trading_intervals[0] < data.datetime.time() < trading_intervals[1]

            if within_trading_hours:
                break

        return within_trading_hours

    def assert_not_outlier(self, data):
        """
        Checks if the latest data is not an outlier, by making sure that latest prices
        reflected are reasonable.

        For example, we may keep a deque of previous prices, compute the median and check that latest
        price is not too far away (relatively) from the median.

        Args:
            data (bar/tick/trade): latest market data received

        Returns:
            not_outlier (bool)
        """
        # initialise boolean
        not_outlier = False

        # hyperparameters to check for outliers
        maximum_acceptable_pct_change = .333
        data_points_needed = 1000

        security = data.security
        if isinstance(data, self.bar_object):
            # Not enough data to ascertain if latest data is clean, so assume it is
            if len(self.securities_and_clean_bars[security]) < data_points_needed:
                self.securities_and_clean_bars[security].append(data.close)
                not_outlier = True
            else:
                median_close_price = np.median(self.securities_and_clean_bars[security])
                # Data is not outlier, so append it to clean bars and pop oldest bar
                if abs((data.close - median_close_price) / median_close_price) < maximum_acceptable_pct_change:
                    self.securities_and_clean_bars[security].append(data.close)
                    self.securities_and_clean_bars[security].popleft()
                    not_outlier = True
                else:
                    self.logger.warning(f"Outlier bar | Security: {security} | Close: {data.close}\n")

        elif isinstance(data, self.trade_object):
            # Not enough data to ascertain if latest data is clean, so assume it is
            if len(self.securities_and_clean_trades[security]) < data_points_needed:
                self.securities_and_clean_trades[security].append(data.last)
                not_outlier = True
            else:
                median_last_price = np.median(self.securities_and_clean_trades[security])
                # Data is not outlier, so append it to clean trades and pop oldest trade
                if abs((data.last - median_last_price) / median_last_price) < maximum_acceptable_pct_change:
                    self.securities_and_clean_trades[security].append(data.last)
                    self.securities_and_clean_trades[security].popleft()
                    not_outlier = True
                else:
                    self.logger.warning(f"Outlier trade | Security: {security} | Last: {data.last}\n")

        elif isinstance(data, self.quote_object):
            # Not enough data to ascertain if latest data is clean, so assume it is
            if len(self.securities_and_clean_quotes[security]) < data_points_needed:
                self.securities_and_clean_quotes[security].append((data.ask, data.bid))
                not_outlier = True
            else:
                median_quote_price = np.median(self.securities_and_clean_quotes[security], axis=0)
                median_ask_price = median_quote_price[0]
                median_bid_price = median_quote_price[1]
                # Data is not outlier, so append it to clean quotes and pop oldest quote
                if abs((data.ask - median_ask_price) / median_ask_price) < maximum_acceptable_pct_change and\
                   abs((data.bid - median_bid_price) / median_bid_price) < maximum_acceptable_pct_change:
                    self.securities_and_clean_quotes[security].append((data.ask, data.bid))
                    self.securities_and_clean_quotes[security].popleft()
                    not_outlier = True
                else:
                    self.logger.warning(f"Outlier quote | Security: {security} | Ask: {data.ask} | Bid: {data.bid}\n")
                    
        else:
            raise NotImplementedError(f"Data type {type(data)} is not supported!")

        return not_outlier

    def collect_data(self, data):
        """
        Collects market data and updates data structures. Called after ensuring
        that data is clean.

        Args:
            data (bar/tick/trade): latest market data received
        """
        security = data.security
        self.current_time = data.datetime
        if isinstance(data, self.bar_object):
            # Checks if data belongs to a security or a currency
            if self.securities_and_ids.get(security) is not None:
                self.securities_and_latest_bar[security] = data
            else:
                self.currencies_and_latest_bar[security] = data
        elif isinstance(data, self.trade_object):
            self.securities_and_latest_trade[security] = data
        elif isinstance(data, self.quote_object):
            self.securities_and_latest_quote[security] = data
        else:
            raise NotImplementedError(f"Data type {type(data)} is not supported!")

    def preprocess_data(self, data):
        """
        Performs any necessary preprocessing for strategies to create indicators.

        As an example, we will calculate latest price in USD based on the mid-price of
        latest quote data. Currency conversions will be done if necessary.

        Args:
            data (bar/tick/trade): latest market data received
        """
        if isinstance(data, self.quote_object):
            security = data.security
            mid_price = (data.ask + data.bid) / 2
            # If base currency is not in USD, need to perform conversion
            if security.quote_currency != 'USD':
                conversion_rate = self.currencies_and_latest_bar[f"{security.quote_currency}USD"].close
                mid_price *= conversion_rate

            self.securities_and_latest_usd_price[security] = mid_price

    def initialise_data_structures(self):
        """
        Initialises data structures necessary for data model to function for
        securities in the trading universe.
        """
        # Data structures for trading universe
        for security in self.securities_and_ids:
            self.securities_and_latest_bar[security] = None
            self.securities_and_latest_trade[security] = None
            self.securities_and_latest_quote[security] = None
            self.securities_and_latest_usd_price[security] = None
            self.securities_and_clean_bars[security] = deque()
            self.securities_and_clean_trades[security] = deque()
            self.securities_and_clean_trades[security] = deque()

        # Data structures for currency data
        for currency in self.currencies_and_ids:
            self.currencies_and_latest_bar[currency] = None
            self.currencies_and_clean_bars[currency] = deque()

    def receive_trading_universe(self, trading_universe):
        """
        Receives securities to trade from universe model.

        Args:
            trading_universe (dict): securities and currencies to trade
        """
        self.securities_and_ids = trading_universe['securities_and_ids']
        self.currencies_and_ids = trading_universe['currencies_and_ids']

    def propagate_data(self, models):
        """
        Propagates fresh data to the other primary models

        Args:
            models (list): list of models receiving the trading universe.
        """
        for model in models:
            model.receive_latest_data({"securities_and_latest_bar": self.securities_and_latest_bar,
                                       "securities_and_latest_quote": self.securities_and_latest_quote,
                                       "securities_and_latest_trade": self.securities_and_latest_trade,
                                       "securities_and_latest_usd_price": self.securities_and_latest_usd_price,
                                       "current_time": self.current_time})

