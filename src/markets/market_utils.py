import json
import logging
import time
from typing import Optional, List
import requests
from decimal import Decimal

from utils import get_config, generate_signature, global_cache, APIEndpoints, APIPaths, init_global_cache
from .models import Precision, LeverageInfo, LeverageBracket, ExchangeInfo, TickerResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_symbol_precision(symbol: str) -> Optional[Precision]:
    """
    获取交易对下单精度要求
    
    Args:
        symbol: 交易对符号，例如 'BTCUSDT'
        
    Returns:
        Precision 对象，包含精度信息，如果未找到则返回 None
    """
    # 确保缓存已初始化
    if global_cache is None:
        logger.warning("缓存未初始化，尝试初始化...")
        init_global_cache()
        if global_cache is None:
            logger.error("缓存初始化失败")
            return None
    
    # 尝试从缓存获取
    cache_key = f"Precision_{symbol}"
    try:
        cached_value, found = global_cache.get(cache_key)
        if found and isinstance(cached_value, Precision):
            return cached_value
    except Exception as e:
        logger.error(f"从缓存获取数据时发生错误: {e}")
    
    try:
        # 从API获取数据
        api_url = f"{APIEndpoints.FAPI}{APIPaths.EXCHANGE_INFO}"
        logger.info(f"请求交易所信息: {api_url}")
        response = requests.get(api_url)
        response.raise_for_status()
        
        # 打印响应内容以便调试
        response_data = response.json()
        logger.debug(f"API响应: {response_data}")
        
        if not isinstance(response_data, dict):
            logger.error(f"API响应格式错误: 期望dict，实际是{type(response_data)}")
            return None
            
        if 'symbols' not in response_data:
            logger.error("API响应中缺少'symbols'字段")
            return None
            
        # 只传 symbols 字段
        exchange_info = ExchangeInfo(symbols=response_data['symbols'])
        
        # 查找指定交易对
        symbol_found = False
        for symbol_info in exchange_info.symbols:
            if symbol_info['symbol'] == symbol:
                symbol_found = True
                precision = Precision(
                    symbol=symbol_info['symbol'],
                    base_asset_precision=symbol_info['baseAssetPrecision'],
                    price_precision=symbol_info['pricePrecision'],
                    quantity_precision=symbol_info['quantityPrecision'],
                    quote_precision=symbol_info['quotePrecision']
                )
                
                # 缓存结果（36小时）
                try:
                    global_cache.set(cache_key, precision, 36 * 3600)
                except Exception as e:
                    logger.error(f"缓存数据时发生错误: {e}")
                return precision
        
        if not symbol_found:
            logger.warning(f"Symbol {symbol} not found in exchange info")
            return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API请求失败: {e}")
        return None
    except Exception as e:
        logger.error(f"获取交易对精度时发生错误: {e}")
        logger.exception("详细错误信息:")
        return None

def get_latest_price(symbol: str) -> Optional[str]:
    """
    获取最新价格
    
    Args:
        symbol: 交易对符号，例如 'BTCUSDT'
        
    Returns:
        最新价格字符串，如果获取失败则返回 None
    """
    try:
        url = f"{APIEndpoints.API0}{APIPaths.PRICE}?symbol={symbol}"
        response = requests.get(url)
        response.raise_for_status()
        
        ticker = TickerResponse(**response.json())
        return ticker.price
        
    except Exception as e:
        logger.error(f"Error getting latest price: {e}")
        return None

def get_max_leverage(symbol: str) -> Optional[LeverageInfo]:
    """
    获取最大杠杆信息
    
    Args:
        symbol: 交易对符号，例如 'BTCUSDT'
        
    Returns:
        LeverageInfo 对象，包含最大杠杆信息，如果获取失败则返回 None
    """
    # 确保缓存已初始化
    if global_cache is None:
        logger.warning("缓存未初始化，尝试初始化...")
        init_global_cache()
        if global_cache is None:
            logger.error("缓存初始化失败")
            return None
    
    # 尝试从缓存获取
    cache_key = f"Leverage_{symbol}"
    try:
        cached_value, found = global_cache.get(cache_key)
        if found and isinstance(cached_value, LeverageInfo):
            return cached_value
    except Exception as e:
        logger.error(f"从缓存获取数据时发生错误: {e}")
    
    try:
        config = get_config()
        timestamp = str(int(time.time() * 1000))
        
        # 构建查询字符串和签名
        query_string = f"symbol={symbol}&timestamp={timestamp}"
        signature = generate_signature(query_string, config.secret_key)
        
        # 构建API URL
        api_url = f"{APIEndpoints.FAPI}{APIPaths.LEVERAGE_BRACKET}?{query_string}&signature={signature}"
        logger.info(f"请求杠杆信息: {api_url}")
        
        # 发送请求
        headers = {"X-MBX-APIKEY": config.api_key}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        # 打印响应内容以便调试
        response_data = response.json()
        logger.debug(f"API响应: {response_data}")
        
        if not isinstance(response_data, list):
            logger.error(f"API响应格式错误: 期望list，实际是{type(response_data)}")
            return None
        
        # 找到 symbol 匹配的项
        target = None
        for item in response_data:
            if item.get('symbol') == symbol:
                target = item
                break
        if not target:
            logger.error(f"未找到 {symbol} 的杠杆档位数据")
            return None
        
        leverage_brackets: List[LeverageBracket] = []
        for bracket in target['brackets']:
            try:
                leverage_brackets.append(
                    LeverageBracket(
                        bracket=bracket['bracket'],
                        leverage=bracket['initialLeverage'],
                        maint_margin_ratio=bracket['maintMarginRatio']
                    )
                )
            except Exception as e:
                logger.error(f"解析杠杆档位数据失败: {e}, 数据: {bracket}")
                continue
        
        if not leverage_brackets:
            logger.error("没有找到有效的杠杆档位数据")
            return None
        
        # 找出最大杠杆
        max_leverage_info = None
        max_leverage = 0
        
        for bracket in leverage_brackets:
            if bracket.leverage > max_leverage:
                max_leverage = bracket.leverage
                max_leverage_info = LeverageInfo(
                    leverage=bracket.leverage,
                    maint_margin_ratio=bracket.maint_margin_ratio
                )
        
        if max_leverage_info:
            # 缓存结果
            try:
                global_cache.set(cache_key, max_leverage_info, 3600)  # 缓存1小时
            except Exception as e:
                logger.error(f"缓存数据时发生错误: {e}")
            return max_leverage_info
            
        logger.warning(f"未找到 {symbol} 的杠杆信息")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API请求失败: {e}")
        return None
    except Exception as e:
        logger.error(f"获取最大杠杆时发生错误: {e}")
        logger.exception("详细错误信息:")
        return None

# Example usage
if __name__ == "__main__":
    # 测试获取交易对精度
    symbol = "BTCUSDT"
    precision = get_symbol_precision(symbol)
    if precision:
        print(f"\nPrecision for {symbol}:")
        print(f"Base Asset Precision: {precision.base_asset_precision}")
        print(f"Price Precision: {precision.price_precision}")
        print(f"Quantity Precision: {precision.quantity_precision}")
        print(f"Quote Precision: {precision.quote_precision}")
    
    # 测试获取最新价格
    price = get_latest_price(symbol)
    if price:
        print(f"\nLatest price for {symbol}: {price}")
    
    # 测试获取最大杠杆
    leverage_info = get_max_leverage(symbol)
    if leverage_info:
        print(f"\nMax leverage for {symbol}:")
        print(f"Leverage: {leverage_info.leverage}")
        print(f"Maintenance Margin Ratio: {leverage_info.maint_margin_ratio}") 