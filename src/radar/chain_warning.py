from web3 import Web3
from typing import Dict, List, Optional, Generator
import logging
from datetime import datetime, timezone
import json
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChainWarningCollector:
    """Collector for monitoring blockchain transactions and detecting large transfers"""
    
    # Default thresholds for different tokens (in USD)
    DEFAULT_THRESHOLDS = {
        'ETH': 1000000,  # 1M USD
        'USDT': 5000000,  # 5M USD
        'USDC': 5000000,  # 5M USD
        'DAI': 5000000,  # 5M USD
        'WBTC': 1000000,  # 1M USD
    }
    
    # Common token addresses on Ethereum mainnet
    TOKEN_ADDRESSES = {
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
    }
    
    # ERC20 Transfer event signature
    TRANSFER_EVENT_SIGNATURE = 'Transfer(address,address,uint256)'
    
    def __init__(self, rpc_url: str, api_key: Optional[str] = None):
        """
        Initialize the collector with Web3 connection
        
        Args:
            rpc_url: Ethereum node RPC URL
            api_key: Optional API key for the RPC provider
        """
        try:
            # Initialize Web3
            if api_key and 'infura' in rpc_url.lower():
                rpc_url = f"{rpc_url}/{api_key}"
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if not self.w3.is_connected():
                raise ConnectionError("Failed to connect to Ethereum node")
            
            # Load token ABIs
            self.token_abi = self._load_token_abi()
            
            # Initialize token contracts
            self.token_contracts = {
                symbol: self.w3.eth.contract(
                    address=self.w3.to_checksum_address(address),
                    abi=self.token_abi
                )
                for symbol, address in self.TOKEN_ADDRESSES.items()
            }
            
            # Add ETH as a special case
            self.token_contracts['ETH'] = None
            
            logger.info("Successfully initialized ChainWarningCollector")
            
        except Exception as e:
            logger.error(f"Error initializing ChainWarningCollector: {str(e)}")
            raise

    def _load_token_abi(self) -> List[Dict]:
        """Load ERC20 token ABI"""
        # Minimal ABI for ERC20 token
        return [
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "from", "type": "address"},
                    {"indexed": True, "name": "to", "type": "address"},
                    {"indexed": False, "name": "value", "type": "uint256"}
                ],
                "name": "Transfer",
                "type": "event"
            }
        ]

    def _get_token_decimals(self, token_address: str) -> int:
        """Get token decimals"""
        try:
            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=self.token_abi
            )
            return contract.functions.decimals().call()
        except Exception as e:
            logger.error(f"Error getting decimals for token {token_address}: {str(e)}")
            return 18  # Default to 18 decimals

    def _get_token_symbol(self, token_address: str) -> str:
        """Get token symbol"""
        try:
            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=self.token_abi
            )
            return contract.functions.symbol().call()
        except Exception as e:
            logger.error(f"Error getting symbol for token {token_address}: {str(e)}")
            return "UNKNOWN"

    def _get_token_price(self, token_symbol: str) -> float:
        """
        Get token price in USD
        This is a placeholder - in production, you should use a price feed API
        """
        # TODO: Implement price feed integration (e.g., CoinGecko, Chainlink)
        return 1.0  # Placeholder

    def _get_block_number_by_timestamp(self, target_timestamp: int) -> int:
        """
        Find the block number closest to the given timestamp using binary search
        
        Args:
            target_timestamp: Unix timestamp to find block for
            
        Returns:
            Block number closest to the timestamp
        """
        try:
            # Get latest block
            latest_block = self.w3.eth.block_number
            latest_block_timestamp = self.w3.eth.get_block(latest_block)['timestamp']
            
            logger.info(f"Searching for block at timestamp {datetime.fromtimestamp(target_timestamp, timezone.utc)}")
            logger.info(f"Latest block {latest_block} timestamp: {datetime.fromtimestamp(latest_block_timestamp, timezone.utc)}")
            
            # If target timestamp is in the future, return latest block
            if target_timestamp >= latest_block_timestamp:
                logger.warning(f"Target timestamp {datetime.fromtimestamp(target_timestamp, timezone.utc)} is in the future, using latest block {latest_block}")
                return latest_block
                
            # Binary search to find the block
            left = 0
            right = latest_block
            
            while left <= right:
                mid = (left + right) // 2
                mid_block_timestamp = self.w3.eth.get_block(mid)['timestamp']
                
                if mid_block_timestamp == target_timestamp:
                    return mid
                elif mid_block_timestamp < target_timestamp:
                    left = mid + 1
                else:
                    right = mid - 1
            
            # Return the block with timestamp closest to target
            return left if abs(self.w3.eth.get_block(left)['timestamp'] - target_timestamp) < \
                           abs(self.w3.eth.get_block(right)['timestamp'] - target_timestamp) else right
            
        except Exception as e:
            logger.error(f"Error finding block by timestamp: {str(e)}")
            raise

    def monitor_large_transfers(
        self,
        hours_ago: int = 1,  # Default to last hour
        custom_thresholds: Optional[Dict[str, float]] = None,
        max_blocks_per_query: int = 100  # Maximum blocks to query at once
    ) -> Generator[Dict, None, None]:
        """
        Monitor blockchain for large transfers in the last N hours
        
        Args:
            hours_ago: Number of hours to look back (default: 1)
            custom_thresholds: Custom thresholds for different tokens in USD
            max_blocks_per_query: Maximum number of blocks to query at once
            
        Yields:
            Dictionary containing transfer information
        """
        try:
            # Calculate timestamp for N hours ago
            current_time = int(datetime.now(timezone.utc).timestamp())
            start_timestamp = current_time - (hours_ago * 3600)
            
            # Get block numbers for the time range
            end_block = self.w3.eth.block_number
            start_block = self._get_block_number_by_timestamp(start_timestamp)
            
            logger.info(f"Monitoring transfers from {hours_ago} hour{'s' if hours_ago != 1 else ''} ago (block {start_block} to {end_block})")
            logger.info(f"Monitoring transfers from {hours_ago} hours ago (block {start_block} to {end_block})")
            
            # Use custom thresholds if provided
            thresholds = custom_thresholds or self.DEFAULT_THRESHOLDS
            
            # Calculate event signature hash (ensure it's 32 bytes with 0x prefix)
            transfer_event_signature_hash = '0x' + self.w3.keccak(
                text=self.TRANSFER_EVENT_SIGNATURE
            ).hex()
            
            # Ensure the hash is 32 bytes (64 hex characters + '0x' prefix)
            if len(transfer_event_signature_hash) != 66:  # 0x + 64 hex chars
                raise ValueError(f"Invalid event signature hash length: {len(transfer_event_signature_hash)}")
            
            logger.debug(f"Event signature hash: {transfer_event_signature_hash}")
            
            # Split block range into smaller chunks
            current_start = start_block
            while current_start <= end_block:
                current_end = min(current_start + max_blocks_per_query - 1, end_block)
                
                logger.info(f"Querying blocks {current_start} to {current_end}")
                
                try:
                    # Get transfer event filter for current chunk
                    transfer_event_filter = self.w3.eth.filter({
                        'fromBlock': current_start,
                        'toBlock': current_end,
                        'topics': [transfer_event_signature_hash]
                    })
                    
                    # Get all transfer events for current chunk
                    events = transfer_event_filter.get_all_entries()
                    logger.info(f"Found {len(events)} transfer events in blocks {current_start} to {current_end}")
                    
                    for event in events:
                        try:
                            # Parse event data
                            token_address = event['address']
                            # Ensure addresses are properly formatted with 0x prefix
                            from_address = self.w3.to_checksum_address('0x' + event['topics'][1].hex()[-40:])
                            to_address = self.w3.to_checksum_address('0x' + event['topics'][2].hex()[-40:])
                            # Convert event data from bytes to hex string, then to integer
                            value = int(event['data'].hex(), 16)
                            
                            # Get token details
                            token_symbol = self._get_token_symbol(token_address)
                            decimals = self._get_token_decimals(token_address)
                            
                            # Calculate actual value
                            actual_value = value / (10 ** decimals)
                            
                            # Get token price and calculate USD value
                            token_price = self._get_token_price(token_symbol)
                            usd_value = actual_value * token_price
                            
                            # Check if transfer exceeds threshold
                            threshold = thresholds.get(token_symbol, thresholds['ETH'])
                            if usd_value >= threshold:
                                # Get transaction details
                                tx_hash = event['transactionHash'].hex()
                                tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                                tx = self.w3.eth.get_transaction(tx_hash)
                                
                                # Format and yield transfer information
                                yield {
                                    'timestamp': datetime.fromtimestamp(
                                        self.w3.eth.get_block(tx['blockNumber'])['timestamp'],
                                        timezone.utc
                                    ).isoformat(),
                                    'block_number': tx['blockNumber'],
                                    'transaction_hash': tx_hash,
                                    'token_symbol': token_symbol,
                                    'token_address': token_address,
                                    'from_address': from_address,
                                    'to_address': to_address,
                                    'amount': actual_value,
                                    'amount_usd': usd_value,
                                    'threshold_usd': threshold,
                                    'gas_price': tx['gasPrice'],
                                    'gas_used': tx_receipt['gasUsed'],
                                    'status': 'success' if tx_receipt['status'] == 1 else 'failed'
                                }
                                
                        except Exception as e:
                            logger.error(f"Error processing transfer event: {str(e)}")
                            continue
                            
                except Exception as e:
                    if 'query returned more than 10000 results' in str(e):
                        # If we hit the limit, reduce the block range and try again
                        new_max_blocks = max_blocks_per_query // 2
                        if new_max_blocks < 1:
                            logger.error("Block range too small to process")
                            break
                        logger.warning(f"Too many results, reducing block range to {new_max_blocks} blocks")
                        # Recursively call with smaller block range
                        yield from self.monitor_large_transfers(
                            hours_ago=hours_ago,
                            custom_thresholds=thresholds,
                            max_blocks_per_query=new_max_blocks
                        )
                    else:
                        logger.error(f"Error querying blocks {current_start} to {current_end}: {str(e)}")
                
                # Move to next chunk
                current_start = current_end + 1
                    
        except Exception as e:
            logger.error(f"Error monitoring large transfers: {str(e)}")
            raise

