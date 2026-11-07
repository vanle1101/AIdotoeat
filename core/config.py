"""
Zero-Cost Corp Core Configuration
Strict Enforcement of the ABSOLUTE ZERO-COST POLICY (0 VND Hardcap)
"""
from dataclasses import dataclass
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "company.db"
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class ZeroCostPolicy:
    # 1. HARD FINANCIAL BOUNDARIES
    HARD_BUDGET_CAP_VND: float = 0.0
    ALLOW_PAID_APIS: bool = False
    ALLOW_CREDIT_CARD_INPUT: bool = False
    ALLOW_AUTO_BILLING: bool = False
    ALLOW_PAID_HOSTING: bool = False

    # 2. RUNTIME & CONCURRENCY CONSTRAINTS
    MAX_CONCURRENT_AGENTS: int = 1   # Single worker to prevent rate limits & RAM bloat
    TOKEN_CHATTER_LIMIT_PER_STEP: int = 0  # No idle agent-to-agent chit chat
    RATE_LIMIT_COOLDOWN_SECONDS: int = 15  # Fallback pause when free tier throttled

    # 3. OWNER CONTROL
    REQUIRE_OWNER_CONFIRMATION_ON_PAYMENT: bool = True
    ALLOW_AI_SELF_REINVESTMENT: bool = False  # Revenue always stays with Owner

POLICY = ZeroCostPolicy()
