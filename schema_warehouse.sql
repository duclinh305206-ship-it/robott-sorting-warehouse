-- ==============================================================================
-- CƠ SỞ DỮ LIỆU: THU THẬP VÀ QUẢN LÝ DỮ LIỆU CÁNH TAY ROBOT CÔNG NGHIỆP
-- Hệ thống phân loại sản phẩm trong nhà kho tự động
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- 1. Bảng Thiết bị Robot
CREATE TABLE IF NOT EXISTS ThietBiRobot (
    RobotID INTEGER PRIMARY KEY AUTOINCREMENT,
    TenRobot TEXT NOT NULL UNIQUE,
    LoaiRobot TEXT NOT NULL,
    HangSanXuat TEXT NOT NULL,
    ModelRobot TEXT NOT NULL,
    ViTriLapDat TEXT NOT NULL,
    NgayLapDat TEXT NOT NULL,
    TrangThaiHoatDong TEXT NOT NULL CHECK(TrangThaiHoatDong IN ('Hoat dong', 'Canh bao', 'Bao tri', 'Ngung hoat dong')),
    GhiChu TEXT
);

-- 2. Bảng Thông số kỹ thuật cánh tay robot
CREATE TABLE IF NOT EXISTS ThongSoKyThuat (
    ThongSo_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    RobotID INTEGER NOT NULL UNIQUE,
    SoBacTuDo INTEGER NOT NULL DEFAULT 6,
    SoLuongKhop INTEGER NOT NULL DEFAULT 6,
    TaiTrongToiDa REAL NOT NULL,
    TamVoiToiDa REAL NOT NULL,
    DoChinhXacLapLai REAL,
    TocDoToiDa REAL,
    BoDieuKhien TEXT,
    GiaoThucKetNoi TEXT,
    NgayCapNhat TEXT NOT NULL,
    GhiChu TEXT,
    FOREIGN KEY (RobotID) REFERENCES ThietBiRobot(RobotID) ON DELETE CASCADE
);

-- 3. Bảng Danh mục mã hàng / Sản phẩm phân loại
CREATE TABLE IF NOT EXISTS MaHang (
    MaHangID INTEGER PRIMARY KEY AUTOINCREMENT,
    MaHang TEXT NOT NULL UNIQUE,
    TenSanPham TEXT NOT NULL,
    LoaiSanPham TEXT NOT NULL,
    KhoiLuong REAL,
    ChieuDai REAL,
    ChieuRong REAL,
    ChieuCao REAL,
    GhiChu TEXT
);

-- 4. Bảng Nhật ký hoạt động phân loại & thao tác
CREATE TABLE IF NOT EXISTS NhatKyHoatDong (
    HoatDongID INTEGER PRIMARY KEY AUTOINCREMENT,
    RobotID INTEGER NOT NULL,
    MaHangID INTEGER,
    ThoiGianBatDau TEXT NOT NULL,
    ThoiGianKetThuc TEXT,
    LoaiThaoTac TEXT NOT NULL,
    KetQua TEXT CHECK(KetQua IN ('Thanh cong', 'That bai', 'Dang xu ly', 'Huy')),
    ThoiGianXuLy REAL,
    GhiChu TEXT,
    FOREIGN KEY (RobotID) REFERENCES ThietBiRobot(RobotID),
    FOREIGN KEY (MaHangID) REFERENCES MaHang(MaHangID)
);

-- 5. Bảng Nhật ký góc của 6 khớp robot (J1 - J6)
CREATE TABLE IF NOT EXISTS NhatKyGocKhop (
    Goc_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    RobotID INTEGER NOT NULL,
    HoatDongID INTEGER,
    ThoiGian TEXT NOT NULL,
    Goc_J1 REAL NOT NULL,
    Goc_J2 REAL NOT NULL,
    Goc_J3 REAL NOT NULL,
    Goc_J4 REAL NOT NULL,
    Goc_J5 REAL NOT NULL,
    Goc_J6 REAL NOT NULL,
    TrangThai TEXT,
    FOREIGN KEY (RobotID) REFERENCES ThietBiRobot(RobotID),
    FOREIGN KEY (HoatDongID) REFERENCES NhatKyHoatDong(HoatDongID)
);

-- 6. Bảng Thiết bị cảm biến trên cánh tay robot
CREATE TABLE IF NOT EXISTS CamBien (
    CamBienID INTEGER PRIMARY KEY AUTOINCREMENT,
    RobotID INTEGER NOT NULL,
    TenCamBien TEXT NOT NULL,
    LoaiCamBien TEXT NOT NULL,
    HangSanXuat TEXT,
    ModelCamBien TEXT,
    ViTriLapDat TEXT NOT NULL,
    DonViDo TEXT,
    TrangThai TEXT NOT NULL CHECK(TrangThai IN ('Hoat dong', 'Canh bao', 'Hong', 'Bao tri')),
    GhiChu TEXT,
    FOREIGN KEY (RobotID) REFERENCES ThietBiRobot(RobotID)
);

-- 7. Bảng Nhật ký số đo cảm biến (LiDAR, Encoder, Siêu âm, v.v.)
CREATE TABLE IF NOT EXISTS NhatKyCamBien (
    DuLieuCamBienID INTEGER PRIMARY KEY AUTOINCREMENT,
    CamBienID INTEGER NOT NULL,
    HoatDongID INTEGER,
    ThoiGian TEXT NOT NULL,
    GiaTri REAL NOT NULL,
    DonViDo TEXT,
    TrangThaiDuLieu TEXT CHECK(TrangThaiDuLieu IN ('Binh thuong', 'Canh bao', 'Loi')),
    GhiChu TEXT,
    FOREIGN KEY (CamBienID) REFERENCES CamBien(CamBienID),
    FOREIGN KEY (HoatDongID) REFERENCES NhatKyHoatDong(HoatDongID)
);

-- 8. Bảng Nhật ký cảnh báo và lỗi hệ thống
CREATE TABLE IF NOT EXISTS NhatKyCanhBao (
    CanhBao_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    RobotID INTEGER NOT NULL,
    HoatDongID INTEGER,
    ThoiGian TEXT NOT NULL,
    MaLoi TEXT,
    MucDo TEXT NOT NULL CHECK(MucDo IN ('Thap', 'Trung binh', 'Cao', 'Nghiem trong')),
    NoiDung TEXT NOT NULL,
    TrangThaiXuLy TEXT NOT NULL CHECK(TrangThaiXuLy IN ('Chua xu ly', 'Dang xu ly', 'Da xu ly')),
    GhiChu TEXT,
    FOREIGN KEY (RobotID) REFERENCES ThietBiRobot(RobotID),
    FOREIGN KEY (HoatDongID) REFERENCES NhatKyHoatDong(HoatDongID)
);

-- Tạo Index tăng tốc truy vấn theo thời gian và thiết bị
CREATE INDEX IF NOT EXISTS idx_gockhop_robot_time ON NhatKyGocKhop(RobotID, ThoiGian);
CREATE INDEX IF NOT EXISTS idx_cambien_robot_time ON NhatKyCamBien(CamBienID, ThoiGian);
CREATE INDEX IF NOT EXISTS idx_canhbao_trangthai ON NhatKyCanhBao(TrangThaiXuLy);
CREATE INDEX IF NOT EXISTS idx_hoatdong_thoigian ON NhatKyHoatDong(ThoiGianBatDau);
