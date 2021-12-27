from itertools import combinations

from Architecture.factor_models.pair_spread_factor import PairSpreadFactor


class AlphaModel:
    """
    Emit trading signals to Portfolio Model. Under the Alpha Model is a collection
    of factor models (strategies) which receive preprocessed data, calculate
    indicators and generate signals based off the indicators.
    """
    def __init__(self):
        # internal data structures
        self.factor_universes_and_models = {}

        # data structures received from data model
        self.securities_and_latest_quote = {}
        self.securities_and_latest_trade = {}
        self.securities_and_latest_bar = {}
        self.securities_and_latest_usd_price = {}
        self.current_time = None

        # data structures received from universe model
        self.securities_and_ids = {}
        self.security_clusters = {}

        # data structures to pass to portfolio model
        self.alpha_signals = {}

    def update_factors_with_latest_data(self):
        """ Updates each factor model with latest data for factor model to function
        """
        # Loop through each factor model, and the subset of securities traded by the factor
        for factor_universe, factor_model in self.factor_universes_and_models.items():
            # Loops through each security in the factor universe to update factor model
            for security in factor_universe:
                self.update_specific_factor_model(security, factor_model)

    def update_specific_factor_model(self, security, factor_model):
        """
        Updates a factor model by feeding it latest data for one of the securities
        that is in the factor model's universe.

        Args:
             security (str): symbol code for the security
             factor_model (FactorModel): an instance of a factor model
        """
        factor_model.receive_data({"security": security,
                                   "latest_bar": self.securities_and_latest_bar[security],
                                   "latest_trade": self.securities_and_latest_trade[security],
                                   "latest_quote": self.securities_and_latest_quote[security],
                                   "latest_usd_price": self.securities_and_latest_usd_price[security]})

    def aggregate_signals_from_strategies(self):
        """ Calls each factor model to generate signals, and aggregates signals across factors
        """
        # Initialise aggregated alpha signals
        alpha_signals = {security: 0 for security in self.securities_and_ids}

        # Loop through each factor model, and the subset of securities traded by the factor
        for factor_universe, factor_model in self.factor_universes_and_models.items():
            signals = factor_model.generate_signals()
            for security in factor_universe:
                alpha_signals[security] += signals[security]

        self.alpha_signals = alpha_signals

    def emit_alpha_signal(self):
        """
        Emits aggregated alpha signals to Portfolio model

        Returns:
            self.alpha_signals (dict{security (str): position (int)})
        """
        return self.alpha_signals

    def receive_trading_universe(self, trading_universe):
        """
        Receives securities to trade from universe model.

        Args:
            trading_universe (dict): securities and currencies to trade
        """
        self.securities_and_ids = trading_universe['securities_and_ids']
        self.security_clusters = trading_universe['security_clusters']

    def receive_latest_data(self, latest_data):
        """
        Receives latest data from data model.

        Args:
            latest_data (dict)
        """
        self.securities_and_latest_quote = latest_data['securities_and_latest_quote']
        self.securities_and_latest_trade = latest_data['securities_and_latest_trade']
        self.securities_and_latest_bar = latest_data['securities_and_latest_bar']
        self.securities_and_latest_usd_price = latest_data['securities_and_latest_usd_price']
        self.current_time = latest_data['current_time']

    def initialise_factor_models(self):
        """
        Initialises factor models for alpha model to function. Each factor models focus on a
        subset of the trading universe, creating signals based on indicators calculated from
        preprocessed data.

        As an example, we will create factors for each pair of securities in the trading
        universe. Such factors focus on pair-trading; a common strategy used by traders to
        take long-short positions in a pair of highly correlated securities.
        """
        # Create pairs of securities from clusters
        pairs_of_securities = []

        for cluster in self.security_clusters.values():
            pairs_of_securities.extend(list(combinations(cluster, 2)))

        for pair in pairs_of_securities:
            self.factor_universes_and_models[pair] = PairSpreadFactor(pair)
