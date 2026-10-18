import sys
import os
# 将项目根目录（即当前目录的父目录）加入 sys.path，以便找到 utils 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import logging
import time
import urllib.parse
from decimal import Decimal
from utils import get_config, generate_signature, APIEndpoints, APIPaths
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def set_leverage(symbol: str, leverage: int) -> bool:
    """设置杠杆倍率"""
    config = get_config()
    api_url = f"{APIEndpoints.FAPI}{APIPaths.LEVERAGE}"
    data = {
        "symbol": symbol,
        "leverage": str(leverage),
        "timestamp": str(int(time.time() * 1000))
    }
    query_string = urllib.parse.urlencode(data)
    signature = generate_signature(query_string, config.secret_key)
    data["signature"] = signature
    headers = {"X-MBX-APIKEY": config.api_key, "Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(api_url, data=data, headers=headers)
    if resp.status_code == 200:
        return True
    else:
        logger.error("Failed to set leverage: %s", resp.text)
        return False


def place_order(amount: float, symbol: str, side: str, position_side: str, price: Optional[float] = None, time_in_force: str = "GTC") -> None:
    """下单（市价单或限价单）。如果 price 不为 None，则自动转为 LIMIT 单，否则为 MARKET 单。"""
    config = get_config()
    from markets.market_utils import get_symbol_precision
    precision_info = get_symbol_precision(symbol)
    if not precision_info:
        logger.error("get precision error")
        return
    api_url = f"{APIEndpoints.FAPI}{APIPaths.ORDER}"
    data = {
        "symbol": symbol,
        "side": side,  # BUY 或 SELL
        "type": "LIMIT" if price is not None else "MARKET",
        "positionSide": position_side,
        "quantity": str(round(amount, precision_info.quantity_precision)),
        "timestamp": str(int(time.time() * 1000))
    }
    if price is not None:
        data["price"] = str(round(price, precision_info.price_precision))
        data["timeInForce"] = time_in_force
    query_string = urllib.parse.urlencode(data)
    signature = generate_signature(query_string, config.secret_key)
    data["signature"] = signature
    headers = {"X-MBX-APIKEY": config.api_key, "Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(api_url, data=data, headers=headers)
    if resp.status_code != 200:
        logger.error("下单失败: %s", resp.text)


def set_margin_type(symbol: str, margin_type: str) -> bool:
    """设置保证金模式（全仓 CROSSED 或逐仓 ISOLATED）"""
    config = get_config()
    api_url = f"{APIEndpoints.FAPI}{APIPaths.MARGIN_TYPE}"
    data = {
        "symbol": symbol,
        "marginType": margin_type,
        "timestamp": str(int(time.time() * 1000))
    }
    query_string = urllib.parse.urlencode(data)
    signature = generate_signature(query_string, config.secret_key)
    data["signature"] = signature
    headers = {"X-MBX-APIKEY": config.api_key, "Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(api_url, data=data, headers=headers)
    if resp.status_code == 200:
        return True
    else:
        logger.error("Failed to set margin type: %s", resp.text)
        return False


def adjust_position_margin(symbol: str, amount: float, adjust_type: int) -> None:
    """调整保证金"""
    config = get_config()
    from markets.market_utils import get_symbol_precision
    precision_info = get_symbol_precision(symbol)
    if not precision_info:
        logger.error("get precision error")
        return
    api_url = f"{APIEndpoints.FAPI}{APIPaths.POSITION_MARGIN}"
    data = {
        "symbol": symbol,
        "amount": str(round(amount, precision_info.price_precision)),
        "type": str(adjust_type),
        "timestamp": str(int(time.time() * 1000))
    }
    query_string = urllib.parse.urlencode(data)
    signature = generate_signature(query_string, config.secret_key)
    data["signature"] = signature
    headers = {"X-MBX-APIKEY": config.api_key, "Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(api_url, data=data, headers=headers)
    logger.info("Response: %s", resp.text)


if __name__ == "__main__":
    # 示例调用
    symbol = "PEOPLEUSDT"
    # 设置杠杆倍率
    set_leverage(symbol, 3)
    # 市价买入（不传 price 参数，自动转为 MARKET 单）
    # place_order(20, symbol, "BUY", "BOTH")
    # 定价合约交易（限价单，传入 price 参数，自动转为 LIMIT 单）
    place_order(20, symbol, "BUY", "BOTH", price=0.033, time_in_force="GTC")
    # 设置保证金模式（逐仓）
    set_margin_type(symbol, "ISOLATED")
    # 调整保证金
    # adjust_position_margin(symbol, 20, 1) 