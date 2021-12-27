from collections import deque


class ExecutionModel:
    """
    Creates the optimal portfolio by sending orders to the exchange.
    Any order execution strategy/tactic/ logic will be placed under
    this model.
    """
    def __init__(self):
        # internal data structures
        self.orders_to_execute = {}
        self.pending_orders = deque()
        self.send_order_function = None
        self.time_order_received = None

        # data structures received from data model
        self.securities_and_latest_quote = {}
        self.securities_and_latest_trade = {}
        self.current_time = None

        # data structures received from universe model
        self.securities_and_ids = {}

    def execute_orders(self, orders_to_execute):
        """
        Main method for the class. Executes orders received from Portfolio model

        Args:
            orders_to_execute (Dict {security (str): position (int)})
        """
        self.orders_to_execute = orders_to_execute
        self.time_order_received = None

        self.create_order()

    def create_order(self):
        """Any execution logic/strategy/tactic will be under this function
        """
        order = {}

        # Insert order creation logic

        # Appends orders to a queue
        self.pending_orders.append(order)

    def send_pending_orders(self):
        """Sends pending orders in the form of a queue
        """
        if self.pending_orders:
            order = self.pending_orders.popleft()
            self.send_order_function(order)

    def initialise_data_structures(self):
        """Initialise data structures necessary for trading universe
        """
        for security in self.securities_and_ids:
            self.orders_to_execute[security] = 0

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
        self.current_time = latest_data['current_time']
