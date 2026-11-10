"""Deterministic proposal skeleton for explicitly degraded, non-AI use."""
from typing import Dict


class ProposalCrafter:
    """Return a safe template without claiming work or results that do not exist."""

    @classmethod
    def craft_proposal(cls, client_need: str, price_vnd: int = 0, turnaround_hours: int = 0) -> Dict[str, str]:
        del price_vnd, turnaround_hours  # Unverified caller guesses are not proposal facts.
        short_pitch = (
            "[DEGRADED_MODE — TEMPLATE, CHƯA CÁ NHÂN HÓA BẰNG AI]\n"
            f"Yêu cầu khách hàng (chưa xác minh): {client_need[:300]}\n\n"
            "Tôi có thể đề xuất cách xử lý sau khi xác nhận phạm vi, dữ liệu đầu vào, "
            "tiêu chí nghiệm thu và khả năng thực hiện. Chưa có giá, tiến độ hay kết quả được xác minh."
        )
        delivery_message = (
            "[DEGRADED_MODE — TEMPLATE, CHỈ DÙNG SAU KHI THỰC SỰ HOÀN THÀNH]\n"
            f"Phạm vi dự án cần đối chiếu: {client_need[:300]}\n\n"
            "Chỉ gửi tin nhắn bàn giao sau khi owner xác nhận file, kiểm thử, giá và phương thức thanh toán."
        )
        return {"mode": "DEGRADED_MODE", "short_pitch": short_pitch,
                "delivery_message": delivery_message}
