import os
import logging
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Endpoints
class APIEndpoints:
    TEST_API = "https://testnet.binance.vision"
    STREAM_WSS = "wss://stream.binance.com:9443"
    FAPI = "https://fapi.binance.com"
    API0 = "https://api.binance.com"
    API1 = "https://api1.binance.com"
    API2 = "https://api2.binance.com"
    API3 = "https://api3.binance.com"
    API4 = "https://api4.binance.com"

# API Paths
class APIPaths:
    EXCHANGE_INFO = "/fapi/v1/exchangeInfo"
    LEVERAGE = "/fapi/v1/leverage"
    PRICE = "/api/v3/ticker/price"
    ORDER = "/fapi/v1/order"
    MARGIN_TYPE = "/fapi/v1/marginType"
    LEVERAGE_BRACKET = "/fapi/v1/leverageBracket"
    POSITION_MARGIN = "/fapi/v1/positionMargin"
    BOOK_TICKER = "/api/v3/ticker/bookTicker"

@dataclass
class Config:
    """Configuration class for storing application settings"""
    api_key: str
    secret_key: str
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'Config':
        """Create a Config instance from a dictionary"""
        return cls(
            api_key=config_dict.get('BINANCE_API_KEY', ''),
            secret_key=config_dict.get('BINANCE_SECRET_KEY', '')
        )

class ConfigManager:
    """Manages application configuration"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the configuration manager"""
        if self._config is None:
            self._load_config()
    
    def _load_config(self, config_path: str = ".") -> None:
        """
        Load configuration from .env file and environment variables
        
        Args:
            config_path: Path to the directory containing the .env file
        """
        try:
            # Convert to Path object for better path handling
            path = Path(config_path).resolve()  # 使用绝对路径
            env_path = path / ".env"
            
            logger.info(f"Looking for .env file at: {env_path}")
            
            # Load .env file if it exists
            if env_path.exists():
                logger.info(f"Found .env file at: {env_path}")
                load_dotenv(env_path, override=True)  # 添加 override=True
            else:
                logger.warning(f".env file not found at: {env_path}")
                # 尝试在当前工作目录查找
                cwd_env_path = Path.cwd() / ".env"
                if cwd_env_path.exists():
                    logger.info(f"Found .env file in current working directory: {cwd_env_path}")
                    load_dotenv(cwd_env_path, override=True)
                else:
                    logger.warning(f".env file not found in current working directory: {cwd_env_path}")
            
            # 打印环境变量（不显示实际值）
            api_key = os.getenv('BINANCE_API_KEY')
            secret_key = os.getenv('BINANCE_SECRET_KEY')
            logger.info(f"API_KEY present: {'Yes' if api_key else 'No'}")
            logger.info(f"SECRET_KEY present: {'Yes' if secret_key else 'No'}")
            
            # Create config from environment variables
            config_dict = {
                'API_KEY': api_key or '',
                'SECRET_KEY': secret_key or ''
            }
            
            self._config = Config.from_dict(config_dict)
            
            # Validate required configuration
            if not self._config.api_key or not self._config.secret_key:
                logger.warning("API key or secret key not found in configuration")
                logger.warning("Please ensure your .env file contains:")
                logger.warning("API_KEY=your_api_key_here")
                logger.warning("SECRET_KEY=your_secret_key_here")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    @property
    def config(self) -> Config:
        """Get the current configuration"""
        if self._config is None:
            self._load_config()
        return self._config
    
    def reload(self, config_path: str = ".") -> None:
        """Reload the configuration"""
        self._load_config(config_path)

# Global configuration instance
config_manager = ConfigManager()

def get_config() -> Config:
    """Get the current configuration"""
    return config_manager.config

# Example usage
if __name__ == "__main__":
    try:
        # Get configuration
        config = get_config()
        
        # Print configuration (excluding sensitive data)
        logger.info("Configuration loaded successfully")
        logger.info(f"API Key present: {'Yes' if config.api_key else 'No'}")
        logger.info(f"Secret Key present: {'Yes' if config.secret_key else 'No'}")
        
        # Example of accessing API endpoints
        logger.info(f"Test API endpoint: {APIEndpoints.TEST_API}")
        logger.info(f"Futures API endpoint: {APIEndpoints.FAPI}")
        
    except Exception as e:
        logger.error(f"Error in configuration: {e}") 