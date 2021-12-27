import mysql.connector


class UniverseModel:
    """
    Selects which securities to trade by filtering the most liquid securities
    from the entire family of securities trading in the exchange. Also
    clusters the filtered securities.
    """
    def __init__(self):
        # helper models
        self.filter_model = None
        self.cluster_model = None
        self.historical_data_model = None

        # internal data structures
        self.mysql_config = {}
        self.full_securities_and_ids = {}
        self.currencies_and_ids = {}
        self.subscribe_security_function = None

        # data structures to be propagated
        self.filtered_securities_and_ids = {}
        self.security_clusters = {}

    def filter_and_cluster_universe(self, time_now):
        """
        Primary method for the class, called on strategy start, and periodically afterwards
        to dynamically select the universe of securities to trade. The following operations
        are carried out:
            1. Historical Downloader:
                - downloads historical data for both filtering and clustering.
                - performs any necessary preprocessing for historical data (e.g currency conversions).
            2. Filter Model:
                - filters universe based on historical data.
            3. Cluster Model:
                - clusters securities in the filtered universe.

        Args:
            time_now (datetime.datetime): current time, used as reference for downloading historical data.
        """
        # Historical Downloader
        securities_and_historical_data = self.download_historical_data(time_now)

        # Filter model
        self.filter_model.receive_historical_data(securities_and_historical_data)
        self.filtered_securities_and_ids = self.filter_model.filter_liquid_securities()

        # Cluster model
        self.cluster_model.receive_historical_data(securities_and_historical_data)
        self.security_clusters = self.cluster_model.cluster_securities()

    def download_historical_data(self, time_now):
        """
        Downloads historical data for filtering universe and clustering securities. Performs any necessary
        data preprocessing.

        As an example, currency  conversions may be needed to standardise base currency
        amongst securities in the trading universe.

        Args:
            time_now (datetime.datetime): current time, used as reference for downloading historical data.

        Returns:
            securities_and_historical_data (Dict {security_symbol (str): historical_data (pd.Series)}):
                historical data for each security.
        """
        securities_and_historical_data =\
            self.historical_data_model.download_historical_data(self.full_securities_and_ids, time_now)

        # Performs currency conversions if necessary
        currency_conversion_data =\
            self.historical_data_model.download_historical_data(self.currencies_and_ids, time_now)

        for security, historical_data_series in securities_and_historical_data.copy().items():
            # If base currency is not in USD, need to perform conversion
            if security.quote_currency != 'USD':
                conversion_series = currency_conversion_data[f'{security.quote_currency}USD']
                securities_and_historical_data[security] = historical_data_series * conversion_series

        return securities_and_historical_data

    def retrieve_full_universe(self):
        """ Called on strategy start, initialises the full universe of securities.
        """
        cnx = mysql.connector.connect(**self.mysql_config)
        cursor = cnx.cursor()

        query =\
            """
            SELECT {columns}
            FROM {table}
            WHERE {condition}
            """

        cursor.execute(query)
        self.full_securities_and_ids = dict(cursor.fetchall())

    def subscribe_market_data(self):
        """ Subscribes market data for securities in the trading universe.
        """
        for security_symbol, security_id in self.filtered_securities_and_ids.items():
            self.subscribe_security_function(security_symbol, security_id)

    def propagate_universe(self, models):
        """
        Propagates trading universe to the other primary models.

        Args:
            models (list): list of models receiving the trading universe.
        """
        for model in models:
            model.receive_trading_universe({"securities_and_ids": self.filtered_securities_and_ids,
                                            "security_clusters": self.security_clusters,
                                            "currencies_and_ids": self.currencies_and_ids})


