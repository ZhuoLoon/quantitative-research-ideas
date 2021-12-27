class PortfolioModel:
    """
    Builds up a portfolio based on the signals emitted by Alpha model.
    Positions are sized up based on firm equity, and modified if necessarily
    by risk models to reduce market exposure.
    """
    def __init__(self):
        # helper models
        self.portfolio_optimizer = None

        # internal data structures
        self.previous_optimal_portfolio = {}
        self.securities_and_leverages = {}
        self.firm_equity = 0

        # data structures received from data model
        self.securities_and_latest_quote = {}
        self.securities_and_latest_trade = {}
        self.securities_and_latest_bar = {}
        self.securities_and_latest_usd_price = {}
        self.current_time = None

        # data structures received from universe model
        self.securities_and_ids = {}

    def create_portfolio(self, signals):
        """
        Main method for the class, receives signals from alpha model, applies
        any necessary optimisations to reduce market exposure, and then
        scales up the portfolio based on firm equity.

        Args:
            signals (Dict {security (str): position (int)})

        Returns:
            optimal_portfolio (Dict {security (str): position (int)})
        """
        normalized_signals = self.normalize_signal_weights(signals)
        risk_optimized_portfolio = self.optimize_portfolio(normalized_signals)
        optimal_portfolio = self.scale_portfolio_by_firm_equity(risk_optimized_portfolio)

        return optimal_portfolio

    def normalize_signal_weights(self, signals):
        """
        Min-max normalizes alpha signals to obtain weights in the interval [0,1]

        Args:
            signals (Dict {security (str): position (int)}): change in positions

        Returns:
            normalized_signals (Dict {security (str): normalized_weight (float)})
        """
        maximum_weight = max(signals.values())
        normalized_signals = {security: position / maximum_weight for
                              security, position in signals.items()}

        return normalized_signals

    def optimize_portfolio(self, normalized_signals):
        """
        Calls risk models to optimize the portfolio by reducing market risk.

        Args:
            normalized_signals (Dict {security (str): normalized_weight (float)})

        Returns:
            risk_optimized_portfolio (Dict {security (str): optimized_weight (float)})
        """
        risk_optimized_portfolio = self.portfolio_optimizer.optimize(normalized_signals)

        return risk_optimized_portfolio

    def scale_portfolio_by_firm_equity(self, risk_optimized_portfolio):
        """
        Calculates the market value MV_{min} of the unit risk optimized portfolio,
        and scales up this portfolio by multiplying it by (firm_equity / MV_{min}) to
        create the optimal portfolio.

        Args:
            risk_optimized_portfolio (Dict {security (str): optimized_weight (float)})

        Returns:
            optimal_portfolio (Dict {security (str): position (int)})
        """
        # calculating MV_{min}
        unit_portfolio_market_value = 0

        for security, weight in risk_optimized_portfolio.items():
            unit_portfolio_market_value +=\
                self.securities_and_latest_usd_price[security] *\
                self.securities_and_leverages[security]

        multiplier = self.firm_equity / unit_portfolio_market_value

        # Scaling up the portfolio by multiplier
        optimal_portfolio = {security: round(weight*multiplier) for
                             security, weight in risk_optimized_portfolio.items()}

        return optimal_portfolio

    def calculate_order_vector_and_emit(self, optimal_portfolio):
        """
        Calculates order vector to pass to execution model. This will be equal to
        the difference between current optimal portfolio and previous optimal. Also
        saves the current optimal portfolio.

        Args:
            optimal_portfolio (Dict {security (str): position (int)})

        Returns:
            orders_to_execute (Dict {security (str): position (int)})
        """
        # Initialise output
        orders_to_execute = {}

        for security in self.securities_and_ids:
            orders_to_execute[security] =\
                optimal_portfolio[security] - self.previous_optimal_portfolio[security]

        # saves optimal portfolio
        self.previous_optimal_portfolio = optimal_portfolio

        return orders_to_execute

    def initialise_data_structures(self):
        """Initialise data structures necessary for trading universe
        """
        for security in self.securities_and_ids:
            self.previous_optimal_portfolio[security] = 0

    def receive_trading_universe(self, trading_universe):
        """
        Receives securities to trade from universe model.

        Args:
            trading_universe (dict): securities and currencies to trade
        """
        self.securities_and_ids = trading_universe['securities_and_ids']

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