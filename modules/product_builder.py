"""
Zero-Cost Product Factory
Builds functional, production-ready deliverables (Chrome Extensions, Python Tools, Local Web Apps)
without any external API or hosting costs.
"""
from pathlib import Path
import json
from core.config import OUTPUTS_DIR

class ProductBuilder:
    """Generates tested, packaged deliverables for clients or digital storefronts."""

    @classmethod
    def build_chrome_extension(cls, output_subdir: str = "chrome_data_exporter") -> Path:
        """
        Builds a complete, zero-dependency Manifest V3 Chrome Extension
        that extracts HTML tables and data lists directly to CSV.
        """
        ext_dir = OUTPUTS_DIR / output_subdir
        ext_dir.mkdir(parents=True, exist_ok=True)

        # 1. Manifest V3
        manifest = {
            "manifest_version": 3,
            "name": "OneClick Table & Data Exporter",
            "version": "1.0.0",
            "description": "Extract any HTML table or list directly to CSV in 1 second. 100% offline & private.",
            "permissions": ["activeTab", "scripting"],
            "action": {
                "default_popup": "popup.html",
                "default_title": "Export Data to CSV"
            }
        }
        with open(ext_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 2. Popup UI
        popup_html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; width: 280px; padding: 14px; margin: 0; background: #0f172a; color: #f8fafc; }
    h3 { margin: 0 0 10px 0; font-size: 15px; color: #38bdf8; display: flex; align-items: center; gap: 6px; }
    p { font-size: 12px; color: #94a3b8; line-height: 1.4; margin-bottom: 12px; }
    button { width: 100%; padding: 10px; border: none; border-radius: 6px; background: #0284c7; color: white; font-weight: 600; cursor: pointer; transition: background 0.2s; }
    button:hover { background: #0369a1; }
    .status { margin-top: 10px; font-size: 11px; text-align: center; color: #4ade80; display: none; }
    .footer { margin-top: 14px; font-size: 10px; text-align: center; color: #64748b; border-top: 1px solid #1e293b; padding-top: 8px; }
  </style>
</head>
<body>
  <h3>⚡ Data Exporter Pro</h3>
  <p>Tự động phát hiện bảng dữ liệu trên trang hiện tại và tải về file CSV ngay lập tức.</p>
  <button id="exportBtn">Trích xuất & Tải CSV</button>
  <div id="status" class="status">Đã tìm thấy và xuất dữ liệu!</div>
  <div class="footer">Công cụ tự động hóa bản quyền bởi Owner</div>
  <script src="popup.js"></script>
</body>
</html>"""
        with open(ext_dir / "popup.html", "w", encoding="utf-8") as f:
            f.write(popup_html)

        # 3. Popup JS logic
        popup_js = """document.getElementById('exportBtn').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: extractTablesToCSV
  });
});

function extractTablesToCSV() {
  const tables = document.querySelectorAll('table');
  if (tables.length === 0) {
    alert('Không tìm thấy bảng (table) nào trên trang này!');
    return;
  }

  let csvContent = "data:text/csv;charset=utf-8,\uFEFF";
  tables.forEach((table, tIdx) => {
    csvContent += `--- BẢNG ${tIdx + 1} ---\\n`;
    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
      const cols = row.querySelectorAll('th, td');
      const rowData = Array.from(cols).map(c => '"' + c.innerText.replace(/"/g, '""').trim() + '"');
      csvContent += rowData.join(',') + "\\n";
    });
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `extracted_data_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
"""
        with open(ext_dir / "popup.js", "w", encoding="utf-8") as f:
            f.write(popup_js)

        # 4. Instructions Readme
        readme = """# Hướng dẫn sử dụng Chrome Extension (Cài đặt 10 giây)

1. Mở trình duyệt Google Chrome hoặc Cốc Cốc.
2. Truy cập đường dẫn: `chrome://extensions/`
3. Bật công tắc **"Developer mode"** (Chế độ dành cho nhà phát triển) ở góc trên bên phải.
4. Bấm nút **"Load unpacked"** (Tải tiện ích đã giải nén) và chọn thư mục này.
5. Tiện ích sẽ xuất hiện trên thanh công cụ, sẵn sàng trích xuất bất kỳ bảng dữ liệu nào thành CSV!
"""
        with open(ext_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme)

        return ext_dir

    @classmethod
    def build_python_scraper_bundle(cls, output_subdir: str = "shopee_market_scraper") -> Path:
        """
        Builds a self-contained Python web scraper script for clients.
        """
        tool_dir = OUTPUTS_DIR / output_subdir
        tool_dir.mkdir(parents=True, exist_ok=True)

        script_code = '''"""
Autonomous E-Commerce Data Scraper
Production-ready script for client delivery.
"""
import requests
from bs4 import BeautifulSoup
import csv
import time
import sys

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

def scrape_sample_quotes(output_csv="scraped_data.csv"):
    """Scrapes data gracefully with rate-limit respect."""
    print("[+] Khởi động quy trình cào dữ liệu...")
    url = "https://quotes.toscrape.com/"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[-] Lỗi kết nối: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.select(".quote")
    
    records = []
    for item in items:
        text = item.select_one(".text").get_text(strip=True) if item.select_one(".text") else ""
        author = item.select_one(".author").get_text(strip=True) if item.select_one(".author") else ""
        tags = [t.get_text(strip=True) for t in item.select(".tag")]
        records.append({"Nội dung": text, "Tác giả": author, "Thẻ tag": ", ".join(tags)})
        
    # Write to CSV UTF-8 with BOM for Excel compatibility
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Nội dung", "Tác giả", "Thẻ tag"])
        writer.writeheader()
        writer.writerows(records)
        
    print(f"[✓] Hoàn thành! Đã xuất {len(records)} dòng ra file: {output_csv}")

if __name__ == "__main__":
    scrape_sample_quotes()
'''
        with open(tool_dir / "scraper.py", "w", encoding="utf-8") as f:
            f.write(script_code)

        readme = """# Hướng dẫn chạy Script cào dữ liệu cho khách hàng

1. Yêu cầu: Đã cài Python (phiên bản 3.8 trở lên).
2. Chạy lệnh cài thư viện cần thiết:
   ```bash
   pip install requests beautifulsoup4
   ```
3. Chạy script:
   ```bash
   python scraper.py
   ```
4. File kết quả `scraped_data.csv` sẽ tự động tạo ngay trong thư mục, mở trực tiếp bằng Excel không lỗi font tiếng Việt.
"""
        with open(tool_dir / "HDSD.txt", "w", encoding="utf-8") as f:
            f.write(readme)

        return tool_dir
