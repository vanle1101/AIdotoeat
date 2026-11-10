# PHASE 10 — VPS canary và bằng chứng thực tế

**Kết luận phát hành production: NO-GO.** Canary riêng đã chạy được và các bài browser/E2E đạt yêu cầu, nhưng VPS production còn rủi ro bảo mật/vận hành chưa được xử lý. Không có thay đổi production, không merge PR, không bật worker, gửi bài, gọi API trả phí hay giao dịch tiền thật.

## Phạm vi và mã nguồn

- PR #1 vẫn mở; nhánh `codex/autoprofit-phase-09-production-readiness`.
- Mốc yêu cầu `7a214fd79ee4609a4663045eb5e29048abb400a`; trạng thái bắt đầu `8baa0217c164ca824e0dbb0ae2a9c9dcac891cf6`.
- Hai lỗi triển khai thật được sửa trên nhánh: log path systemd chưa tồn tại làm service thoát `209/STDOUT`; Uvicorn không thấy package `core`. Bản sửa dùng journald, giới hạn restart và đặt `PYTHONPATH` rõ ràng.
- CI của bản canary `08f0e32d3bc31c6617aed0347c0ee7cc4c388f7b` xanh ở hai job Ubuntu. Commit cuối cùng của báo cáo có CI riêng trong PR.
- Kiểm tra secret hiện tại không thấy giá trị nhận tiền đã biết trong `HEAD`, không thấy private-key/API-token theo các mẫu đã quét. Các giá trị nhận tiền từng xuất hiện trong lịch sử/base `origin/main` tại `1424d3355616`; việc xóa khỏi file hiện tại không xóa được Git history. Báo cáo không ghi lại các giá trị đó.

## Kiểm tra VPS production

| Hạng mục | Kết quả thực tế |
|---|---|
| Hệ điều hành/tài nguyên | Ubuntu 24.04, 6 vCPU, RAM 5.8 GiB (còn khoảng 2.2 GiB lúc kiểm tra), swap 4 GiB (đã dùng khoảng 3.3 GiB), SSD còn 35 GiB. |
| Port | SSH 22; HTTP 80, HTTPS 443, app 8888 và dịch vụ khác 8000 đang lắng nghe. 8451/8889 ban đầu trống và được dành riêng cho canary loopback. |
| HTTP production | `/` và `/api/health` trả 200; `/api/ready` trả 404. |
| HTTPS | Nginx có listener/certificate trên 443 cho các vhost hiện hữu; ứng dụng tại `:8888` là HTTP. TLS handshake vào `https://host:8888` thất bại. Không sửa vhost TLS dùng chung. `nginx -t` thành công nhưng in cảnh báo TLS option trùng từ các vhost hiện hữu. |
| Service và dữ liệu | `autoprofit-backend` và `autoprofit-traffic` đều đang chạy bằng `root`. Production SQLite là `root:root`, mode `0666`. Không tìm thấy backup phù hợp trong các thư mục VPS đã rà soát; chưa xác nhận backup offsite. |
| Traffic worker | Service traffic cũ vẫn active trên production. Code trong PR đã retire việc tạo traffic tự động, nhưng service đang chạy trên VPS chưa được dừng vì yêu cầu không thay đổi production. Đây là blocker nghiêm trọng. |
| Local LLM 0 đồng | Không có Ollama/llama.cpp runtime, model file hay GPU runtime được phát hiện. Vì vậy LLM trên host là **UNAVAILABLE**, không tự tải model. |

Các thư mục backup được rà soát là `/var/backups`, `/root/backups`, `/var/www/autoprofit/backups` và `/var/lib/autoprofit`; việc không thấy file ở đó không chứng minh không có bản sao ngoài host.

## Canary riêng

- Release: `08f0e32d3bc31c6617aed0347c0ee7cc4c388f7b`, cài dưới `/var/www/autoprofit-canary`; dữ liệu riêng trong `/var/lib/autoprofit-canary`.
- Chạy bằng user `autoprofit-canary`; API `127.0.0.1:8451`, Nginx độc lập `127.0.0.1:8889`. Không dùng/reload Nginx production.
- Worker `false`; engine và budget kill switch `true`; TEST mode `false`; payment, admin key, order secret, LLM key đều chưa cấu hình. Hai unit đang **disabled at boot** và listener chỉ ở loopback. Browser truy cập qua SSH tunnel.
- Canary DB mode `0600`, `quick_check=ok`, 46 bảng, migration version 13. Endpoint `/api/health` và `/api/ready` trả 200; admin chưa xác thực trả 503; payment catalog xác nhận `payment_configured=false`.
- Canary Nginx/systemd được kiểm chứng trực tiếp. Rollback thật từ release trước `8baa021` về `08f0e32` và khởi động readiness thành công ở cả hai chiều; không đổi production database.

## Browser và 3D

Chạy Playwright với Chrome hệ thống và Intel UHD Direct3D11, chặn mọi request khác origin. Kết quả: **44/44 browser assertions đạt** trên 1920×1080, 1440×900 và mobile 390×844; không có JavaScript page error hay tràn ngang. Hai HTTP 503 là các request đọc admin chưa cấu hình, đúng hành vi fail-closed.