def main():
    """Test the ChainWarningCollector"""
    # Load environment variables
    load_dotenv()
    
    # Get RPC URL and API key
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    api_key = os.getenv('INFURA_API_KEY')
    
    if not rpc_url:
        logger.error("ETHEREUM_RPC_URL not found in environment variables")
        return
    
    try:
        # Initialize collector
        collector = ChainWarningCollector(rpc_url, api_key)
        
        # Monitor transfers from last hour
        logger.info("Starting to monitor large transfers from the last hour...")
        for transfer in collector.monitor_large_transfers(hours_ago=1):
            print("\n" + "="*100)
            print("🚨 LARGE TRANSFER DETECTED")
            print("="*100)
            print(f"Time: {transfer['timestamp']}")
            print(f"Block: {transfer['block_number']}")
            print(f"Transaction: {transfer['transaction_hash']}")
            print(f"\nToken: {transfer['token_symbol']}")
            print(f"Amount: {transfer['amount']:,.2f} {transfer['token_symbol']}")
            print(f"Value: ${transfer['amount_usd']:,.2f}")
            print(f"Threshold: ${transfer['threshold_usd']:,.2f}")
            print(f"\nFrom: {transfer['from_address']}")
            print(f"To: {transfer['to_address']}")
            print(f"\nGas Used: {transfer['gas_used']:,}")
            print(f"Status: {transfer['status']}")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
