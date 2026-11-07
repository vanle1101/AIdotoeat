# 🚀 AUTOPROFIT AI ENTERPRISE — HỆ THỐNG AI TỰ ĐỘNG HÓA KIẾM TIỀN 24/7

> Hệ sinh thái Full-Stack kết hợp **FastAPI + SQLite WAL + 3D Virtual AI Workforce (Three.js) + GitHub Web Factory + Hệ thống Quảng Cáo A-Ads & Monetag + VietQR Napas247 & Binance USDT**.

---

## 🌐 1. ĐỊA CHỈ TRUY CẬP TRỰC TIẾP (LIVE PRODUCTION)

Hệ thống đã được triển khai hoàn tất và đang chạy ngầm 24/7 trên máy chủ VPS:

* 🔗 **Link Web Trực Tiếp (Domain tạm thời sslip.io):** [http://160.22.107.108.sslip.io:8888](http://160.22.107.108.sslip.io:8888)
* 🔗 **Link Truy Cập Theo IP VPS:** [http://160.22.107.108:8888](http://160.22.107.108:8888)
* 🔄 **Trang Auto-Surf 10x View & Cày Tiền Quảng Cáo:** [http://160.22.107.108:8888/autosurf.html](http://160.22.107.108:8888/autosurf.html)
* ⚡ **API Health Check:** [http://160.22.107.108:8888/api/health](http://160.22.107.108:8888/api/health)

---

## 🛠️ 2. DANH MỤC WEB APP THƯƠNG MẠI SẴN CÓ (GITHUB WEB FACTORY)

Các công cụ đã được đóng gói thành file HTML độc lập, có sẵn khung quảng cáo **A-Ads**, nút mua mã nguồn **VietQR** và **USDT**:

1. [JSON Schema & Data Formatter Pro](http://160.22.107.108:8888/apps/json-schema-seo-studio.html)
2. [Social Meta & OpenGraph Studio](http://160.22.107.108:8888/apps/seo-opengraph-meta-generator.html)
3. [VietQR & Multi-Chain Payment Gateway](http://160.22.107.108:8888/apps/vietqr-crypto-payment-generator.html)
4. [AI LLM Token & Cost Calculator](http://160.22.107.108:8888/apps/openai-tiktoken-cost-estimator.html)
5. [Crypto CEX/DEX Arbitrage Spread Scanner](http://160.22.107.108:8888/apps/crypto-arbitrage-spread-scanner.html)
6. [DeFi APY & Staking Yield Compounder](http://160.22.107.108:8888/apps/defi-staking-yield-compounder.html)
7. [Password Entropy & Hash Security Auditor](http://160.22.107.108:8888/apps/password-hash-security-auditor.html)
8. [Smart CSV to JSON & Data Cleaner](http://160.22.107.108:8888/apps/papaparse-csv-to-json-cleaner.html)
9. [Modern CSS Glassmorphism Studio](http://160.22.107.108:8888/apps/css-glassmorphism-card-builder.html)
10. [Web3 Airdrop & Testnet Quest Tracker](http://160.22.107.108:8888/apps/web3-airdrop-testnet-quest-tracker.html)
11. [Markdown to HTML & Prompt Studio](http://160.22.107.108:8888/apps/ai-prompt-markdown-converter.html)
12. [SaaS ROI & Pomodoro Calculator](http://160.22.107.108:8888/apps/saas-roi-pomodoro-calculator.html)

---

## ⚙️ 3. CẤU TRÚC HỆ THỐNG TRÊN VPS (160.22.107.108)

* **Thư mục dự án:** `/var/www/autoprofit/`
  * `backend/`: Mã nguồn FastAPI điều hành và quản trị dữ liệu.
  * `frontend/`: Toàn bộ giao diện 3D, CSS, JS, hình ảnh và thư mục `apps/`.
  * `venv/`: Môi trường ảo Python 3.12 chứa đầy đủ thư viện.
* **Dịch vụ chạy nền (Systemd Daemon):**
  * Tên dịch vụ: `autoprofit-backend.service` (Cổng nội bộ `127.0.0.1:8450`, tự khởi động lại khi crash hoặc reboot).
  * Web Server: **Nginx** reverse proxy lắng nghe trên cổng public `8888`.

---

## 🔑 4. HƯỚNG DẪN GẮN DOMAIN CHÍNH THỨC CỦA BẠN (SAU NÀY)

Khi bạn muốn trỏ tên miền riêng (ví dụ: `kiemtien.vorte.me` hoặc `yourdomain.com`):

1. **Trỏ DNS:** Vào quản lý tên miền (Cloudflare/Namecheap), tạo bản ghi `A` trỏ tên miền về `160.22.107.108`.
2. **Cập nhật Nginx:** Thêm `server_name yourdomain.com;` vào `/etc/nginx/sites-available/autoprofit.conf` và cấp SSL:
   ```bash
   certbot --nginx -d yourdomain.com
   ```
