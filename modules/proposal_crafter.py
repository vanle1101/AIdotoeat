"""
High-Converting Proposal & Outreach Generator
Zero-Cost: Transforms raw project requirements into immediate client proposals
ready for Upwork, Facebook groups, or Direct Messages.
"""
from typing import Dict, Any

class ProposalCrafter:
    """Generates irresistible proposals and pitch decks for fast client closing."""

    @classmethod
    def craft_proposal(cls, client_need: str, price_vnd: int = 500_000, turnaround_hours: int = 2) -> Dict[str, str]:
        """
        Builds a customized proposal designed to win the job in under 60 seconds.
        """
        short_pitch = (
            f"Chào bạn, mình đã đọc kỹ yêu cầu '{client_need[:60]}...'.\n\n"
            f"Hiện tại mình đã có sẵn giải pháp và script chạy chuẩn cho task này, "
            f"có thể bàn giao file chạy ngay trong vòng {turnaround_hours} giờ.\n"
            f"- Đảm bảo: Xuất file Excel chuẩn UTF-8 (không lỗi font tiếng Việt).\n"
            f"- Chi phí trọn gói: {price_vnd:,.0f} VND (bàn giao test ưng ý mới thanh toán qua STK/VietQR).\n"
            f"- Kèm file hướng dẫn chi tiết cách chạy 1-click.\n\n"
            f"Bạn check tin nhắn chờ mình gửi demo kết quả thử nghiệm nhé!"
        )

        delivery_message = (
            f"Chào bạn, mình đã hoàn thành xong công việc '{client_need[:50]}'.\n\n"
            f"1. Toàn bộ file source code + kết quả đã được đóng gói trong file đính kèm.\n"
            f"2. File hướng dẫn từng bước (HDSD.txt) đã có sẵn bên trong.\n\n"
            f"Bạn kiểm tra kết quả nhé. Nếu mọi thứ đúng ý, bạn có thể quét mã VietQR "
            f"hoặc chuyển khoản vào STK bên dưới giúp mình:\n"
            f"Số tiền: {price_vnd:,.0f} VND\n"
            f"Nội dung: Thanh toan du an\n\n"
            f"Cảm ơn bạn và hy vọng có cơ hội hợp tác lâu dài!"
        )

        return {
            "short_pitch": short_pitch,
            "delivery_message": delivery_message
        }
