"""
Zero-Cost Corp Management Console
Interactive CLI & Dashboard for the Human Owner
"""
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from core.config import OUTPUTS_DIR
from core.roles import list_all_roles
from core.db import get_connection
from core.orchestrator import ZeroCostOrchestrator
from core.llm import LLMError

console = Console()

def display_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║       ZERO-COST CORP ENGINE — 50 LOGICAL AGENTS              ║
    ║   Hard Budget Cap: 0 VND | Paid APIs: 0 | Hidden Fees: 0     ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(f"[bold cyan]{banner}[/bold cyan]")

def view_roles():
    roles = list_all_roles()
    table = Table(title=f"Danh sách 50 Vai trò Logic (Chi phí kích hoạt: 0 VND)")
    table.add_column("Mã Vai Trò", style="cyan", no_wrap=True)
    table.add_column("Tên Vai Trò", style="white")
    table.add_column("Phòng Ban", style="magenta")
    table.add_column("Nhiệm Vụ Cốt Lõi", style="green")

    for r in roles:
        table.add_row(r.role_id, r.name, r.department, r.mission)

    console.print(table)

def view_deliverables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, deliverable_type, estimated_market_value_vnd, owner_status, created_at FROM deliverables ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    table = Table(title="Kho Sản Phẩm & Deliverable Sẵn Sàng Kiếm Tiền")
    table.add_column("ID", style="cyan")
    table.add_column("Tên Sản Phẩm", style="bold white")
    table.add_column("Loại", style="magenta")
    table.add_column("Giá Đề Xuất (VND)", style="green")
    table.add_column("Trạng Thái Owner", style="yellow")
    table.add_column("Thời Gian Tạo", style="dim")

    for r in rows:
        table.add_row(str(r["id"]), r["name"], r["deliverable_type"], f"{r['estimated_market_value_vnd']:,.0f}", r["owner_status"], str(r["created_at"]))

    console.print(table)
    console.print(f"[bold green]Thư mục chứa file đóng gói:[/bold green] {OUTPUTS_DIR}")

def run_opportunity_cycle():
    console.print("\n[bold yellow]>>> PHÂN LOẠI NGUỒN NHU CẦU DO OWNER CUNG CẤP[/bold yellow]")
    source_text = Prompt.ask("Dán nội dung nguồn thật (bài đăng, phỏng vấn hoặc dữ liệu đã thu thập)")
    orchestrator = ZeroCostOrchestrator()
    result = orchestrator.run_zero_cost_venture(
        source_text=source_text,
        source_id="owner_provided_source",
    )
    if result["status"] != "ANALYSIS_ONLY":
        console.print(Panel(f"{result['status']}: {result['message']}", title="CHƯA CÓ KẾT QUẢ AI"))
        return
    analysis = result["analysis"]
    confidence = analysis.get("confidence_estimate")
    confidence_text = (f"{confidence:.2f} (ước lượng chưa hiệu chuẩn)" if confidence is not None
                       else "không có (DEGRADED_MODE hoặc model không báo estimate)")
    console.print(Panel(
        f"Niche được phân loại: {analysis['niche']}\n\n"
        f"Lý do: {analysis['rationale']}\n"
        f"Confidence: {confidence_text}\n"
        f"Provider/model: {result['provenance']['provider']} / {result['provenance']['model']}\n"
        f"Bước tiếp: Owner xác minh bằng chứng. Chưa tạo giá, doanh thu hay sản phẩm.",
        title="PHÂN TÍCH NGUỒN — CẦN OWNER DUYỆT"
    ))

def solve_custom_gig():
    console.print("\n[bold cyan]>>> SOẠN NHÁP CÁ NHÂN HÓA QUA MODEL ĐÃ KIỂM TRA[/bold cyan]")
    client_request = Prompt.ask("Dán mô tả yêu cầu của khách hàng vào đây")
    facts_raw = Prompt.ask("Nhập dữ kiện đã xác minh, phân cách bằng dấu | (để trống nếu chưa có)", default="")
    verified_facts = [fact.strip() for fact in facts_raw.split("|") if fact.strip()]
    try:
        result = ZeroCostOrchestrator().personalize_proposal(client_request, verified_facts)
    except LLMError as exc:
        console.print(Panel(
            f"Chưa tạo bản nháp AI. reason_code: {exc.code}\n"
            "Không dùng template tĩnh để giả làm model. Kiểm tra `python -m core.llm doctor`.",
            title="PROVIDER CHƯA SẴN SÀNG",
        ))
        return
    proposals = result["output"]
    console.print(Panel(
        f"{proposals['subject']}\n\n{proposals['proposal']}\n\n"
        f"Dữ kiện được gắn nhãn đã xác minh: {', '.join(proposals['grounded_facts']) or 'không có'}\n"
        f"Điểm cần xác nhận: {', '.join(proposals['unknowns']) or 'không có'}\n\n"
        f"Provider/model: {result['provenance']['provider']} / {result['provenance']['model']}\n"
        "Đây là bản nháp; kiểm tra thủ công trước khi gửi.",
        title="DRAFT — OWNER REVIEW"
    ))

def main_menu():
    display_banner()
    while True:
        console.print("\n[bold]DANH MỤC ĐIỀU HÀNH DÀNH CHO OWNER:[/bold]")
        console.print("1. Chạy chu trình tạo sản phẩm số & kịch bản kiếm tiền (0 VND)")
        console.print("2. Soạn kịch bản chốt kèo Freelance từ Facebook / Upwork")
        console.print("3. Xem danh mục sản phẩm (Deliverables) đã đóng gói")
        console.print("4. Xem danh sách 50 Vai trò Nhân sự Logic")
        console.print("5. Thoát")

        choice = Prompt.ask("Chọn thao tác [1-5]", default="1")
        if choice == "1":
            run_opportunity_cycle()
        elif choice == "2":
            solve_custom_gig()
        elif choice == "3":
            view_deliverables()
        elif choice == "4":
            view_roles()
        elif choice == "5":
            console.print("[green]Tạm dừng hệ thống. Không có tiến trình chạy ngầm.[/green]")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        display_banner()
        console.print("[bold yellow]Không tự chạy nghiên cứu hay tạo doanh thu bằng dữ liệu mẫu.[/bold yellow]")
        console.print("Dùng menu owner để cung cấp nguồn thật, hoặc chạy `python -m core.llm doctor` để kiểm tra provider.")
    else:
        main_menu()