Ở 1920×1080, đã kéo camera phải **90.07°**, tiếp tục **90.07°** tới mặt đối diện (tổng **179.86°**), zoom, chuyển đủ sáu preset, chọn trực tiếp Ad Network và workstation, reset toàn cảnh, dùng phím mũi tên chuyển camera tab. WebGL context khỏe.

Đo trên GPU Intel UHD: **61 FPS**, 264 draw calls, 239,456 triangles, 224 geometries và 10 textures. Đây là phép đo browser headless trên GPU workstation; không đại diện cho mọi GPU/máy khách. Lighthouse chưa chạy.

Ảnh và dữ liệu thô:

- [1920×1080 Dashboard](evidence/phase10/vps-canary-chrome-final-08f0e32/desktop-1920x1080-dashboard.png)
- [3D toàn cảnh](evidence/phase10/vps-canary-chrome-final-08f0e32/desktop-1920x1080-scene-panorama.png)
- [Camera sau lượt xoay 90°](evidence/phase10/vps-canary-chrome-final-08f0e32/desktop-1920x1080-scene-rotate-90.png)
- [Camera đối diện sau tổng 180°](evidence/phase10/vps-canary-chrome-final-08f0e32/desktop-1920x1080-scene-rotate-180.png)
- [Mobile 390×844](evidence/phase10/vps-canary-chrome-final-08f0e32/mobile-390x844-dashboard.png)
- [Browser JSON gồm console/network/API/FPS](evidence/phase10/vps-canary-chrome-final-08f0e32/browser-evidence.json)

Các preset AI Agents, Ad Network và Products cũng có screenshot riêng trong cùng thư mục. 8 request third-party bị chặn theo chính sách kiểm thử; không gửi traffic ra ngoài.

## Migration, E2E và bảo mật

- Bản sao SQLite production được migrate từ schema 0 lên 13, chạy lần hai idempotent, integrity `ok`, row count cũ được giữ; restore trả về **đường dẫn mới**, không ghi đè nguồn. [Bằng chứng migration](evidence/phase10/migration-copy.json).
- E2E cục bộ trên database tạm: ingest nguồn công khai, tạo/QA/package sản phẩm; false payment claim không tạo giao dịch; TEST delivery đúng một lần, test cash không vào revenue; crash/restart resume idempotent; provider unavailable/quota và kill switch fail-closed; backup/restore đạt; 0 network calls. [Bằng chứng E2E](evidence/phase10/local-e2e.json).
- Full test suite: **143 passed, 1 skipped, 70 subtests passed**. Bài skip là bài POSIX-only trên Windows; CI Ubuntu kiểm tra nhánh POSIX. PR CI cho release canary đã xanh.
- Local security regression tests bao gồm admin auth, cross-origin mutation, rate limits, SSRF, SQLi/XSS, path traversal, secret redaction, false claims, delivery authorization và kill switch. Trên canary, admin không cấu hình nên chỉ xác minh được từ chối ẩn danh; không cấu hình khóa để giả lập owner.
- Không gửi post/outreach, không chuyển khoản, không bật TEST checkout trên canary. Nginx canary chỉ loopback và browser không truy cập origin bên ngoài.

## GO / NO-GO

- **GO:** kiểm thử kỹ thuật canary loopback; health/readiness; migration trên bản sao; browser 3D; crash recovery/kill switch/E2E cục bộ; rollback canary.
- **NO-GO:** triển khai production hoặc bật automation. Cần xử lý worker legacy đang chạy, service production bằng root, SQLite mode `0666`, backup chưa xác minh, `/api/ready` thiếu, HTTPS chưa áp dụng cho app `:8888`, và lịch sử Git còn thông tin nhận tiền. Cần chủ sở hữu phê duyệt riêng mọi thay đổi production.
- **Chưa xác minh:** xác thực owner HTTPS qua hostname canary, HTTPS canary công khai, hiệu năng GPU trên VPS, backup offsite, local LLM, và phục hồi production từ bản backup có kiểm chứng.

## Thử nghiệm kiếm khách đầu tiên — không quảng cáo/spam

Ưu tiên gói dọn CSV/Excel, nhưng tín hiệu từ nguồn công khai chưa chứng minh có khách trả tiền. Chuẩn bị demo offline bằng dữ liệu tổng hợp, ghi rõ dữ liệu giả và cho tải CSV sạch kèm mapping/dedupe report. Trong tuần đầu, hỏi tối đa 5 chủ shop/người quen đã đồng ý trao đổi về một file lặp lại tốn thời gian; không lấy danh sách email, không gửi hàng loạt. Nếu một người tự nguyện chia sẻ file đã ẩn danh, làm một mẫu nhỏ miễn phí và đưa báo giá cố định cho phần tùy chỉnh sau khi họ duyệt phạm vi. Theo dõi thủ công: cuộc trò chuyện có đồng ý, workflow lặp lại được xác nhận, yêu cầu báo giá, pilot trả phí. Nếu sau 5 cuộc trò chuyện được cho phép không ai có pain lặp lại hoặc hỏi báo giá, dừng và đổi phân khúc. Ngân sách: **0 VND**, không mua quảng cáo, API hay dịch vụ.
