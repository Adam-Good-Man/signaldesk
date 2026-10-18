import logging
import time
import os
from typing import Optional

from utils import init_global_cache, get_config
from markets import (
    get_symbol_precision,
    get_latest_price,
    get_max_leverage,
    Precision,
    LeverageInfo
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_configuration() -> bool:
    """检查配置是否正确"""
    try:
        config = get_config()
        if not config.api_key or not config.secret_key:
            logger.error("API 密钥未配置！请创建 .env 文件并设置以下环境变量：")
            logger.error("API_KEY=your_api_key_here")
            logger.error("SECRET_KEY=your_secret_key_here")
            logger.error("\n你可以从 Binance 网站获取这些密钥：")
            logger.error("https://www.binance.com/en/my/settings/api-management")
            return False
        return True
    except Exception as e:
        logger.error(f"配置检查失败: {e}")
        return False

def initialize_cache() -> bool:
    """初始化缓存系统"""
    try:
        init_global_cache()
        return True
    except Exception as e:
        logger.error(f"缓存初始化失败: {e}")
        return False

def test_symbol_precision(symbol: str) -> None:
    """测试获取交易对精度"""
    logger.info(f"\n=== 测试获取 {symbol} 交易对精度 ===")
    
    try:
        # 第一次获取（从API）
        start_time = time.time()
        precision = get_symbol_precision(symbol)
        api_time = time.time() - start_time
        
        if precision:
            logger.info(f"API获取耗时: {api_time:.3f}秒")
            logger.info(f"交易对: {precision.symbol}")
            logger.info(f"基础资产精度: {precision.base_asset_precision}")
            logger.info(f"价格精度: {precision.price_precision}")
            logger.info(f"数量精度: {precision.quantity_precision}")
            logger.info(f"计价资产精度: {precision.quote_precision}")
        else:
            logger.error(f"获取 {symbol} 精度信息失败")
            return
        
        # 第二次获取（从缓存）
        start_time = time.time()
        cached_precision = get_symbol_precision(symbol)
        cache_time = time.time() - start_time
        
        if cached_precision:
            logger.info(f"缓存获取耗时: {cache_time:.3f}秒")
            logger.info("缓存数据验证: " + 
                       ("成功" if precision == cached_precision else "失败"))
    except Exception as e:
        logger.error(f"测试交易对精度时发生错误: {e}")

def test_latest_price(symbol: str) -> None:
    """测试获取最新价格"""
    logger.info(f"\n=== 测试获取 {symbol} 最新价格 ===")
    
    try:
        # 获取价格
        start_time = time.time()
        price = get_latest_price(symbol)
        api_time = time.time() - start_time
        
        if price:
            logger.info(f"获取耗时: {api_time:.3f}秒")
            logger.info(f"最新价格: {price}")
        else:
            logger.error(f"获取 {symbol} 最新价格失败")
    except Exception as e:
        logger.error(f"测试最新价格时发生错误: {e}")

def test_max_leverage(symbol: str) -> None:
    """测试获取最大杠杆"""
    logger.info(f"\n=== 测试获取 {symbol} 最大杠杆 ===")
    
    try:
        # 第一次获取（从API）
        start_time = time.time()
        leverage_info = get_max_leverage(symbol)
        api_time = time.time() - start_time
        
        if leverage_info:
            logger.info(f"API获取耗时: {api_time:.3f}秒")
            logger.info(f"最大杠杆: {leverage_info.leverage}")
            logger.info(f"维持保证金率: {leverage_info.maint_margin_ratio}")
        else:
            logger.error(f"获取 {symbol} 杠杆信息失败")
            return
        
        # 第二次获取（从缓存）
        start_time = time.time()
        cached_leverage = get_max_leverage(symbol)
        cache_time = time.time() - start_time
        
        if cached_leverage:
            logger.info(f"缓存获取耗时: {cache_time:.3f}秒")
            logger.info("缓存数据验证: " + 
                       ("成功" if leverage_info == cached_leverage else "失败"))
    except Exception as e:
        logger.error(f"测试最大杠杆时发生错误: {e}")

def run_all_tests(symbol: str) -> None:
    """运行所有测试"""
    logger.info(f"开始测试 {symbol} 的所有功能...")
    
    # 检查配置
    if not check_configuration():
        return
    
    # 初始化缓存
    if not initialize_cache():
        logger.error("缓存初始化失败，无法继续测试")
        return
    
    try:
        # 运行所有测试
        test_symbol_precision(symbol)
        test_latest_price(symbol)
        test_max_leverage(symbol)
        
        logger.info("\n=== 所有测试完成 ===")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
    finally:
        logger.info("\n" + "=" * 50 + "\n")

if __name__ == "__main__":
    # 测试交易对列表
    test_symbols = ["PEOPLEUSDT"]
    
    # 运行所有测试
    for symbol in test_symbols:
        run_all_tests(symbol)
