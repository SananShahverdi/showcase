# Demo script

1. Open Quant Research Lab from the portfolio and keep **Apple (AAPL) daily** selected.
2. Run the walk-forward study. Point out the finding: no model beats the random walk at the 5% level, and gradient boosting is significantly worse. Explain why the random-walk baseline and the Diebold-Mariano test matter.
3. Switch to **Signal strategy** and run the backtest. Compare CAGR, volatility, Sharpe, and drawdown with buy and hold. Raise trading cost to 50 bps and rerun to show how quickly an active signal erodes.
4. Switch the dataset to **Bitcoin** and rerun the strategy: the same signal loses money over this period.
5. Open **Risk** to show VaR, expected shortfall, GARCH persistence, and fat tails (excess kurtosis above 5 for AAPL).
6. Click **Download report** for the Markdown summary, or upload another CSV export.
