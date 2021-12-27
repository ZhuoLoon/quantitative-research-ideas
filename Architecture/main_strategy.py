"""Skeletal code structure for algorithmic trading systems.
"""

from datetime import datetime

from primary_models.universe_model import UniverseModel
from primary_models.data_model import DataModel
from primary_models.alpha_model import AlphaModel
from primary_models.portfolio_model import PortfolioModel
from primary_models.execution_model import ExecutionModel


class MainStrategy:
    """
    Main strategy for trading. Ties up primary models in a coherent manner and acts
    as a nexus for the primary models to communicate with each other.
    """
    def __init__(self):
        # primary models
        self.universe_model = UniverseModel()
        self.data_model = DataModel()
        self.alpha_model = AlphaModel()
        self.portfolio_model = PortfolioModel()
        self.execution_model = ExecutionModel()

        # internal data structures
        self.backtest_start_date = None

    def main_event_loop(self):
        """
        Primary method for the class, called whenever market data is received. The following
        operations are carried out:
            1. Alpha Model:
                - Updates strategy models with latest data
                - Calls strategy models to emit signals (if any)
                - Aggregates signals across strategies (if there are multiple strategies)
                - Emits signals to Portfolio
            2. Portfolio Model:
                - Updates signals from Alpha
                - Calls Risk models to manage risk of portfolio
                - Calculates position sizes based on firm equity and leverage
                - Emits order vector to Execution
            3. Execution Model:
                - Accepts order vector from Portfolio
                - Slices orders into smaller chunks
                - Executes orders
        """
        # Alpha Model
        self.alpha_model.update_factors_with_latest_data()
        self.alpha_model.aggregate_signals_from_strategies()
        signal = self.alpha_model.emit_alpha_signal()

        # Portfolio Model
        optimal_portfolio = self.portfolio_model.create_portfolio(signal)
        orders_to_execute = self.portfolio_model.calculate_order_vector_and_emit(optimal_portfolio)

        # Execution Model
        self.execution_model.execute_orders(orders_to_execute)
        self.execution_model.send_pending_orders()

    def on_bar(self, bar):
        """
        Called whenever we receive a bar. Data model checks if bar is clean, collects the bar
        if it is and performs any preprocessing before propagating data to other models.
        """
        # First checks if bar received is clean
        bar_is_clean = self.data_model.assert_clean_data(bar)

        if bar_is_clean:
            self.data_model.collect_data(bar)
            self.data_model.preprocess_data(bar)
            self.data_model.propagate_data([self.alpha_model, self.portfolio_model,
                                            self.execution_model])
            self.main_event_loop()

    def on_quote(self, quote):
        """
        Called whenever we receive a quote. Data model checks if quote is clean,
        collects the quote if it is and performs any preprocessing before
        propagating data to other models.
        """
        # First checks if quote received is clean
        quote_is_clean = self.data_model.assert_clean_data(quote)

        if quote_is_clean:
            self.data_model.collect_data(quote)
            self.data_model.preprocess_data(quote)
            self.data_model.propagate_data([self.alpha_model, self.portfolio_model,
                                            self.execution_model])
            self.main_event_loop()

    def on_trade(self, trade):
        """
        Called whenever we receive a trade. Data model checks if trade is clean,
        collects the trade if it is and performs any preprocessing before
        propagating data to other models.
        """
        # First checks if trade received is clean
        trade_is_clean = self.data_model.assert_clean_data(trade)

        if trade_is_clean:
            self.data_model.collect_data(trade)
            self.data_model.preprocess_data(trade)
            self.data_model.propagate_data([self.alpha_model, self.portfolio_model,
                                            self.execution_model])
            self.main_event_loop()

    def on_strategy_start(self):
        """ Called when strategy is first started, prepares the primary models for trading.
        """
        self.prepare_universe_model()
        self.prepare_data_model()
        self.prepare_alpha_model()
        self.prepare_portfolio_model()
        self.prepare_execution_model()

    def prepare_universe_model(self):
        """
        Prepares the universe model by calling it to:
            1. Retrieve full universe of securities
            2. Download historical data for filtering & clustering
            3. Subscribe market data for filtered universe
            4. Propagate universe of securities to other models.
        """
        # If starting a backtest, set initial time to backtest start date.
        # If doing live trading, set initial time to current time.
        time_now = self.backtest_start_date if self.backtest_start_date else datetime.now()

        self.universe_model.retrieve_full_universe()

        self.universe_model.filter_and_cluster_universe(time_now)

        self.universe_model.subscribe_market_data()

        self.universe_model.propagate_universe([self.data_model, self.alpha_model,
                                                self.portfolio_model, self.execution_model])

    def prepare_data_model(self):
        """ Prepares data model by initialising data structures for each security in the universe.
        """
        self.data_model.initialise_data_structures()

    def prepare_alpha_model(self):
        """ Prepares alpha model by initialising factor models based on trading universe.
        """
        self.alpha_model.initialise_factor_models()

    def prepare_portfolio_model(self):
        """ Prepares portfolio model by initialising data structures for each security in the universe.
        """
        self.portfolio_model.initialise_data_structures()

    def prepare_execution_model(self):
        """ Prepares alpha model by initialising data structures for each security in the universe.
        """
        self.execution_model.initialise_data_structures()
