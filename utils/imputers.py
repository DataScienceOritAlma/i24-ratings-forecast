# -*- coding: utf-8 -*-
"""Custom imputers used in the training pipeline.

These need to live in a shared module so both training and prediction code
can import them by the same fully-qualified name (utils.imputers.X) — that
way joblib pickle/unpickle resolves correctly across scripts.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class SimpleMedianImputer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        X = pd.DataFrame(X).apply(pd.to_numeric, errors="coerce")
        self.medians_ = X.median()
        return self

    def transform(self, X):
        X = pd.DataFrame(X).apply(pd.to_numeric, errors="coerce")
        return X.fillna(self.medians_).values


class SimpleConstantImputer(BaseEstimator, TransformerMixin):
    def __init__(self, fill):
        self.fill = fill

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = pd.DataFrame(X)
        return X.fillna(self.fill).values
