"""Unverified seed ideas for an owner to investigate.

This module does not browse the web, observe demand, or perform AI inference.
"""
from typing import Dict, List


class MarketScout:
    """Return static ideas explicitly separated from verified opportunities."""

    SEED_IDEAS = [
        {"id": "NICHE_SCRAPER_ECOMMERCE", "title": "Cào dữ liệu sản phẩm & giá Shopee/Tiki/TikTok Shop",
         "evidence_status": "UNVERIFIED_IDEA_TEMPLATE", "estimated_value_vnd": None,
         "deliverable": "Python Scraper Script + Xuất Excel", "effort_minutes": None,
         "target_roles": ["DEV_SCRAPER_SPECIALIST", "DEV_EXCEL_CSV_WIZARD", "OPS_PROPOSAL_CRAFTER"]},
        {"id": "NICHE_TELEGRAM_NOTIFIER", "title": "Bot Telegram thông báo biến động giá / tin tức tự động",
         "evidence_status": "UNVERIFIED_IDEA_TEMPLATE", "estimated_value_vnd": None,
         "deliverable": "Python Bot Script", "effort_minutes": None,
         "target_roles": ["DEV_TELEGRAM_BOT_CRAFTER", "DEV_PYTHON_ENGINEER", "OPS_PROPOSAL_CRAFTER"]},
        {"id": "NICHE_CHROME_EXT_DATA_EXTRACTOR", "title": "Tiện ích Chrome trích xuất dữ liệu ra Excel",
         "evidence_status": "UNVERIFIED_IDEA_TEMPLATE", "estimated_value_vnd": None,
         "deliverable": "Chrome Extension (Manifest V3)", "effort_minutes": None,
         "target_roles": ["DEV_CHROME_EXT_BUILDER", "MKT_COPYWRITER", "OPS_DELIVERY_DISPATCHER"]},
        {"id": "NICHE_EXCEL_CLEANER_AUTOMATION", "title": "Script chuẩn hóa dữ liệu Excel",
         "evidence_status": "UNVERIFIED_IDEA_TEMPLATE", "estimated_value_vnd": None,
         "deliverable": "Python Automation Tool", "effort_minutes": None,
         "target_roles": ["DEV_EXCEL_CSV_WIZARD", "DEV_PYTHON_ENGINEER", "OPS_PROPOSAL_CRAFTER"]},
    ]

    @classmethod
    def get_seed_ideas(cls) -> List[Dict]:
        return [dict(item) for item in cls.SEED_IDEAS]

    @classmethod
    def get_validated_opportunities(cls) -> List[Dict]:
        """Compatibility alias; no item returned here is actually validated."""
        return cls.get_seed_ideas()

    @classmethod
    def parse_client_request(cls, raw_text: str) -> Dict:
        """Wrap supplied text without claiming research or model parsing."""
        return {"raw_text": raw_text, "suggested_price_vnd": None, "turnaround_hours": None,
                "free_stack_applicable": None, "status": "UNVERIFIED_INPUT_ONLY"}
