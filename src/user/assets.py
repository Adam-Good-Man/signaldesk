import sys
import os
# 将项目根目录（即当前目录的父目录）加入 sys.path，以便找到 utils 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import requests
import logging
from decimal import Decimal
from utils import get_config, generate_signature, APIEndpoints

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_spot_assets(min_usdt: float = 1.0):
    """获取现货账户所有大于min_usdt价值的资产"""
    config = get_config()
    timestamp = int(time.time() * 1000)
    params = f'timestamp={timestamp}'
    signature = generate_signature(params, config.secret_key)
    url = f"{APIEndpoints.API0}/api/v3/account?{params}&signature={signature}"
    headers = {"X-MBX-APIKEY": config.api_key}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    balances = data.get('balances', [])
    # 获取所有币种的余额
    assets = {}
    for b in balances:
        free = Decimal(b['free'])
        locked = Decimal(b['locked'])
        total = free + locked
        if total > 0:
            assets[b['asset']] = total
    return assets

def get_futures_assets(min_usdt: float = 1.0):
    """获取合约账户所有大于min_usdt价值的资产"""
    config = get_config()
    timestamp = int(time.time() * 1000)
    params = f'timestamp={timestamp}'
    signature = generate_signature(params, config.secret_key)
    url = f"{APIEndpoints.FAPI}/fapi/v2/account?{params}&signature={signature}"
    headers = {"X-MBX-APIKEY": config.api_key}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    assets = {}
    for a in data.get('assets', []):
        asset = a['asset']
        wallet_balance = Decimal(a['walletBalance'])
        if wallet_balance > 0:
            assets[asset] = wallet_balance
    return assets

def get_usdt_prices(symbols):
    """获取币种兑USDT的价格，返回dict"""
    url = f"{APIEndpoints.API0}/api/v3/ticker/price"
    resp = requests.get(url)
    resp.raise_for_status()
    prices = resp.json()
    price_map = {}
    for p in prices:
        sym = p['symbol']
        if sym.endswith('USDT'):
            base = sym[:-4]
            price_map[base] = Decimal(p['price'])
    # USDT本身价格为1
    price_map['USDT'] = Decimal('1')
    return {s: price_map.get(s, Decimal('0')) for s in symbols}

def print_user_assets(min_usdt: float = 1.0):
    """输出所有大于min_usdt USDT价值的现货和合约资产"""
    logger.info('获取现货资产...')
    spot_assets = get_spot_assets(min_usdt)
    logger.info('获取合约资产...')
    futures_assets = get_futures_assets(min_usdt)
    all_assets = spot_assets.copy()
    for k, v in futures_assets.items():
        all_assets[k] = all_assets.get(k, Decimal('0')) + v
    # 获取所有币种兑USDT价格
    prices = get_usdt_prices(all_assets.keys())
    logger.info('大于 %.2f USDT 的资产如下：', min_usdt)
    print(f"{'币种':<8}{'总数量':>20}{'估值(USDT)':>20}")
    print('-'*48)
    for asset, amount in all_assets.items():
        price = prices.get(asset, Decimal('0'))
        usdt_value = amount * price
        if usdt_value >= Decimal(str(min_usdt)):
            print(f"{asset:<8}{amount:>20.8f}{usdt_value:>20.4f}")

if __name__ == "__main__":
    print_user_assets(1.0) 