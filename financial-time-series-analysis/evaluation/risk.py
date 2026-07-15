"""Alias delle baseline di rischio per l'API evaluation."""

from baselines.risk import filtered_historical_var, historical_var, normal_var, student_t_var

__all__ = ["historical_var", "normal_var", "student_t_var", "filtered_historical_var"]
