# ĐỀ TÀI: THU THẬP VÀ QUẢN LÍ DỮ LIỆU CÁC CÁNH TAY ROBOT CÔNG NGHIỆP CỦA HỆ THỐNG PHÂN LOẠI SẢN PHẨM TRONG NHÀ KHO TỰ ĐỘNG

> **Môn học:** Hệ Thống Thông Tin  
> **Nền tảng:** Python · SQLite · Streamlit · Plotly · Seaborn · Matplotlib

---

## 📌 1. Giới thiệu tổng quan
Dự án xây dựng hệ thống phần mềm hoàn chỉnh nhằm:
1. **Thu thập dữ liệu thời gian thực (Real-time Data Collection):** Giả lập và thu thập dữ liệu góc quay 6 khớp nối ($J_1 \rightarrow J_6$), cảm biến khoảng cách/vị trí (LiDAR, Encoder, Siêu âm), nhiệt độ động cơ và kết quả phân loại sản phẩm theo chu kỳ 1 giây.
2. **Quản lý dữ liệu quan hệ (Relational Database Management):** Thiết kế CSDL SQLite chuẩn hóa 8 bảng có ràng buộc toàn vẹn khóa ngoại (`FOREIGN KEY = ON`) và miền giá trị (`CHECK constraint`).
3. **Giám sát và Phân tích (Web Dashboard):** Cung cấp giao diện trực quan hóa dữ liệu qua biểu đồ tương tác, Heatmap phân bố góc khớp, bảng truy vấn dữ liệu gốc, và chức năng xuất báo cáo CSV.
4. **Quản trị vận hành (CRUD & Alert Management):** Cho phép người vận hành đổi trạng thái robot (`Hoạt động`, `Cảnh báo`, `Bảo trì`), cập nhật tiến độ xử lý sự cố cảnh báo và thêm mới mã hàng hóa trực tiếp trên Web.

---

## 📁 2. Cấu trúc thư mục dự án

```text
robotcontrol-main/
│
├── README.md                          # Tài liệu hướng dẫn dự án
│
├── Robot_Warehouse/                   # [PHIÊN BẢN CHÍNH NÂNG CAO]
│   ├── app.py                         # Web Dashboard chính (Streamlit + CRUD + Heatmap)
│   ├── realtime_page.py               # Giao diện giám sát Real-time tự động làm mới mỗi giây
│   ├── mo_phong_du_lieu.py            # Bộ sinh dữ liệu góc khớp & cảm biến thời gian thực
│   ├── tao_du_lieu_mau.py             # Script nạp dữ liệu mẫu ban đầu (Seed data)
│   ├── nhap_du_lieu.py                # Script kiểm tra kết nối & danh sách bảng CSDL
│   ├── schema_warehouse.sql           # File DDL định nghĩa toàn bộ 8 bảng CSDL chuẩn
│   ├── warehouse_robot.db             # File CSDL SQLite thực tế
│   └── requirements.txt               # Danh sách thư viện phụ thuộc
│
└── robot-sorting-warehouse-main/      # [PHIÊN BẢN NGHIỆP VỤ PHÂN LOẠI SẢN PHẨM]
    └── robot-sorting-warehouse-main/
        ├── app.py                     # Dashboard phân loại theo chủng loại hàng & barcode
        ├── simulator.py               # Giả lập gắp hàng, nhiệt độ khớp nối & tỷ lệ rơi hàng
        ├── schema_robot.sql           # File DDL định nghĩa CSDL phân loại 4 bảng
        ├── init_db.py                 # Khởi tạo CSDL từ file sql
        ├── hien_thi_bieu_do.py        # Mở popup biểu đồ Matplotlib/Seaborn độc lập
        └── xem_ket_qua.py             # In kết quả truy vấn nhanh trên Terminal
```

---

## 🛠️ 3. Cài đặt môi trường

Mở Terminal tại thư mục dự án và cài đặt các thư viện cần thiết:

```powershell
pip install -r Robot_Warehouse/requirements.txt
```

*(Các thư viện chính: `streamlit`, `pandas`, `plotly`, `matplotlib`, `seaborn`, `streamlit-autorefresh`)*

---

## 🚀 4. Hướng dẫn khởi chạy hệ thống

### Bước 1: Khởi động bộ giả lập thu thập dữ liệu (Simulator)
Mở một cửa sổ Terminal và chạy:

```powershell
cd Robot_Warehouse
python mo_phong_du_lieu.py
```
*(Chương trình sẽ tự động đo đạc và ghi nhận dữ liệu 6 khớp và các cảm biến mỗi giây vào CSDL SQLite)*

---

### Bước 2: Khởi động Web Dashboard quản lý & giám sát
Mở một cửa sổ Terminal thứ hai và chạy:

```powershell
cd Robot_Warehouse
streamlit run app.py
```

Truy cập trình duyệt tại địa chỉ: **`http://localhost:8501`**

Trên giao diện bạn có thể:
- **Menu bên trái:** Chuyển đổi giữa `📊 Quản lý dữ liệu` và `📡 Giám sát Real-time`.
- **Tab Quản lý & Cập nhật:** Thay đổi trạng thái vận hành của robot, đánh dấu đã xử lý cảnh báo sự cố, hoặc thêm mã hàng mới vào nhà kho.
- **Tab Biểu đồ & Dữ liệu:** Theo dõi biến thiên cảm biến, Heatmap góc khớp $J_1 \rightarrow J_6$, lọc tìm kiếm và tải file `.csv`.

---

## 🗄️ 5. Thiết kế Cơ sở dữ liệu (8 Bảng)

| Tên Bảng | Ý nghĩa nghiệp vụ |
| :--- | :--- |
| **`ThietBiRobot`** | Lưu thông tin các cánh tay robot (Tên, model, vị trí khu vực, trạng thái hoạt động). |
| **`ThongSoKyThuat`** | Thông số cơ khí: bậc tự do (6 DOF), tải trọng tối đa, tầm với, độ chính xác lặp lại. |
| **`MaHang`** | Danh mục sản phẩm phân loại: mã hàng, khối lượng chuẩn, kích thước dài/rộng/cao. |
| **`NhatKyHoatDong`** | Nhật ký các chu kỳ gắp, phân loại, kiểm tra kiện hàng kèm thời gian xử lý và kết quả. |
| **`NhatKyGocKhop`** | Thu thập góc quay của 6 khớp nối ($J_1 \rightarrow J_6$) liên tục phục vụ phân tích động học. |
| **`CamBien`** | Danh mục các cảm biến gắn trên cánh tay (LiDAR đo khoảng cách, Encoder đo góc, Siêu âm). |
| **`NhatKyCamBien`** | Dữ liệu đo đạc liên tục từ cảm biến để phát hiện vật cản hoặc sai lệch vị trí. |
| **`NhatKyCanhBao`** | Ghi nhận sự cố bất thường (quá nhiệt, kẹt cơ cấu kẹp, lệch tọa độ) và trạng thái xử lý. |

---

## 🏆 6. Điểm nổi bật môn Hệ Thống Thông Tin
- **Toàn vẹn dữ liệu:** Ràng buộc chặt chẽ bằng `FOREIGN KEY`, `ON DELETE CASCADE`, và các điều kiện `CHECK`.
- **Tốc độ truy vấn:** Đã đánh chỉ mục (`INDEX`) trên các trường thời gian và ID giúp hiển thị Real-time không bị giật lag.
- **Tính thực tế:** Kết hợp mô hình IoT / SCADA giám sát thời gian thực với chức năng quản trị cơ sở dữ liệu chuyên nghiệp.
