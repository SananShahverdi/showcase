# ADR 0001: Honest evaluation over impressive numbers

## Status

Accepted.

## Context

The source scripts trained models with a shuffled train/test split, used same-day high/low prices to predict the close, fitted decompositions and scalers on the full series, computed indicators on newest-first data, and included an RL agent whose update did nothing. They produced convincing-looking results that could not be trusted.

## Decision

- Evaluate only out of sample, walk-forward, against a random-walk baseline with a significance test.
- Build features strictly from data available at each close, and test that property.
- Trade signals on the next bar with explicit costs, and always show buy and hold beside the strategy.
- Implement GARCH and the statistical tests directly with NumPy and SciPy so every number is inspectable.
- Remove components that do not work instead of labeling them as features.

## Consequences

- The headline results are modest, and that is the finding: on liquid assets, simple features rarely beat a random walk. This is more credible to a technical reviewer than inflated accuracy.
- Walk-forward retraining is slower than a single split, so results are cached per parameter set.
