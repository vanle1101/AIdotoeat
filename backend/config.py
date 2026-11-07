"""
AUTOProfit AI Enterprise Configuration
Updated with Real Owner Credentials
"""
import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "company.db"
APPS_DIR = BASE_DIR.parent / "frontend" / "apps"
APPS_DIR.mkdir(parents=True, exist_ok=True)

class OwnerFinanceConfig(BaseModel):
    # Owner Direct Payout Settings
    BANK_NAME: str = "MB"
    BANK_ACCOUNT_NO: str = "0702543889"
    BANK_ACCOUNT_NAME: str = "LE HONG VAN"
    
    SECONDARY_BANK_NAME: str = "ACB"
    SECONDARY_BANK_ACCOUNT_NO: str = "36691617"
    SECONDARY_BANK_ACCOUNT_NAME: str = "LE HONG VAN"
    
    BINANCE_ID: str = "1225675522"
    BINANCE_USDT_BEP20: str = "Binance Pay ID: 1225675522"
    
    # Ad Network Monetization Settings
    AADS_UNIT_ID_TOP: str = "2460284"
    AADS_UNIT_ID_BOTTOM: str = "2460312"
    MONETAG_TAG_ID: str = "f8f0bb388a6f1dfc4e55e63df23354a2"
    
    # Affiliate Settings
    BINANCE_REF_ID: str = "1225675522"
    SHOPIFY_REF_URL: str = "https://tinyurl.com/2bj8pgjp"
    AMAZON_REF_URL: str = "https://tinyurl.com/22g5svtc"

CONFIG = OwnerFinanceConfig()
