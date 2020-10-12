"""Implementation of Zero-Intelligence Models of Limit Order Book"""

from typing import Tuple
from numpy import floor
import numpy as np
import matplotlib.pyplot as plt


class Book:
    """Implements a Limit Order Book via array based data structure

    Two Agent Based Models are currently supported:
    - The SFGK Zero Intelligence Model c.f
      https://arxiv.org/pdf/cond-mat/0210475.pdf
    - The Cont-Stoikov-Talreja Model c.f
      https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.139.1085&rep=rep1&type=pdf

    Currently only supports placing orders of size 1
    """
    def __init__(self):
        """Default Constructor used to initialize the order book"""
        self._levels = 1000
        self._depth = 5
        self.price = np.arange(-self._levels, self._levels + 1)
        self.bid_size, self.ask_size = self._initialize_orders()
        self.events = self._create_events()

    def _get_levels(self) -> int:
        """returns number of levels in lob

        :return: levels in the lob
        :rtype: int
        """
        return self._levels

    def _get_depth(self) -> int:
        """Returns the depth of orders from the limit order book

        :return: depth of orders in the book
        :rtype: int
        """
        return self._depth

    def _initialize_orders(self) -> Tuple[np.ndarray, np.ndarray]:
        """Creates buy and sell orders in the lob

        Orders are created before agent based simulation begins
        These orders await execution by incoming order or
        can be cancelled

        :return: buy/sell sizes on the bid/ask side
        :rtype: Tuple[np.ndarray, np.ndarray]
        """
        d, pl = self._get_depth(), self._get_levels()

        # create buy & sell orders for bid prices at -1000 to -1
        buy_orders = np.repeat(d, pl - 8)
        buy_orders = np.append(buy_orders, [5, 4, 4, 3, 3, 2, 2, 1])
        sell_orders = np.repeat(0, pl)

        # create buy and sell orders for ask prices at 0 to 1000
        buy_orders = np.append(buy_orders, np.repeat(0, pl + 1))
        sell_orders = np.append(sell_orders, [0, 1, 2, 2, 3, 3, 4, 4, 5])
        sell_orders = np.append(sell_orders, np.repeat(d, pl - 8))

        return buy_orders, sell_orders

    # functions to get information from market
    def best_ask(self) -> float:
        """Computes the best price on ask side

        :return: the best asking price is returned
        :rtype: float
        """
        return self.price[self.ask_size > 0].min()

    def best_bid(self) -> float:
        """Computes the best bid on bid side

        :return: the best bid price is returned
        :rtype: float
        """
        return self.price[self.bid_size > 0].max()

    def spread(self) -> float:
        """Compute the inside spread

        :return: spread between best prices
        :rtype: float
        """
        return self.best_ask() - self.best_bid()

    def mid(self) -> float:
        """compute the mid price from best bid and ask

        :return: mid price
        :rtype: float
        """
        return (self.best_ask() + self.best_bid()) * 0.5

    # functions to place order
    def market_buy(self, qty: int = 1):
        """Places market buy order at best ask

        :param qty: the quantity to buy
         if not specified, defaults to 1
        :type qty: int, optional
        """
        # get the best ask and remove orders at that price
        p = self.best_ask()
        remaining_orders = self.ask_size[self.price == p][0] - qty
        self.ask_size[self.price == p] = remaining_orders

    def market_sell(self, qty: int = 1):
        """Places market sell order at best bid

        :param qty: the quantity to sell
         if not specified, defaults to 1.
        :type qty: int, optional
        """
        # get best bid and remove orders at that price
        p = self.best_bid()
        remaining_orders = self.bid_size[self.price == p][0] - qty
        self.bid_size[self.price == p] = remaining_orders

    def limit_buy(self, price: int, qty: int = 1):
        """Places limit buy order at a given price level

        :param price: the price at which to place the LBO
        :type price: int
        :param qty: the quantity agent wishes to buy
         if not specified, defaults to 1
        :type qty: int, optional
        """
        # add orders at the price specified
        new_orders = self.bid_size[self.price == price][0] + qty
        self.bid_size[self.price == price] = new_orders

    def limit_sell(self, price: int, qty: int = 1):
        """Places limit sell order at a given price level

        :param price: price at which to place the LSO
        :type price: int
        :param qty: the quantity agent wishes to sell
         if not specified, defaults to 1
        :type qty: int, optional
        """
        # add orders at the price specified
        new_orders = self.ask_size[self.price == price][0] + qty
        self.ask_size[self.price == price] = new_orders

    def cancel_buy(self,
                   price: int = None,
                   cancelable_orders: int = None,
                   qty: int = 1):
        """Places a cancel order at given price level on bid side

        :param price: price at which we cancel order
         defaults to None.  If not specified, randomly choose
         from which cancelable_orders to cancel from
        :type price: int, optional
        :param cancelable_orders: total cancelable orders on bid side
         defaults to None.  If price is specified,
         then cancelable_orders is None
        :type cancelable_orders: int, optional
        :param qty: the quantity agent wishes to cancel
         defaults to 1
        :type qty: int, optional
        """
        # if price is specified, cancel order at that level
        if price is not None:
            remaining_orders = self.bid_size[self.price == price][0] - qty
            self.bid_size[self.price == price] = remaining_orders
        # otherwise randomly choose from total cancelable_orders at bid side
        else:
            q = self.choose(cancelable_orders)
            tmp = self.buy_size[::-1].cumsum()
            posn = len(tmp[tmp >= q])
            p = self.price[posn-1]
            self.bid_size[posn-1] = self.bid_size[posn-1] - qty

    def cancel_sell(self,
                    price: int = None,
                    cancelable_orders: int = None,
                    qty: int = 1):
        """Places a cancel order at given price level on ask side

        :param price: price at which we cancel order
         defaults to None.  If not specified, randomly choose
         from which cancelable_orders to cancel from
        :type price: int, optional
        :param cancelable_orders: total cancelable orders on ask side
         defaults to None.  If price is specified,
         then cancelable_orders is None
        :type cancelable_orders: int, optional
        :param qty: the quantity agent wishes to cancel
         defaults to 1
        :type qty: int, optional
        """
        # if price is specified, cancel order at that level
        if price is not None:
            remaining_orders = self.ask_size[self.price == price][0] - qty
            self.sell_size[self.price == price] = remaining_orders
        # otherwise randomly choose from total cancelable_orders at ask side
        else:
            q = self.choose(cancelable_orders)
            tmp = self.sell_size.cumsum()
            posn = len(tmp[tmp < q]) + 1
            p = self.price[posn - 1]
            self.ask_size[posn - 1] = self.ask_size[posn - 1] - qty

    # functions to find the bid/ask positions and mid position
    def _bid_position(self) -> int:
        """returns the index of position of best bid

        :return: index of best bid
        :rtype: int
        """
        return np.where(self.price == self.best_bid())[0][0] + 1

    def _ask_position(self) -> int:
        """returns the index of position of best ask

        :return: index of best ask
        :rtype: int
        """
        return np.where(self.price == self.best_ask())[0][0] + 1

    def _mid_position(self) -> int:
        """returns index of position of mid-market

        :return: index of mid-point price
        :rtype: int
        """
        mid_pos = (self._bid_position() + self._ask_position()) * 0.5
        return int(floor(mid_pos))

    def book_shape(self, band):
        """
        returns the #of shares up to band on each side of book around mid-price
        """
        buy_qty = self.bid_size[self._mid_position() + np.arange(-band-1, 0)]
        sell_qty = self.ask_size[self._mid_position() + np.arange(band)]
        return np.append(buy_qty, sell_qty)

    def book_plot(self, band: int):
        """plots the book shape around mid-price

        the function plots the number of shares around mid-price
        upto the given band

        :param band: the interval around mid-price to plot
        :type band: int
        """
        shares_around_mid = self.book_shape(band)
        plt.plot(np.arange(-band, band + 1), shares_around_mid)

    def choose(self, price_level: int, prob: np.ndarray = None):
        """pick price from price_level randomly

        :param price_level: the price level from which to pick from
        :type price_level: int
        :param prob: pick a level based on provided prob
         if not specified, pick uniformly.  defaults to None
        :type prob: float, optional
        :return: the price level chosen
        :rtype: int
        """
        # if probability isn't specified, pick uniformly
        if prob is None:
            return np.random.choice(np.arange(1, price_level + 1), 1)[0]
        # otherwise pick based on given probability
        return np.random.choice(np.arange(1, price_level + 1), 1, prob)[0]

    def _create_events(self) -> dict:
        """creates events based on simulation

        :return: dictionary of events
        :rtype: dict
        """
        events = ["market_buy", "market_sell", "limit_buy", "limit_sell",
                  "cancel_buy", "cancel_sell"]
        return dict(zip(range(6), events))

    def sfgk_model(self,
                   mu: float,
                   lamda: float,
                   theta: float,
                   L: int = 20):
        """Generates an agent based event simulation

        Calling this function generates a market event
        that results in one of market_buy, market_sell,
        limit_buy, limit_sell, cancel_buy, cancel_sell
        according to sfgk model

        :param mu: rate of arrival of market orders
        :type mu: int
        :param lamda: rate of arrival of limit orders
        :type lamda: int
        :param theta: rate at which orders are cancelled
        :type theta: float
        :param L: distance in ticks from opposite best quote
        :type L: int
        """
        # get total orders on bid side from opposte best quote from L
        net_buys = self.buy_size[self.price >= (self.best_ask()-L)].sum()

        # get total orders on ask side from opposite best quote from L
        net_sells = self.sell_size[self.price <= (self.best_bid() + L)].sum()

        # set the probability of each event based on market rates
        cum_rate = mu + 2 * L * lamda + net_buys * theta + net_sells * theta
        pevent = [0.5*mu, 0.5*mu, L*lamda, L*lamda,
                  net_buys*theta, net_sells*theta]
        pevent = np.array(pevent) / cum_rate

        # generate market events and initite orders
        market_event = self.events[np.random.choice(6, 1, p=pevent)[0]]
        if market_event == "market_buy":
            self.market_buy()
        elif market_event == "market_sell":
            self.market_sell()
        elif market_event == "limit_buy":
            # pick price from distance L of opposite best quote and place order
            q = self.choose(L)
            p = self.best_ask() - q
            self.limit_buy(price=p)
        elif market_event == "limit_sell":
            # pick price from distance L of opposite best quote and place order
            q = self.choose(L)
            p = self.best_bid() + q
            self.limit_sell(price=p)
        elif market_event == "cancel_buy":
            self.cancel_buy(cancellable_orders=net_buys)
        elif market_event == "cancel_sell":
            self.cancel_sell(cancellable_orders=net_sells)

    def sfgk_simulate(self,
                      mu: float,
                      lamda: float,
                      theta: float,
                      L: int,
                      max_events: int = 10000,
                      ) -> np.ndarray:
        """Simulates the average book shape in SFGK model

        :param mu: arrival rate of market orders
        :type mu: float
        :param lamda: arrival rate of limit orders
        :type lamda: float
        :param theta: rate at which orders are cancelled
        :type theta: float
        :param L: distance in ticks from opposite best quote
        :type L: int
        :param max_events: number of events generated
         defaults to 10000
        :type max_events: int, optional
        :return: average book shape
        :rtype: np.ndarray
        """
        # simulate 1000 events to start
        for _ in range(1000):
            self.sfgk_model(mu, lamda, theta, L)

        # calculate average book shape
        avg_book_shape = self.book_shape(L) / max_events

        # run sfgk simulation for max_events and return bookshape
        for _ in range(1, max_events):
            self.sfgk_model(mu, lamda, theta, L)
            avg_book_shape += self.book_shape(L) / max_events

        return avg_book_shape

    def cst_model(self, mu, lamdas, thetas, L):
        """Generates a agent based event simulation

        Calling this function generates a market event
        that results in one of market_buy, market_sell,
        limit_buy, limit_sell, cancel_buy or cancel_sell

        :param mu: the rate of arrival of market orders
        :type mu: float
        :param lamdas: the rate of arrival of limit orders
        :type lamdas: np.ndarray
        :param thetas: the rate at which orders are cancelled
        :type thetas: np.ndarray
        :param L: [description]
        :type L: [type]
        """
        cb = self.buy_size[self.price >= (self.best_ask()-L)][:L][::-1]
        cs = self.sell_size[self.price <= (self.best_bid() + L)][-L:]
        nb = cb.sum()
        ns = cs.sum()
        cb_rates = np.dot(thetas, cb)
        cs_rates = np.dot(thetas, cs)

        cum_lam = lamdas.sum()

        cum_rate = 2*mu + 2*cum_lam + cb_rates+cs_rates
        pevent = np.array([mu, mu, cum_lam, cum_lam, cb_rates, cs_rates]) / cum_rate
        market_event = self.events[np.random.choice(6, 1, p=pevent)[0]]

        if market_event == "market_buy":
            self.market_buy()
        elif market_event == "market_sell":
            self.market_sell()
        elif market_event == "limit_buy":
            pevent = lamdas / cum_lam
            q = self.choose(L, prob = pevent)
            p = self.best_ask() - q
            self.limit_buy(price = p)
        elif market_event == "limit_sell":
            pevent = lamdas / cum_lam
            q = self.choose(L, prob = pevent)
            p = self.best_bid() + q
            self.limit_sell(price = p)
        elif market_event == "cancel_buy":
            pevent = (thetas * cb) / cb_rates
            q = self.choose(L,prob=pevent)
            p = self.best_ask() - q
            self.cancel_buy(price = p)
        elif market_event == "cancel_sell":
            pevent = (thetas * cs) / cs_rates
            q = self.choose(L,prob = pevent)
            p = self.best_bid() + q
            self.cancel_sell(price = p)

    def cst_simulate(self, mu, lamdas, thetas, L, numEvents):
        """returns the average book shape"""
        # burn in for 1000 events
        n = 1000
        for i in range(n):
            self.cst_model(mu,lamdas,thetas,L)
        avgBookShape = self.book_shape(L) / numEvents

        for i in range(1,numEvents):
            self.cst_model(mu,lamdas,thetas,L)
            avgBookShape = avgBookShape + self.book_shape(L)/ numEvents
        ans = (avgBookShape[:L][::-1]+avgBookShape[L+1:])*0.5
        ans = np.append(avgBookShape[L],ans)
        return ans

    def powerlawfit(self, emp_estimates, distance):
        obj_func = lambda k,alpha,i: k*i**(-alpha)
        import lmfit as lmfit
        model = lmfit.Model(obj_func,independent_vars=['i'],param_names=['k','alpha'])
        fit = model.fit(emp_estimates,i=np.arange(1,6),k=1.2,alpha=0.4,verbose=False)
        return fit.values['k']*distance**-fit.values['alpha']

    def prob_mid(self, n=10000, xb=1, xs=1):
        """ calculates probability of mid-price to go up"""
        def send_orders(xb, xs, mu = 0.94, lamda = 1.85,theta = 0.71):
            cum_rate = 2*mu + 2*lamda + theta*xb + theta*xs
            bid_qty_down = mu+theta*xb
            ask_qty_down = mu+theta*xs
            pevent = np.array([lamda,lamda,bid_qty_down,ask_qty_down])/cum_rate
            ans = np.random.choice(np.arange(4),size=1,p=pevent)[0]

            if ans == 0:
                xb += 1
            elif ans == 1:
                xs += 1
            elif ans == 2:
                xb -= 1
            elif ans == 3:
                xs -= 1
            return xb, xs

        count = 0
        for i in range(n):
            qb_old,qs_old = xb,xs
            while True:
                qb_new,qs_new = send_orders(xb=qb_old,xs=qs_old)
                if qb_new == 0:
                    break
                elif qs_new == 0:
                    count += 1
                    break
                qb_old, qs_old = qb_new, qs_new
        return count / n

    def limit_order_prob(self, n=10000, xb=5, xs=5, dpos=5):
        # assumes my order is first at the bid
        def send_orders(xb, xs, d,mu=0.94, lamda=1.85, theta=0.71):
            cum_rate = 2*mu + 2*lamda + theta*(xb-1) + theta*xs
            ask_qty_down = mu+theta*xs
            pevent = np.array([lamda,lamda,mu,theta*(xb-1), ask_qty_down])/cum_rate
            ans = np.random.choice(np.arange(5), size=1, p=pevent)[0]  # pick based on respetive probabilities

            if ans == 0:  # limit buy
                xb += 1
            elif ans == 1:  # limit sell
                xs += 1
            elif ans == 2:  # market sell
                xb -= 1
                d -= 1 if d > 0 else 0
            elif ans == 3:  # cancel buy
                r = np.random.uniform()
                if r > (xb-d) / (xb-1):
                    d -= 1
                xb -= 1
            else:  # market buy
                xs -= 1
            return xb, xs, d

        count = 0
        for i in range(n):
            qb_old,qs_old,d_old = xb,xs,dpos
            while True:
                qb_new,qs_new,d_new = send_orders(xb=qb_old, xs=qs_old, d=d_old)
                if d_new == 0:  # my order has been executed
                    count += 1
                    break
                elif qs_new == 0 and d_new > 0:  # mid price has moved
                    break
                qb_old, qs_old, d_old = qb_new, qs_new, d_new
        return count / n

    def prob_making_spread(self, n=10000, xb=5, xs=5, bid_pos=5, ask_pos=5):

        def send_orders(xb, xs, bid_pos, ask_pos, mu=0.94, lamda=1.85, theta=0.71):
            xb_rate = xb - 1
            xs_rate = xs - 1
            if bid_pos == 0:
                xb_rate = xb
            if ask_pos == 0:
                xs_rate = xs

            cum_rate = 2*mu + 2*lamda + theta*xb_rate + theta*xs_rate
            pevent = np.array([lamda,lamda,mu,mu,theta*xb_rate,theta*xs_rate])/cum_rate
            ans = np.random.choice(np.arange(6), size=1, p=pevent)[0]

            if ans == 0:
                xb += 1
            elif ans == 1:
                xs += 1
            elif ans == 2:
                xb -= 1
                bid_pos -= 1 if bid_pos > 0 else 0
            elif ans == 3:
                xs -= 1
                ask_pos -= 1 if ask_pos > 0 else 0
            elif ans == 4:
                r = np.random.uniform()
                if r > (xb - bid_pos) / xb_rate:
                    bid_pos -= 1
                xb -= 1
            elif ans == 5:
                r = np.random.uniform()
                if r > (xs - ask_pos) / xs_rate:
                    ask_pos -= 1
                xs -= 1

            return xb, xs, bid_pos, ask_pos

        count = 0
        for i in range(n):
            qb_old, qs_old, b_old, a_old = xb,xs,bid_pos,ask_pos
            while True:
                qb_new, qs_new, b_new, a_new = send_orders(qb_old, qs_old, b_old, a_old)
                if b_new == 0 and a_new == 0:
                    count += 1
                    break
                elif qb_new == 0 and a_new > 0:
                    break
                elif qs_new == 0 and b_new > 0:
                    break
                qb_old, qs_old, b_old, a_old = qb_new, qs_new, b_new, a_new
        return count / n