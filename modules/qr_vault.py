"""
VietQR & Offline Payment Generator
100% Zero-Cost: Runs locally via segno and standard VietQR specs.
Direct payout to Owner's bank account (0% intermediary fees).
"""
import segno
from pathlib import Path
from typing import Optional, Dict

class VietQRVault:
    """Generates standard VietQR images and payment links at zero cost."""

    # Common Vietnam Bank BIN codes (NAPAS)
    BANK_BINS = {
        "MB": "970422",
        "VCB": "970436",
        "TCB": "970407",
        "VPB": "970432",
        "ACB": "970416",
        "BIDV": "970418",
        "VIB": "970441",
        "TPB": "970458",
        "OCB": "970448",
        "SHB": "970443",
        "MSB": "970426",
    }

    @classmethod
    def generate_vietqr_url(cls, bank_id: str, account_no: str, account_name: str, amount: Optional[int] = None, memo: Optional[str] = None) -> str:
        """
        Creates standard VietQR quick link (publicly accessible, zero-cost).
        """
        bank_clean = bank_id.upper().strip()
        acc_clean = account_no.strip()
        url = f"https://img.vietqr.io/image/{bank_clean}-{acc_clean}-compact2.png"
        
        params = []
        if amount and amount > 0:
            params.append(f"amount={amount}")
        if memo:
            import urllib.parse
            params.append(f"addInfo={urllib.parse.quote(memo)}")
        if account_name:
            import urllib.parse
            params.append(f"accountName={urllib.parse.quote(account_name)}")
            
        if params:
            url += "?" + "&".join(params)
        return url

    @classmethod
    def generate_local_qr_png(cls, content: str, output_path: Path) -> Path:
        """
        Generates QR code locally using segno (zero internet, zero API cost).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        qr = segno.make_qr(content)
        qr.save(str(output_path), scale=5)
        return output_path
