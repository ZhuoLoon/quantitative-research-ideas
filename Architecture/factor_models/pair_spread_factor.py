"""Dummy pair-trading factor model"""


class PairSpreadFactor:
    def __init__(self, pair_of_securities):
        # internal data structures
        self.pair_of_securities = pair_of_securities
        self.securities_and_latest_bar = {security: None for security in pair_of_securities}
        self.securities_and_latest_trade = {security: None for security in pair_of_securities}
        self.securities_and_latest_quote = {security: None for security in pair_of_securities}
        self.securities_and_latest_usd_price = {security: None for security in pair_of_securities}

    def receive_data(self, data):
        """
        Receives latest data from alpha model

        Args:
            data (dict) latest data
        """
        security = data['security']

        self.securities_and_latest_bar[security] = data['securities_and_latest_bar']
        self.securities_and_latest_trade[security] = data['securities_and_latest_trade']
        self.securities_and_latest_quote[security] = data['securities_and_latest_quote']
        self.securities_and_latest_usd_price[security] = data['securities_and_latest_usd_price']

    def generate_signals(self):
        """
        Dummy method to generate signals based off calculated indicators

        Returns:
            signals (dict {security (str): position (int)}): positions to take
        """
        # Initialise output
        signals = {security: 0 for security in self.pair_of_securities}

        # Calculation of indicators

        # Taking positions

        return signals


