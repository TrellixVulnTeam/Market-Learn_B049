"""
Implementation of Harry Markowitz's Modern Portfolio Theory
Author: Rajan Subramanian
Created Feb 10 2021
"""

from __future__ import annotations
from marketlearn.optimization import Asset
from numpy import fromiter
from numpy.random import random
from scipy.optimize import minimize
import numpy as np
import pandas as pd
import plotly.graph_objects as go


class Harry:
    """
    Implements Harry Markowitz'a Model of mean variance optimization

    Parameters
    ----------
    historical_prices : pd.DataFrame
        represents historical daily end of day prices

    Attributes
    ----------
    assets: Dict[name: Asset]
        dictionary of Asset objects whose keys are asset names
    covariance_matrix: np.ndarray
        Scaled Covariance Matrix of daily log returns
    asset_expected_returns: np.ndarray
        forecasted sample means of each Asset
    asset_expected_vol: np.ndarray
        forecasted sample volatility of each Asset
    """

    def __init__(self, historical_prices: pd.DataFrame, risk_free_rate=None):
        """Default constructor used to initialize portfolio"""
        self.__assets = {
            name: Asset(name=name, price_history=historical_prices[name])
            for name in historical_prices.columns
        }
        self.covariance_matrix = Asset.covariance_matrix(tuple(self))
        self.asset_expected_returns = fromiter(
            self.asset_expected_returns(), dtype=float
        )
        self.asset_expected_vol = fromiter(
            self.asset_expected_volatility(), dtype=float
        )

        self.security_count = len(self.__assets)
        self.risk_free_rate = risk_free_rate

    def __eq__(self, other: Harry):
        return type(self) is type(other) and self.assets() == other.assets()

    def __ne__(self, other: Harry):
        return not (self == other)

    def __repr__(self):
        return f"Portfolio size: {self.security_count} Assets"

    def __iter__(self):
        yield from self.__assets.values()

    def assets(self):
        yield from self

    def get_asset(self, name: str) -> Asset:
        """return the Asset in portfolio given name

        Parameters
        ----------
        name : str
            name of the Asset

        Returns
        -------
        Asset
            contains information about the asset
        """
        return self.__assets[name]

    def asset_expected_returns(self):
        """gets expected return of each asset in portfolio

        Yields
        -------
        Iterator[float]
            an iteration of expected return of each asset in portfolio
        """
        yield from (asset.expected_returns for asset in self)

    def asset_expected_volatility(self):
        """gets expected volatility of each asset in portfolio

        Yields
        -------
        Iterator[float]
            iteration of expected volatility of each asset scaled by trading days
        """
        yield from np.sqrt(np.diag(self.covariance_matrix))

    @classmethod
    def random_weights(cls, nsim: int, nsec: int):
        """creates a portfolio with random weights

        Parameters
        ----------
        nsec : int
            number of securities in porfolio
        nsim : int, optional, default=1
            number of simulations to perform

        Returns
        -------
        np.ndarray, shape=(nsim, nsec)
            random weight matrix
        """
        if nsim == 1:
            weights = random(nsec)
            weights /= weights.sum()
        else:
            weights = random((nsim, nsec))
            weights = (weights.T / weights.sum(axis=1)).T

        return weights

    def portfolio_variance(self, weights: np.ndarray):
        """computes the portfolio variance

        portfolio variance is given by var_p = w'cov(R)w

        Parameters
        ----------
        weights : np.ndarray
            weight of each asset in portfolio

        Returns
        -------
        float
            portfolio variance
        """
        return weights.T @ self.covariance_matrix @ weights

    def portfolio_expected_return(self, weights: np.ndarray):
        return weights.T @ self.asset_expected_returns

    def simulate_random_portfolios(self, nportfolios: int):
        """runs a monte-carlo simulation by generating random portfolios

        Parameters
        ----------
        nsec : int
            [description]
        nportfolios : int, optional
            [description], by default 1
        """
        nsec = self.security_count
        weights = Harry.random_weights(nsim=nportfolios, nsec=nsec)

        # return volatility and mean of each simulation as a tuple
        return (
            (
                np.sqrt(self.portfolio_variance(weights[p])),
                self.portfolio_expected_return(weights[p]),
            )
            for p in range(nportfolios)
        )

    def plot_simulated_portfolios(self, nportfolios: int):
        """plots the simulated portfolio

        Parameters
        ----------
        nportfolios : int
            [description]
        """
        simulations = self.simulate_random_portfolios(nportfolios)
        xval, yval = zip(*simulations)
        # plt.scatter(xval, yval, marker="o", s=10, cmap="winter", alpha=0.35)
        # plt.grid()
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=xval,
                y=yval,
                mode="markers",
                line=dict(color="rgb(55, 83, 109)", dash="dash"),
            )
        )
        fig.update_layout(
            title_text="Simulated Portfolio Frontier",
            template="plotly_white",
            xaxis=dict(title="Annualized portfolio expected volatility"),
            yaxis=dict(title="Annualized portfolio expected returns"),
        )
        fig.show()

    def sharpe_ratio(self, weights: np.ndarray) -> float:
        """Comoputes the sharpe ratio of portfolio given weights

        Parameters
        ----------
        weights : np.ndarray
            percentage of each asset held in portfolio

        Returns
        -------
        sharpe ratio
            float
        """
        return (
            self.portfolio_expected_return(weights) - self.risk_free_rate
        ) / np.sqrt(self.portfolio_variance(weights))

    def optimize_risk(self, constraints: bool = False, target: float = None):
        """Computes the weights corresponding to minimum variance

        Parameters
        ----------
        constraints : bool, optional, default=False
            mean constraint
        target : float, optional, default=None
            target portfolio return if constraints is True

        Returns
        -------
        np.ndarray
            weights corresponding to minimum variance
        """
        # get count of assets in portfolio
        total_assets = self.security_count

        # make random guess
        guess_weights = Harry.random_weights(nsim=1, nsec=total_assets)

        # minimize risk subject to target level of return constraint
        if constraints:
            consts = [
                {
                    "type": "eq",
                    "fun": lambda w: self.portfolio_expected_returns(w) - target,
                },
                {"type": "eq", "fun": lambda w: sum(w) - 1},
            ]
        # minimize risk with only contraint sum of weights = 1
        else:
            consts = [{"type": "eq", "fun": lambda w: sum(w) - 1}]

        # minimize the portolio variance, assume no short selling
        weights = minimize(
            fun=lambda w: self.portfolio_variance(w),
            x0=guess_weights,
            constraints=consts,
            method="SLSQP",
            bounds=[(0, 1) for _ in range(total_assets)],
        )["x"]
        return weights

    def optimize_sharpe(self, target_return, target_vol):
        """Return the weights corresponding to maximizing sharpe ratio

        The sharpe ratio is given by SRp = mu_p - mu_f / sigma_p
        subject to w'mu = mu_p
                   w'cov(R)w = var_p
                   s.t sum(weights) = 1
        """
        # get count of assets in portfolio
        total_assets = self.security_count

        # make random guess
        guess_weights = Harry.random_weights(nsim=1, nsec=total_assets)

        target_variance = target_vol ** 2

        # set target return & target variance and sum of weights constraint
        consts = [
            {
                "type": "eq",
                "fun": lambda w: self.portfolio_expected_return(w) - target_return,
            },
            {
                "type": "eq",
                "fun": lambda w: self.portfolio_variance(w) - target_variance,
            },
            {"type": "eq", "fun": lambda w: sum(w) - 1},
        ]

        # maximize sharpe subject to above constraints
        weights = minimize(
            fun=lambda w: -1 * self.sharpe_ratio(w),
            x0=guess_weights,
            constraints=consts,
            method="SLSQP",
            bounds=[(0, 1) for _ in range(total_assets)],
        )["x"]

        return weights
