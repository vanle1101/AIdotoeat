"""
Zero-Cost Corp Management Console
Interactive CLI & Dashboard for the Human Owner
"""
import sys
import os
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

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from core.config import POLICY, OUTPUTS_DIR
from core.roles import list_all_roles
from core.db import get_connection
from core.orchestrator import ZeroCostOrchestrator
from modules.qr_vault import VietQRVault
from modules.product_builder import ProductBuilder
from modules.proposal_crafter import ProposalCrafter

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
    console.print("\n[bold yellow]>>> ĐANG KHỞI ĐỘNG CHU TRÌNH TẠO SẢN PHẨM & TÌM DOANH THU (0 VND)...[/bold yellow]")
    
    bank_code = Prompt.ask("Nhập mã ngân hàng của bạn (ví dụ: MB, VCB, TCB, ACB, VPB)", default="MB")
    acc_no = Prompt.ask("Nhập số tài khoản ngân hàng của bạn", default="0000000000")
    acc_name = Prompt.ask("Nhập tên chủ tài khoản (không dấu)", default="CHU TAI KHOAN")

    orchestrator = ZeroCostOrchestrator()
    result = orchestrator.run_zero_cost_venture(
        bank_code=bank_code,
        account_no=acc_no,
        account_name=acc_name
    )

    console.print(Panel(
        f"[bold green]ĐÃ HOÀN THÀNH CHU TRÌNH VỚI CHI PHÍ: 0 VND![/bold green]\n\n"
        f"1. Sản phẩm số 1: Chrome Data Exporter Extension -> [cyan]{result['deliverable_paths']['chrome_extension']}[/cyan]\n"
        f"2. Sản phẩm số 2: E-Commerce Python Scraper -> [cyan]{result['deliverable_paths']['python_scraper']}[/cyan]\n"
        f"3. Mã VietQR thanh toán -> [cyan]{result['deliverable_paths']['vietqr_image']}[/cyan]\n"
        f"4. Link QR thanh toán trực tiếp: [link]{result['vietqr_payment_url']}[/link]\n\n"
        f"[bold yellow]Kịch bản chào hàng dành cho Owner:[/bold yellow]\n"
        f"{result['proposals']['short_pitch']}",
        title="KẾT QUẢ TRIỂN KHAI"
    ))

def solve_custom_gig():
    console.print("\n[bold cyan]>>> GIẢI QUYẾT KÈO FREELANCE / YÊU CẦU TỪ KHÁCH HÀNG (0 VND)[/bold cyan]")
    client_request = Prompt.ask("Dán mô tả yêu cầu của khách hàng vào đây")
    price = Prompt.ask("Mức giá bạn muốn báo khách (VND)", default="500000")
    
    proposals = ProposalCrafter.craft_proposal(client_request, int(price))
    console.print(Panel(
        f"[bold green]Kịch bản gửi báo giá nhanh:[/bold green]\n\n{proposals['short_pitch']}\n\n"
        f"[bold blue]Kịch bản bàn giao & gửi STK sau khi xong việc:[/bold blue]\n\n{proposals['delivery_message']}",
        title="KỊCH BẢN CHỐT ĐƠN 60 GIÂY"
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
        console.print("[bold yellow]>>> CHẾ ĐỘ TỰ ĐỘNG KHỞI CHẠY (ZERO-TOUCH OWNER MODE)...[/bold yellow]")
        orchestrator = ZeroCostOrchestrator()
        result = orchestrator.run_zero_cost_venture(
            bank_code="MB",
            account_no="0000000000",
            account_name="CHU TAI KHOAN"
        )
        console.print(Panel(
            f"[bold green]ĐÃ TỰ ĐỘNG HOÀN THÀNH CHU TRÌNH VỚI CHI PHÍ: 0 VND![/bold green]\n\n"
            f"1. Chrome Data Exporter Extension: [cyan]{result['deliverable_paths']['chrome_extension']}[/cyan]\n"
            f"2. E-Commerce Python Scraper: [cyan]{result['deliverable_paths']['python_scraper']}[/cyan]\n"
            f"3. Mã VietQR: [cyan]{result['deliverable_paths']['vietqr_image']}[/cyan]\n\n"
            f"[bold yellow]Kịch bản chào hàng sẵn sàng giao:[/bold yellow]\n"
            f"{result['proposals']['short_pitch']}",
            title="KẾT QUẢ KHỞI CHẠY TỰ ĐỘNG"
        ))
        view_deliverables()
    else:
        main_menu()
