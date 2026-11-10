"""Runtime configuration for the AUTOProfit backend.

Payout and affiliate values come only from the process environment. Keeping
them empty by default prevents a fresh checkout from publishing owner data.
"""
from __future__ import annotations

import os
import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env", override=False)
DATA_DIR = Path(os.getenv("AUTOPROFIT_DATA_DIR", "").strip() or str(BASE_DIR / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "company.db"
APPS_DIR = Path(os.getenv("AUTOPROFIT_APPS_DIR", "").strip() or str(BASE_DIR.parent / "frontend" / "apps")).resolve()
APPS_DIR.mkdir(parents=True, exist_ok=True)


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _https_url(name: str, value: str) -> None:
    if not value:
        return
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{name} must be an HTTPS URL without embedded credentials")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".local", ".internal")):
        raise ValueError(f"{name} must not target a local or internal host")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError(f"{name} must not target a private or reserved IP address")


@dataclass(frozen=True)
class OwnerFinanceConfig:
    BANK_NAME: str = ""
    BANK_ACCOUNT_NO: str = ""
    BANK_ACCOUNT_NAME: str = ""
    SECONDARY_BANK_NAME: str = ""
    SECONDARY_BANK_ACCOUNT_NO: str = ""
    SECONDARY_BANK_ACCOUNT_NAME: str = ""
    BINANCE_ID: str = ""
    BINANCE_USDT_BEP20: str = ""
    AADS_UNIT_ID_TOP: str = ""
    AADS_UNIT_ID_BOTTOM: str = ""
    MONETAG_TAG_ID: str = ""
    MONETAG_ZONE_ID: str = ""
    BINANCE_REF_ID: str = ""
    SHOPIFY_REF_URL: str = ""
    AMAZON_REF_URL: str = ""
    BSC_USDT_WALLET: str = ""
    BSC_RPC_URL: str = "https://bsc-dataseed.binance.org/"
    BSC_USDT_CONTRACT: str = "0x55d398326f99059ff775485246999027b3197955"

    def __post_init__(self) -> None:
        for prefix in ("", "SECONDARY_"):
            bank = getattr(self, f"{prefix}BANK_NAME")
            account = getattr(self, f"{prefix}BANK_ACCOUNT_NO")
            holder = getattr(self, f"{prefix}BANK_ACCOUNT_NAME")
            if any((bank, account, holder)) and not all((bank, account, holder)):
                raise ValueError(f"{prefix or 'primary '}bank name, account number, and account name must be configured together")
            if account and not re.fullmatch(r"\d{6,20}", account):
                raise ValueError(f"{prefix or 'primary '}bank account number must contain 6-20 digits")
            if bank and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{1,59}", bank):
                raise ValueError(f"{prefix or 'primary '}bank name contains invalid characters")
            if holder and (len(holder) > 100 or not re.fullmatch(r"[\w .'-]+", holder, re.UNICODE)):
                raise ValueError(f"{prefix or 'primary '}account name contains invalid characters")

        if self.BINANCE_ID and not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", self.BINANCE_ID):
            raise ValueError("Binance Pay ID has an invalid format")
        if self.BINANCE_USDT_BEP20 and not re.fullmatch(
            r"(?:Binance Pay ID:\s*)?\d{6,20}|0x[0-9a-fA-F]{40}", self.BINANCE_USDT_BEP20
        ):
            raise ValueError("Binance payment destination has an invalid format")
        for name in ("AADS_UNIT_ID_TOP", "AADS_UNIT_ID_BOTTOM"):
            value = getattr(self, name)
            if value and not re.fullmatch(r"\d{5,12}", value):
                raise ValueError(f"{name} must contain 5-12 digits")
        if self.MONETAG_TAG_ID and not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", self.MONETAG_TAG_ID):
            raise ValueError("MONETAG_TAG_ID has an invalid format")
        if self.MONETAG_ZONE_ID and not re.fullmatch(r"\d{3,12}", self.MONETAG_ZONE_ID):
            raise ValueError("MONETAG_ZONE_ID must contain 3-12 digits")
        if self.BINANCE_REF_ID and not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", self.BINANCE_REF_ID):
            raise ValueError("BINANCE_REF_ID has an invalid format")
        _https_url("SHOPIFY_REF_URL", self.SHOPIFY_REF_URL)
        _https_url("AMAZON_REF_URL", self.AMAZON_REF_URL)

        if self.BSC_USDT_WALLET and not re.fullmatch(r"0x[0-9a-fA-F]{40}", self.BSC_USDT_WALLET):
            raise ValueError("BSC_USDT_WALLET must be a 20-byte hexadecimal address")
        if self.BSC_USDT_CONTRACT and not re.fullmatch(r"0x[0-9a-fA-F]{40}", self.BSC_USDT_CONTRACT):
            raise ValueError("BSC_USDT_CONTRACT must be a 20-byte hexadecimal address")
        _https_url("BSC_RPC_URL", self.BSC_RPC_URL)


CONFIG = OwnerFinanceConfig(
    BANK_NAME=_env("AUTOPROFIT_BANK_NAME"),
    BANK_ACCOUNT_NO=_env("AUTOPROFIT_BANK_ACCOUNT_NO"),
    BANK_ACCOUNT_NAME=_env("AUTOPROFIT_BANK_ACCOUNT_NAME"),
    SECONDARY_BANK_NAME=_env("AUTOPROFIT_SECONDARY_BANK_NAME"),
    SECONDARY_BANK_ACCOUNT_NO=_env("AUTOPROFIT_SECONDARY_BANK_ACCOUNT_NO"),
    SECONDARY_BANK_ACCOUNT_NAME=_env("AUTOPROFIT_SECONDARY_BANK_ACCOUNT_NAME"),
    BINANCE_ID=_env("AUTOPROFIT_BINANCE_PAY_ID"),
    BINANCE_USDT_BEP20=_env("AUTOPROFIT_BINANCE_USDT_BEP20"),
    AADS_UNIT_ID_TOP=_env("AUTOPROFIT_AADS_UNIT_ID_TOP"),
    AADS_UNIT_ID_BOTTOM=_env("AUTOPROFIT_AADS_UNIT_ID_BOTTOM"),
    MONETAG_TAG_ID=_env("AUTOPROFIT_MONETAG_TAG_ID"),
    MONETAG_ZONE_ID=_env("AUTOPROFIT_MONETAG_ZONE_ID"),
    BINANCE_REF_ID=_env("AUTOPROFIT_BINANCE_REF_ID"),
    SHOPIFY_REF_URL=_env("AUTOPROFIT_SHOPIFY_REF_URL"),
    AMAZON_REF_URL=_env("AUTOPROFIT_AMAZON_REF_URL"),
    BSC_USDT_WALLET=_env("AUTOPROFIT_BSC_USDT_WALLET"),
    BSC_RPC_URL=_env("AUTOPROFIT_BSC_RPC_URL") or "https://bsc-dataseed.binance.org/",
    BSC_USDT_CONTRACT=_env("AUTOPROFIT_BSC_USDT_CONTRACT") or "0x55d398326f99059ff775485246999027b3197955",
)
