from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal

@dataclass
class Precision:
    """交易对精度信息"""
    symbol: str
    base_asset_precision: int
    price_precision: int
    quantity_precision: int
    quote_precision: int

@dataclass
class LeverageInfo:
    """杠杆信息"""
    leverage: int
    maint_margin_ratio: float

@dataclass
class LeverageBracket:
    """杠杆档位信息"""
    bracket: int
    leverage: int
    maint_margin_ratio: float

@dataclass
class ExchangeInfo:
    """交易所信息"""
    symbols: List[dict]

@dataclass
class TickerResponse:
    """价格响应"""
    symbol: str
    price: str 