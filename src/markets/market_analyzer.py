import logging
import requests
from typing import Dict, Optional, Tuple
from decimal import Decimal
import time
from dataclasses import dataclass
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class OrderBookLevel:
    """订单簿价格档位"""
    price: Decimal
    quantity: Decimal
    total_quantity: Decimal  # 累计数量

class FuturesMarketAnalyzer:
    """合约市场深度分析器"""
    
    def __init__(self, symbol: str, testnet: bool = False):
        """
        初始化合约市场分析器
        :param symbol: 交易对，例如 'PEOPLEUSDT'
        :param testnet: 是否使用测试网络
        """
        self.symbol = symbol.upper()
        self.testnet = testnet
        # 使用合约 API 端点
        self.base_url = 'https://testnet.binancefuture.com/fapi/v1' if testnet else 'https://fapi.binance.com/fapi/v1'
        
        # 订单簿数据
        self.bids: Dict[str, OrderBookLevel] = {}  # 买单 {price: OrderBookLevel}
        self.asks: Dict[str, OrderBookLevel] = {}  # 卖单 {price: OrderBookLevel}
        self.last_update_id = 0
        
        # 分析参数
        self.price_precision = 8  # 价格精度
        self.quantity_precision = 3  # 数量精度
    
    def get_depth(self, limit: int = 100) -> Optional[Dict]:
        """
        获取合约市场深度数据
        :param limit: 深度档位数量，最大1000
        :return: 深度数据字典
        """
        try:
            url = f"{self.base_url}/depth"
            params = {
                'symbol': self.symbol,
                'limit': min(limit, 1000)  # 限制最大档位为1000
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 更新订单簿
            self._update_order_book(data)
            
            # 分析数据
            analysis = self._analyze_depth()
            
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': self.symbol,
                'last_update_id': self.last_update_id,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"获取深度数据失败: {e}")
            return None
    
    def _update_order_book(self, data: Dict):
        """更新订单簿数据"""
        # 更新买单
        total_bid_qty = Decimal('0')
        for price, quantity in data['bids']:
            price = Decimal(price)
            quantity = Decimal(quantity)
            total_bid_qty += quantity
            self.bids[str(price)] = OrderBookLevel(
                price=price,
                quantity=quantity,
                total_quantity=total_bid_qty
            )
        
        # 更新卖单
        total_ask_qty = Decimal('0')
        for price, quantity in data['asks']:
            price = Decimal(price)
            quantity = Decimal(quantity)
            total_ask_qty += quantity
            self.asks[str(price)] = OrderBookLevel(
                price=price,
                quantity=quantity,
                total_quantity=total_ask_qty
            )
        
        self.last_update_id = data['lastUpdateId']
    
    def _analyze_depth(self) -> Dict:
        """分析深度数据"""
        if not self.bids or not self.asks:
            return {}
        
        # 获取最优价格
        best_bid = max(self.bids.values(), key=lambda x: x.price)
        best_ask = min(self.asks.values(), key=lambda x: x.price)
        mid_price = (best_bid.price + best_ask.price) / 2
        
        # 计算价格区间
        price_range = mid_price * Decimal('0.01')  # 中间价格上下1%的范围
        min_price = mid_price - price_range
        max_price = mid_price + price_range
        
        # 分析买单
        bid_analysis = {
            'total_quantity': sum(level.quantity for level in self.bids.values()),
            'total_orders': len(self.bids),
            'price_levels': {
                'min': min(level.price for level in self.bids.values()),
                'max': max(level.price for level in self.bids.values()),
                'mid': mid_price
            },
            'large_orders': self._find_large_orders(self.bids, min_price, max_price)
        }
        
        # 分析卖单
        ask_analysis = {
            'total_quantity': sum(level.quantity for level in self.asks.values()),
            'total_orders': len(self.asks),
            'price_levels': {
                'min': min(level.price for level in self.asks.values()),
                'max': max(level.price for level in self.asks.values()),
                'mid': mid_price
            },
            'large_orders': self._find_large_orders(self.asks, min_price, max_price)
        }
        
        return {
            'mid_price': float(mid_price),
            'spread': float(best_ask.price - best_bid.price),
            'spread_percentage': float((best_ask.price - best_bid.price) / mid_price * 100),
            'bids': bid_analysis,
            'asks': ask_analysis
        }
    
    def _find_large_orders(self, orders: Dict[str, OrderBookLevel], 
                          min_price: Decimal, max_price: Decimal, 
                          threshold: Decimal = Decimal('1000')) -> list:
        """查找大单"""
        large_orders = []
        for level in orders.values():
            if min_price <= level.price <= max_price and level.quantity >= threshold:
                large_orders.append({
                    'price': float(level.price),
                    'quantity': float(level.quantity),
                    'total_quantity': float(level.total_quantity)
                })
        return sorted(large_orders, key=lambda x: x['quantity'], reverse=True)

def analyze_market_depth(symbol: str, testnet: bool = False) -> Optional[Dict]:
    """
    分析指定交易对的市场深度
    :param symbol: 交易对，例如 'PEOPLEUSDT'
    :param testnet: 是否使用测试网络
    :return: 分析结果
    """
    analyzer = FuturesMarketAnalyzer(symbol, testnet)
    return analyzer.get_depth()

if __name__ == "__main__":
    # 使用示例
    symbol = "PEOPLEUSDT"
    result = analyze_market_depth(symbol, testnet=True)
    
    if result:
        logger.info(f"\n=== {symbol} 市场深度分析 ===")
        logger.info(f"时间: {result['timestamp']}")
        logger.info(f"中间价格: {result['analysis']['mid_price']:.8f}")
        logger.info(f"价差: {result['analysis']['spread']:.8f} ({result['analysis']['spread_percentage']:.2f}%)")
        
        # 买单分析
        bids = result['analysis']['bids']
        logger.info("\n买单分析:")
        logger.info(f"总数量: {bids['total_quantity']:.3f}")
        logger.info(f"订单数: {bids['total_orders']}")
        logger.info(f"价格范围: {bids['price_levels']['min']:.8f} - {bids['price_levels']['max']:.8f}")
        
        # 卖单分析
        asks = result['analysis']['asks']
        logger.info("\n卖单分析:")
        logger.info(f"总数量: {asks['total_quantity']:.3f}")
        logger.info(f"订单数: {asks['total_orders']}")
        logger.info(f"价格范围: {asks['price_levels']['min']:.8f} - {asks['price_levels']['max']:.8f}")
        
        # 大单分析
        logger.info("\n买单大单:")
        for order in bids['large_orders'][:5]:  # 显示前5个大单
            logger.info(f"价格: {order['price']:.8f}, 数量: {order['quantity']:.3f}")
        
        logger.info("\n卖单大单:")
        for order in asks['large_orders'][:5]:  # 显示前5个大单
            logger.info(f"价格: {order['price']:.8f}, 数量: {order['quantity']:.3f}")
        
        logger.info("\n=== 分析结束 ===")
    else:
        logger.error("获取市场深度数据失败")
