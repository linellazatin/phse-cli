"""Dividends package — dividend tracking."""

from .dividends import (
    dividend_add,
    dividend_list,
    dividend_remove,
    dividend_upcoming,
)

__all__ = ["dividend_add", "dividend_remove", "dividend_list", "dividend_upcoming"]
