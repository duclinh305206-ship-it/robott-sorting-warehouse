
from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
import threading
import time
from streamlit_autorefresh import st_autorefresh

from realtime_page import render_realtime


# ==========================================
# 1. KET NOI CO SO DU LIEU
# ==========================================

DB_PATH = Path(__file__).resolve().with_name("warehouse_robot.db")

st.set_page_config(
    page_title="Quản lý hệ thống robot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stMetric"] {
        background: rgba(120,120,120,0.08);
        padding: 14px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


if not DB_PATH.exists():
    st.error(f"Không tìm thấy database: {DB_PATH}")
    st.info(
        "Hãy đặt file app.py cùng thư mục "
        "với warehouse_robot.db."
    )
    st.stop()


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


@st.cache_data(ttl=1)
def load_data(query: str, params=()):
    conn = get_connection()

    try:
        return pd.read_sql_query(
            query,
            conn,
            params=params
        )
    finally:
        conn.close()


def count_rows(table: str) -> int:
    df = load_data(
        f"SELECT COUNT(*) AS total FROM {table}"
    )
    return int(df.iloc[0]["total"])


def execute_query(sql: str, params=()):
    conn = get_connection()
    try:
        with conn:
            conn.execute(sql, params)
    finally:
        conn.close()


# ==========================================
# 2. MENU CHUYEN TRANG
# ==========================================

st.sidebar.header("🤖 ROBOT WAREHOUSE")

page = st.sidebar.radio(
    "Chọn chức năng",
    [
        "📊 Quản lý dữ liệu",
        "📡 Giám sát Real-time"
    ],
    key="main_page"
)


# Neu chon Real-time thi hien thi giao dien rieng
if page == "📡 Giám sát Real-time":

    render_realtime(DB_PATH)

    st.stop()


# ==========================================
# 3. DASHBOARD QUAN LY DU LIEU
# ==========================================

st.title("🤖 DASHBOARD QUẢN LÝ HỆ THỐNG ROBOT")

st.caption(
    "Đề tài: Thu thập và quản lí dữ liệu các cánh tay robot công nghiệp của hệ thống phân loại sản phẩm trong nhà kho tự động."
)


# ==========================================
# 4. BO LOC DASHBOARD
# ==========================================

st.sidebar.divider()
st.sidebar.header("Bộ lọc dashboard")

robot_df = load_data("""
    SELECT RobotID, TenRobot, LoaiRobot,
           HangSanXuat, ModelRobot,
           ViTriLapDat, NgayLapDat,
           TrangThaiHoatDong, GhiChu
    FROM ThietBiRobot
    ORDER BY RobotID
""")

if robot_df.empty:
    st.warning("Chưa có dữ liệu robot.")
    st.stop()


robot_options = (
    ["Tất cả robot"]
    + robot_df["TenRobot"].astype(str).tolist()
)

selected_robot = st.sidebar.selectbox(
    "Chọn robot",
    robot_options
)

selected_robot_id = None

if selected_robot != "Tất cả robot":

    selected_robot_id = int(
        robot_df.loc[
            robot_df["TenRobot"] == selected_robot,
            "RobotID"
        ].iloc[0]
    )


# ==========================================
# 4.1. DONG BO REAL-TIME & MO PHONG TRUC TIEP
# ==========================================

st.sidebar.divider()
st.sidebar.header("⚡ Đồng bộ Real-time")

live_sync = st.sidebar.toggle("Tự động đồng bộ không delay (1s)", value=True, key="toggle_live_sync")
if live_sync:
    st_autorefresh(interval=1000, key="auto_sync_main_dashboard")

# Điều khiển mô phỏng trực tiếp từ Web Dashboard (không cần mở terminal nếu muốn)
if "sim_bg_running" not in st.session_state:
    st.session_state.sim_bg_running = False

def bg_simulation_worker():
    import mo_phong_du_lieu
    step = 0
    while st.session_state.get("sim_bg_running", False):
        try:
            with mo_phong_du_lieu.get_connection() as c:
                robots = [r[0] for r in c.execute("SELECT RobotID FROM ThietBiRobot").fetchall()]
                act_ids = {rid: c.execute("SELECT HoatDongID FROM NhatKyHoatDong WHERE RobotID = ? ORDER BY HoatDongID DESC LIMIT 1", (rid,)).fetchone()[0] for rid in robots}
                sensors = [{"CamBienID": r[0], "RobotID": r[1], "LoaiCamBien": r[2], "DonViDo": r[3]} for r in c.execute("SELECT CamBienID, RobotID, LoaiCamBien, DonViDo FROM CamBien").fetchall()]
                product_ids = [r[0] for r in c.execute("SELECT MaHangID FROM MaHang").fetchall()]
                
                mo_phong_du_lieu.simulate_joint_data(c, robots, act_ids, step)
                mo_phong_du_lieu.simulate_sensor_data(c, sensors, act_ids, step)
                mo_phong_du_lieu.simulate_picking_activity(c, robots, product_ids, act_ids, step)
                mo_phong_du_lieu.simulate_periodic_alerts(c, robots, act_ids, step)
            step += 1
            time.sleep(1)
        except Exception:
            time.sleep(1)

sim_switch = st.sidebar.toggle("▶️ Chạy mô phỏng trực tiếp trên Web", value=st.session_state.sim_bg_running, key="sim_web_switch")
if sim_switch != st.session_state.sim_bg_running:
    st.session_state.sim_bg_running = sim_switch
    if sim_switch:
        th = threading.Thread(target=bg_simulation_worker, daemon=True)
        th.start()
        st.sidebar.success("🟢 Mô phỏng đang chạy ngầm mỗi 1s...")
    else:
        st.sidebar.info("⏹️ Đã dừng mô phỏng.")

if st.sidebar.button("🔄 Làm mới thủ công"):
    st.cache_data.clear()
    st.rerun()


# ==========================================
# 5. CAC CHI SO TONG QUAN
# ==========================================

robot_count = count_rows("ThietBiRobot")
sensor_count = count_rows("CamBien")
activity_count = count_rows("NhatKyHoatDong")
alert_count = count_rows("NhatKyCanhBao")

# Thống kê tỷ lệ gắp hàng và hoạt động
success_df = load_data("""
    SELECT 
        COUNT(*) AS total,
        SUM(CASE WHEN KetQua = 'Thanh cong' THEN 1 ELSE 0 END) AS success,
        SUM(CASE WHEN KetQua != 'Thanh cong' THEN 1 ELSE 0 END) AS fail
    FROM NhatKyHoatDong
""")
total_act = int(success_df.iloc[0]["total"]) if not success_df.empty and pd.notna(success_df.iloc[0]["total"]) else 0
success_act = int(success_df.iloc[0]["success"]) if not success_df.empty and pd.notna(success_df.iloc[0]["success"]) else 0
fail_act = total_act - success_act
success_rate = (success_act / total_act * 100) if total_act > 0 else 0.0

normal_robots = len(robot_df[robot_df["TrangThaiHoatDong"] == "Hoat dong"])
warning_robots = len(robot_df[robot_df["TrangThaiHoatDong"] == "Canh bao"])
maint_robots = len(robot_df[robot_df["TrangThaiHoatDong"].isin(["Bao tri", "Ngung hoat dong"])])

if warning_robots > 0:
    robot_delta = f"⚠️ {warning_robots} robot cảnh báo"
    delta_color_type = "inverse"
elif normal_robots == robot_count:
    robot_delta = "🟢 Tất cả bình thường"
    delta_color_type = "normal"
else:
    robot_delta = f"🔧 {maint_robots} robot bảo trì"
    delta_color_type = "off"

# Banner cảnh báo nếu có sự cố chưa xử lý
unhandled_alerts = load_data("""
    SELECT COUNT(*) AS total
    FROM NhatKyCanhBao
    WHERE TrangThaiXuLy != 'Da xu ly'
""")
unhandled_total = int(unhandled_alerts.iloc[0]["total"]) if not unhandled_alerts.empty else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Robot bình thường", f"{normal_robots} / {robot_count}", robot_delta, delta_color=delta_color_type)
col2.metric("Tổng lượt gắp hàng", f"{total_act:,} lượt")
col3.metric("Tỷ lệ gắp thành công", f"{success_rate:.1f}%", f"{success_act} kiện đạt")
col4.metric("Tỷ lệ lỗi / rơi hàng", f"{(100 - success_rate):.1f}%", f"{fail_act} kiện lỗi", delta_color="inverse")
col5.metric("Sự cố tồn đọng", f"{unhandled_total} cảnh báo", "Cần xử lý" if unhandled_total > 0 else "An toàn", delta_color="inverse" if unhandled_total > 0 else "normal")

if unhandled_total > 0:
    st.warning(
        f"⚠️ **Hệ thống đang có {unhandled_total} cảnh báo sự cố chưa được xử lý xong!** "
        "Vui lòng vào tab **⚙️ Quản lý & Cập nhật** để kiểm tra và cập nhật tiến độ."
    )


# ==========================================
# 6. CAC TAB CHUC NANG
# ==========================================

(
    tab_overview,
    tab_robots,
    tab_activities,
    tab_sensors,
    tab_alerts,
    tab_crud,
    tab_tables
) = st.tabs([
    "📊 Tổng quan",
    "🤖 Robot",
    "🧾 Hoạt động",
    "📡 Cảm biến",
    "⚠️ Cảnh báo",
    "⚙️ Quản lý & Cập nhật",
    "🗃️ Dữ liệu bảng"
])


# ==========================================
# 7. TAB TONG QUAN
# ==========================================

with tab_overview:

    st.subheader("Tình trạng các robot")

    status_counts = (
        robot_df["TrangThaiHoatDong"]
        .fillna("Chưa xác định")
        .value_counts()
        .rename_axis("Trạng thái")
        .reset_index(name="Số lượng")
    )

    left, right = st.columns(2)

    with left:

        st.dataframe(
            robot_df[
                [
                    "TenRobot",
                    "ModelRobot",
                    "ViTriLapDat",
                    "TrangThaiHoatDong"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    with right:

        st.bar_chart(
            status_counts.set_index("Trạng thái")
        )


    st.subheader("🎯 Tỷ lệ hoạt động & Hiệu suất gắp hàng của Robot")
    p_col1, p_col2 = st.columns(2)

    with p_col1:
        st.write("##### Tỷ lệ gắp hàng toàn hệ thống")
        if total_act > 0:
            pie_df = pd.DataFrame({
                "KetQua": ["Thành công", "Lỗi / Sự cố"],
                "SoLuong": [success_act, fail_act]
            })
            fig_pie = px.pie(
                pie_df,
                names="KetQua",
                values="SoLuong",
                hole=0.45,
                color="KetQua",
                color_discrete_map={"Thành công": "#28a745", "Lỗi / Sự cố": "#dc3545"}
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu gắp hàng.")

    with p_col2:
        st.write("##### Hiệu suất phân loại theo từng Robot")
        robot_perf = load_data("""
            SELECT 
                r.TenRobot,
                COUNT(a.HoatDongID) AS TongSoKien,
                SUM(CASE WHEN a.KetQua = 'Thanh cong' THEN 1 ELSE 0 END) AS ThanhCong,
                SUM(CASE WHEN a.KetQua != 'Thanh cong' THEN 1 ELSE 0 END) AS SoLoi
            FROM ThietBiRobot r
            LEFT JOIN NhatKyHoatDong a ON r.RobotID = a.RobotID
            GROUP BY r.RobotID, r.TenRobot
            ORDER BY r.RobotID
        """)
        if not robot_perf.empty:
            fig_bar_perf = px.bar(
                robot_perf,
                x="TenRobot",
                y=["ThanhCong", "SoLoi"],
                barmode="group",
                title="Số lượt gắp Thành công vs Lỗi theo Robot",
                labels={"value": "Số lượt", "TenRobot": "Robot", "variable": "Kết quả"},
                color_discrete_map={"ThanhCong": "#28a745", "SoLoi": "#dc3545"}
            )
            st.plotly_chart(fig_bar_perf, use_container_width=True)


    st.subheader("Số hoạt động theo robot")

    activity_by_robot = load_data("""
        SELECT r.TenRobot,
               COUNT(a.HoatDongID) AS SoHoatDong
        FROM ThietBiRobot r
        LEFT JOIN NhatKyHoatDong a
            ON r.RobotID = a.RobotID
        GROUP BY r.RobotID, r.TenRobot
        ORDER BY r.RobotID
    """)

    st.bar_chart(
        activity_by_robot.set_index("TenRobot")
    )


    st.subheader("Tình trạng cảnh báo")

    alert_status = load_data("""
        SELECT TrangThaiXuLy AS TrangThai,
               COUNT(*) AS SoLuong
        FROM NhatKyCanhBao
        GROUP BY TrangThaiXuLy
        ORDER BY SoLuong DESC
    """)

    if not alert_status.empty:

        st.bar_chart(
            alert_status.set_index("TrangThai")
        )

    else:

        st.info("Chưa có cảnh báo.")


# ==========================================
# 8. TAB QUAN LY ROBOT
# ==========================================

with tab_robots:

    st.subheader(
        "Danh sách robot và thông số kỹ thuật"
    )

    robot_details = load_data("""
        SELECT
            r.RobotID,
            r.TenRobot,
            r.LoaiRobot,
            r.HangSanXuat,
            r.ModelRobot,
            r.ViTriLapDat,
            r.NgayLapDat,
            r.TrangThaiHoatDong,
            t.SoBacTuDo,
            t.SoLuongKhop,
            t.TaiTrongToiDa,
            t.TamVoiToiDa,
            t.DoChinhXacLapLai,
            t.TocDoToiDa,
            t.BoDieuKhien,
            t.GiaoThucKetNoi
        FROM ThietBiRobot r
        LEFT JOIN ThongSoKyThuat t
            ON r.RobotID = t.RobotID
        ORDER BY r.RobotID
    """)

    if selected_robot_id is not None:

        robot_details = robot_details[
            robot_details["RobotID"]
            == selected_robot_id
        ]

    st.dataframe(
        robot_details,
        use_container_width=True,
        hide_index=True
    )


    st.subheader("Cảm biến được lắp trên robot")

    sensor_inventory = load_data("""
        SELECT
            r.TenRobot,
            c.TenCamBien,
            c.LoaiCamBien,
            c.HangSanXuat,
            c.ModelCamBien,
            c.ViTriLapDat,
            c.DonViDo,
            c.TrangThai
        FROM CamBien c
        JOIN ThietBiRobot r
            ON c.RobotID = r.RobotID
        ORDER BY r.RobotID, c.CamBienID
    """)

    if selected_robot_id is not None:

        chosen_name = robot_df.loc[
            robot_df["RobotID"] == selected_robot_id,
            "TenRobot"
        ].iloc[0]

        sensor_inventory = sensor_inventory[
            sensor_inventory["TenRobot"] == chosen_name
        ]

    st.dataframe(
        sensor_inventory,
        use_container_width=True,
        hide_index=True
    )


# ==========================================
# 9. TAB LICH SU HOAT DONG
# ==========================================

with tab_activities:

    st.subheader("Lịch sử hoạt động")

    activities = load_data("""
        SELECT
            a.HoatDongID,
            r.TenRobot,
            m.MaHang,
            m.TenSanPham,
            a.ThoiGianBatDau,
            a.ThoiGianKetThuc,
            a.LoaiThaoTac,
            a.KetQua,
            a.ThoiGianXuLy,
            a.GhiChu
        FROM NhatKyHoatDong a
        JOIN ThietBiRobot r
            ON a.RobotID = r.RobotID
        LEFT JOIN MaHang m
            ON a.MaHangID = m.MaHangID
        ORDER BY
            a.ThoiGianBatDau DESC,
            a.HoatDongID DESC
    """)

    if selected_robot_id is not None:

        chosen_name = robot_df.loc[
            robot_df["RobotID"] == selected_robot_id,
            "TenRobot"
        ].iloc[0]

        activities = activities[
            activities["TenRobot"] == chosen_name
        ]

    st.dataframe(
        activities,
        use_container_width=True,
        hide_index=True
    )


    st.subheader("Thống kê kết quả hoạt động")

    if not activities.empty:

        result_counts = (
            activities["KetQua"]
            .fillna("Chưa cập nhật")
            .value_counts()
            .rename_axis("Kết quả")
            .reset_index(name="Số lượng")
        )

        st.bar_chart(
            result_counts.set_index("Kết quả")
        )


# ==========================================
# 10. TAB DU LIEU CAM BIEN
# ==========================================

with tab_sensors:

    st.subheader("Dữ liệu cảm biến")

    sensor_data = load_data("""
        SELECT
            d.DuLieuCamBienID,
            r.TenRobot,
            c.TenCamBien,
            c.LoaiCamBien,
            d.ThoiGian,
            d.GiaTri,
            COALESCE(d.DonViDo, c.DonViDo) AS DonViDo,
            d.TrangThaiDuLieu,
            d.GhiChu
        FROM NhatKyCamBien d
        JOIN CamBien c
            ON d.CamBienID = c.CamBienID
        JOIN ThietBiRobot r
            ON c.RobotID = r.RobotID
        ORDER BY
            d.ThoiGian DESC,
            d.DuLieuCamBienID DESC
    """)

    if selected_robot_id is not None:

        chosen_name = robot_df.loc[
            robot_df["RobotID"] == selected_robot_id,
            "TenRobot"
        ].iloc[0]

        sensor_data = sensor_data[
            sensor_data["TenRobot"] == chosen_name
        ]

    if not sensor_data.empty:

        sensor_names = (
            ["Tất cả cảm biến"]
            + sorted(
                sensor_data["TenCamBien"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )
        )

        chosen_sensor = st.selectbox(
            "Lọc theo cảm biến",
            sensor_names,
            key="sensor_filter"
        )

        if chosen_sensor != "Tất cả cảm biến":

            sensor_data = sensor_data[
                sensor_data["TenCamBien"] == chosen_sensor
            ]

        st.dataframe(
            sensor_data,
            use_container_width=True,
            hide_index=True
        )


        chart_data = sensor_data.copy()

        chart_data["GiaTri"] = pd.to_numeric(
            chart_data["GiaTri"],
            errors="coerce"
        )

        chart_data = chart_data.dropna(
            subset=["GiaTri"]
        )

        if not chart_data.empty:

            st.subheader(
                "Biểu đồ giá trị cảm biến"
            )

            chart_data["Nhãn"] = (
                chart_data["TenRobot"].astype(str)
                + " - "
                + chart_data["TenCamBien"].astype(str)
            )

            chart_pivot = chart_data.pivot_table(
                index="ThoiGian",
                columns="Nhãn",
                values="GiaTri",
                aggfunc="mean"
            ).sort_index()

            st.line_chart(chart_pivot)

    else:

        st.info(
            "Không có dữ liệu cảm biến phù hợp với bộ lọc."
        )


# ==========================================
# 11. TAB CANH BAO
# ==========================================

with tab_alerts:

    st.subheader("Nhật ký cảnh báo và lỗi")

    alerts = load_data("""
        SELECT
            a.CanhBao_ID,
            r.TenRobot,
            a.ThoiGian,
            a.MaLoi,
            a.MucDo,
            a.NoiDung,
            a.TrangThaiXuLy,
            a.GhiChu
        FROM NhatKyCanhBao a
        JOIN ThietBiRobot r
            ON a.RobotID = r.RobotID
        ORDER BY
            a.ThoiGian DESC,
            a.CanhBao_ID DESC
    """)

    if selected_robot_id is not None:

        chosen_name = robot_df.loc[
            robot_df["RobotID"] == selected_robot_id,
            "TenRobot"
        ].iloc[0]

        alerts = alerts[
            alerts["TenRobot"] == chosen_name
        ]

    st.dataframe(
        alerts,
        use_container_width=True,
        hide_index=True
    )

    if not alerts.empty:

        severity_counts = (
            alerts["MucDo"]
            .fillna("Chưa xác định")
            .value_counts()
            .rename_axis("Mức độ")
            .reset_index(name="Số lượng")
        )

        st.bar_chart(
            severity_counts.set_index("Mức độ")
        )


# ==========================================
# 12. TAB QUAN LY & CAP NHAT DU LIEU (CRUD)
# ==========================================

with tab_crud:

    st.subheader("⚙️ Quản lý & Cập nhật dữ liệu hệ thống")
    st.caption("Cập nhật trạng thái máy móc, xử lý sự cố cảnh báo và quản lý danh mục hàng hóa.")

    crud_action = st.radio(
        "Chọn tác vụ quản lý:",
        ["🔧 Cập nhật trạng thái Robot", "🛠️ Xử lý cảnh báo sự cố", "📦 Thêm mới mã hàng hóa", "🚨 Kích hoạt sự cố thử nghiệm"],
        horizontal=True,
        key="crud_action_choice"
    )

    if crud_action == "🔧 Cập nhật trạng thái Robot":
        st.write("##### Thay đổi trạng thái vận hành của cánh tay Robot")
        with st.form("form_update_robot"):
            robot_choices = {
                f"{row['TenRobot']} ({row['ModelRobot']})": int(row['RobotID'])
                for _, row in robot_df.iterrows()
            }
            selected_rb_label = st.selectbox(
                "Chọn Robot cần điều chỉnh:",
                list(robot_choices.keys())
            )
            target_rb_id = robot_choices[selected_rb_label]

            current_row = robot_df[robot_df["RobotID"] == target_rb_id].iloc[0]
            st.info(
                f"Trạng thái hiện tại: **{current_row['TrangThaiHoatDong']}** | Vị trí: **{current_row['ViTriLapDat']}**"
            )

            status_list = ["Hoat dong", "Canh bao", "Bao tri", "Ngung hoat dong"]
            current_status = current_row["TrangThaiHoatDong"]
            default_index = status_list.index(current_status) if current_status in status_list else 0

            new_status = st.selectbox(
                "Trạng thái mới:",
                status_list,
                index=default_index
            )
            new_note = st.text_input(
                "Ghi chú vận hành / lý do thay đổi:",
                value=str(current_row["GhiChu"] or "")
            )

            btn_update_rb = st.form_submit_button("💾 Lưu thay đổi trạng thái Robot")
            if btn_update_rb:
                try:
                    execute_query(
                        "UPDATE ThietBiRobot SET TrangThaiHoatDong = ?, GhiChu = ? WHERE RobotID = ?",
                        (new_status, new_note, target_rb_id)
                    )
                    st.success(f"✅ Đã cập nhật trạng thái của Robot {selected_rb_label} thành: {new_status}!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as ex:
                    st.error(f"Lỗi khi cập nhật: {ex}")

    elif crud_action == "🛠️ Xử lý cảnh báo sự cố":
        st.write("##### Tiếp nhận & Cập nhật tiến độ xử lý sự cố / cảnh báo")
        
        # Nút giải quyết nhanh tất cả cảnh báo
        if st.button("⚡ Đánh dấu ĐÃ XỬ LÝ tất cả cảnh báo tồn đọng", key="btn_resolve_all"):
            execute_query("""
                UPDATE NhatKyCanhBao 
                SET TrangThaiXuLy = 'Da xu ly', GhiChu = 'Đã xử lý an toàn và hiệu chuẩn lại'
                WHERE TrangThaiXuLy != 'Da xu ly'
            """)
            st.success("✅ Đã chuyển toàn bộ sự cố sang trạng thái 'Đã xử lý'!")
            st.cache_data.clear()
            st.rerun()

        all_alerts = load_data("""
            SELECT a.CanhBao_ID, r.TenRobot, a.ThoiGian, a.MucDo, a.NoiDung, a.TrangThaiXuLy, a.GhiChu
            FROM NhatKyCanhBao a
            JOIN ThietBiRobot r ON a.RobotID = r.RobotID
            ORDER BY a.CanhBao_ID DESC
        """)

        if all_alerts.empty:
            st.info("Hiện tại không có cảnh báo nào trong hệ thống.")
        else:
            with st.form("form_handle_alert"):
                alert_options = {
                    f"#{row['CanhBao_ID']} - [{row['MucDo']}] {row['TenRobot']} ({row['ThoiGian']}): {row['NoiDung']} [Trạng thái: {row['TrangThaiXuLy']}]": int(row['CanhBao_ID'])
                    for _, row in all_alerts.iterrows()
                }
                selected_alert_label = st.selectbox(
                    "Chọn sự cố / cảnh báo cần cập nhật:",
                    list(alert_options.keys())
                )
                target_alert_id = alert_options[selected_alert_label]

                alert_curr = all_alerts[all_alerts["CanhBao_ID"] == target_alert_id].iloc[0]

                process_statuses = ["Chua xu ly", "Dang xu ly", "Da xu ly"]
                curr_proc = alert_curr["TrangThaiXuLy"]
                proc_idx = process_statuses.index(curr_proc) if curr_proc in process_statuses else 0

                new_process_status = st.selectbox(
                    "Cập nhật trạng thái xử lý:",
                    process_statuses,
                    index=proc_idx
                )
                resolution_note = st.text_input(
                    "Ghi chú biện pháp khắc phục:",
                    value=str(alert_curr["GhiChu"] or "Đã kiểm tra kỹ thuật")
                )

                btn_update_alert = st.form_submit_button("✅ Cập nhật tiến độ xử lý cảnh báo")
                if btn_update_alert:
                    try:
                        execute_query(
                            "UPDATE NhatKyCanhBao SET TrangThaiXuLy = ?, GhiChu = ? WHERE CanhBao_ID = ?",
                            (new_process_status, resolution_note, target_alert_id)
                        )
                        st.success(f"✅ Đã cập nhật cảnh báo #{target_alert_id} thành: {new_process_status}!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Lỗi khi cập nhật: {ex}")

    elif crud_action == "📦 Thêm mới mã hàng hóa":
        st.write("##### Thêm loại sản phẩm mới vào danh mục nhà kho")
        with st.form("form_add_product"):
            c_code, c_name = st.columns(2)
            with c_code:
                new_code = st.text_input("Mã hàng (VD: MH006):", placeholder="MH006")
            with c_name:
                new_name = st.text_input("Tên sản phẩm:", placeholder="Sản phẩm F")

            c_cat, c_weight = st.columns(2)
            with c_cat:
                new_cat = st.selectbox(
                    "Phân loại hàng:",
                    ["Loai A", "Loai B", "Loai C", "Hang de vo", "Linh kien dien tu"]
                )
            with c_weight:
                new_weight = st.number_input(
                    "Khối lượng chuẩn (kg):",
                    min_value=0.1,
                    max_value=50.0,
                    value=1.5,
                    step=0.1
                )

            c_l, c_w, c_h = st.columns(3)
            with c_l:
                new_l = st.number_input("Chiều dài (cm):", value=15.0, min_value=1.0)
            with c_w:
                new_w = st.number_input("Chiều rộng (cm):", value=10.0, min_value=1.0)
            with c_h:
                new_h = st.number_input("Chiều cao (cm):", value=8.0, min_value=1.0)

            new_p_note = st.text_input("Ghi chú sản phẩm:", value="Hàng nhập kho tự động")

            btn_add_p = st.form_submit_button("➕ Thêm sản phẩm vào CSDL")
            if btn_add_p:
                if not new_code.strip() or not new_name.strip():
                    st.error("Vui lòng nhập đầy đủ Mã hàng và Tên sản phẩm!")
                else:
                    try:
                        execute_query("""
                            INSERT INTO MaHang (
                                MaHang, TenSanPham, LoaiSanPham,
                                KhoiLuong, ChieuDai, ChieuRong, ChieuCao, GhiChu
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            new_code.strip(),
                            new_name.strip(),
                            new_cat,
                            new_weight,
                            new_l,
                            new_w,
                            new_h,
                            new_p_note
                        ))
                        st.success(f"✅ Đã thêm sản phẩm '{new_name}' ({new_code}) vào danh mục!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Lỗi khi thêm sản phẩm (có thể trùng mã): {ex}")

    elif crud_action == "🚨 Kích hoạt sự cố thử nghiệm":
        st.write("##### Giả lập sự cố cánh tay robot để kiểm thử quy trình xử lý (Demo)")
        st.info("💡 Tính năng này giúp mày hoặc giảng viên tạo ra một lỗi bất kỳ ngay lập tức để xem hệ thống cảnh báo và kiểm tra quy trình xử lý sự cố.")
        
        with st.form("form_inject_fault"):
            robot_choices = {
                f"{row['TenRobot']} ({row['ModelRobot']})": int(row['RobotID'])
                for _, row in robot_df.iterrows()
            }
            fault_robot_label = st.selectbox("Chọn Robot bị sự cố:", list(robot_choices.keys()))
            target_fault_robot_id = robot_choices[fault_robot_label]
            
            fault_type = st.selectbox(
                "Loại sự cố / cảnh báo phát sinh:",
                [
                    "🔥 Động cơ khớp nối quá nhiệt (54.5°C) - Cần làm mát khẩn cấp",
                    "⚠️ Lực hút kẹp không đủ - Trượt rơi kiện hàng trên băng chuyền",
                    "🛑 Sai lệch góc quay trục J2 vượt dung sai cho phép (±3.2°)",
                    "📡 Cảm biến LiDAR phát hiện vật cản bất thường trong bán kính gắp",
                    "⚡ Quá tải mô-men xoắn khi gắp kiện hàng nặng"
                ]
            )
            
            fault_level = st.selectbox("Mức độ nghiêm trọng:", ["Cao", "Trung binh", "Nghiem trong"])
            
            btn_trigger_fault = st.form_submit_button("🚨 Kích hoạt sự cố ngay")
            if btn_trigger_fault:
                try:
                    from datetime import datetime
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 1. Ghi nhận cảnh báo mới vào CSDL
                    execute_query("""
                        INSERT INTO NhatKyCanhBao (
                            RobotID, HoatDongID, ThoiGian, MaLoi, MucDo, NoiDung, TrangThaiXuLy, GhiChu
                        )
                        VALUES (?, NULL, ?, 'ERR_DEMO', ?, ?, 'Chua xu ly', 'Su co kich hoat thu nghiem')
                    """, (target_fault_robot_id, now_str, fault_level, fault_type))
                    
                    # 2. Đổi trạng thái Robot sang 'Canh bao'
                    execute_query(
                        "UPDATE ThietBiRobot SET TrangThaiHoatDong = 'Canh bao', GhiChu = ? WHERE RobotID = ?",
                        (f"Đang gặp sự cố: {fault_type[:30]}...", target_fault_robot_id)
                    )
                    
                    st.error(f"🚨 ĐÃ KÍCH HOẠT SỰ CỐ TRÊN {fault_robot_label}! Banner màu vàng đã xuất hiện trên hệ thống.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as ex:
                    st.error(f"Lỗi: {ex}")


# ==========================================
# 13. TAB XEM DU LIEU CAC BANG
# ==========================================

with tab_tables:

    st.subheader(
        "Xem dữ liệu gốc của từng bảng"
    )

    table_names = [
        "ThietBiRobot",
        "ThongSoKyThuat",
        "MaHang",
        "NhatKyHoatDong",
        "NhatKyGocKhop",
        "NhatKyCanhBao",
        "CamBien",
        "NhatKyCamBien"
    ]

    selected_table = st.selectbox(
        "Chọn bảng dữ liệu",
        table_names
    )

    raw_df = load_data(
        f'SELECT * FROM "{selected_table}"'
    )

    st.caption(
        f"Số bản ghi: {len(raw_df)}"
    )

    st.dataframe(
        raw_df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = raw_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="⬇️ Tải bảng này về CSV",
        data=csv_data,
        file_name=f"{selected_table}.csv",
        mime="text/csv"
    )


# ==========================================
# 13. PHAN TICH BIEU DO
# ==========================================

st.divider()

st.header("📈 PHÂN TÍCH VÀ TRỰC QUAN HÓA DỮ LIỆU")


# ------------------------------------------
# A. BIEU DO SO HOAT DONG THEO ROBOT
# ------------------------------------------

st.subheader("1. Thống kê hoạt động của robot")

activity_chart = load_data("""
    SELECT
        r.TenRobot,
        COUNT(a.HoatDongID) AS SoHoatDong
    FROM ThietBiRobot r
    LEFT JOIN NhatKyHoatDong a
        ON r.RobotID = a.RobotID
    GROUP BY r.RobotID, r.TenRobot
    ORDER BY r.RobotID
""")

if selected_robot_id is not None:

    chosen_name = robot_df.loc[
        robot_df["RobotID"] == selected_robot_id,
        "TenRobot"
    ].iloc[0]

    activity_chart = activity_chart[
        activity_chart["TenRobot"] == chosen_name
    ]


if not activity_chart.empty:

    fig_activity = px.bar(
        activity_chart,
        x="TenRobot",
        y="SoHoatDong",
        color="TenRobot",
        text="SoHoatDong",
        title="Số lượng hoạt động theo robot",
        labels={
            "TenRobot": "Tên robot",
            "SoHoatDong": "Số hoạt động"
        }
    )

    fig_activity.update_layout(
        showlegend=False,
        xaxis_title="Robot",
        yaxis_title="Số hoạt động"
    )

    st.plotly_chart(
        fig_activity,
        use_container_width=True
    )


# ------------------------------------------
# B. BIEU DO CAM BIEN THEO THOI GIAN
# ------------------------------------------

st.subheader("2. Theo dõi dữ liệu cảm biến")

sensor_chart = load_data("""
    SELECT
        r.TenRobot,
        c.TenCamBien,
        c.LoaiCamBien,
        d.ThoiGian,
        d.GiaTri,
        COALESCE(d.DonViDo, c.DonViDo) AS DonViDo
    FROM NhatKyCamBien d
    JOIN CamBien c
        ON d.CamBienID = c.CamBienID
    JOIN ThietBiRobot r
        ON c.RobotID = r.RobotID
    ORDER BY d.ThoiGian
""")

if selected_robot_id is not None:

    chosen_name = robot_df.loc[
        robot_df["RobotID"] == selected_robot_id,
        "TenRobot"
    ].iloc[0]

    sensor_chart = sensor_chart[
        sensor_chart["TenRobot"] == chosen_name
    ]


if not sensor_chart.empty:

    sensor_options = sorted(
        sensor_chart["TenCamBien"].dropna().unique().tolist()
    )

    chosen_sensor = st.selectbox(
        "Chọn cảm biến cần phân tích",
        sensor_options,
        key="plotly_sensor"
    )

    selected_sensor_data = sensor_chart[
        sensor_chart["TenCamBien"] == chosen_sensor
    ].copy()

    selected_sensor_data["GiaTri"] = pd.to_numeric(
        selected_sensor_data["GiaTri"],
        errors="coerce"
    )

    selected_sensor_data = selected_sensor_data.dropna(
        subset=["GiaTri"]
    )

    if not selected_sensor_data.empty:

        fig_sensor = px.line(
            selected_sensor_data,
            x="ThoiGian",
            y="GiaTri",
            color="TenRobot",
            markers=True,
            title=f"Biến thiên dữ liệu cảm biến: {chosen_sensor}",
            labels={
                "ThoiGian": "Thời gian",
                "GiaTri": "Giá trị đo",
                "TenRobot": "Robot"
            }
        )

        st.plotly_chart(
            fig_sensor,
            use_container_width=True
        )

else:

    st.info("Chưa có dữ liệu cảm biến.")


# ------------------------------------------
# C. HEATMAP GOC KHOP J1-J6
# ------------------------------------------

st.subheader("3. Heatmap phân tích góc khớp J1–J6")

joint_chart = load_data("""
    SELECT
        r.TenRobot,
        g.ThoiGian,
        g.Goc_J1,
        g.Goc_J2,
        g.Goc_J3,
        g.Goc_J4,
        g.Goc_J5,
        g.Goc_J6
    FROM NhatKyGocKhop g
    JOIN ThietBiRobot r
        ON g.RobotID = r.RobotID
    ORDER BY g.ThoiGian
""")

if selected_robot_id is not None:

    chosen_name = robot_df.loc[
        robot_df["RobotID"] == selected_robot_id,
        "TenRobot"
    ].iloc[0]

    joint_chart = joint_chart[
        joint_chart["TenRobot"] == chosen_name
    ]


if not joint_chart.empty:

    joint_columns = [
        "Goc_J1",
        "Goc_J2",
        "Goc_J3",
        "Goc_J4",
        "Goc_J5",
        "Goc_J6"
    ]

    joint_values = joint_chart[
        joint_columns
    ].apply(pd.to_numeric, errors="coerce")

    joint_values = joint_values.tail(30)

    fig_heatmap, ax = plt.subplots(figsize=(12, 6))

    sns.heatmap(
        joint_values,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        linewidths=0.5,
        xticklabels=[
            "J1", "J2", "J3", "J4", "J5", "J6"
        ],
        yticklabels=True,
        ax=ax,
        cbar_kws={"label": "Giá trị góc"}
    )

    ax.set_title("Heatmap giá trị góc của 6 khớp robot")
    ax.set_xlabel("Các khớp robot")
    ax.set_ylabel("Thứ tự mẫu dữ liệu")

    plt.tight_layout()

    st.pyplot(fig_heatmap)
    plt.close(fig_heatmap)

else:

    st.info("Chưa có dữ liệu góc khớp.")


st.divider()

st.caption(
    f"Nguồn dữ liệu: {DB_PATH.name} "
    "· Dashboard quản lý dữ liệu."
)
