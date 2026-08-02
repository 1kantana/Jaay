import re
from collections import defaultdict
from datetime import datetime
import streamlit as st
import pandas as pd
from io import BytesIO

# 1. ตั้งค่าหน้าตาของโปรแกรมเบื้องต้น
# TODO: ถ้ามีไอคอนของตัวเองแล้ว ใส่ path หรือ URL รูปที่นี่ เช่น "assets/icon.png" หรือ "https://.../icon.png"
CUSTOM_ICON = "https://www.rw-designer.com/icon-image/5547-256x256x32.png"

st.set_page_config(
    page_title="Jaay",
    page_icon=CUSTOM_ICON if CUSTOM_ICON else None,
    layout="centered"
)

# 2. ใส่ Custom CSS เพื่อเปลี่ยนฟอนต์ทั้งแอปเป็น "Sarabun"
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], stText, p, div, span, h1, h2, h3, h4, h5, h6, button, input, textarea {
        font-family: 'Sarabun', sans-serif !important;
    }
    /* ปรับฟอนต์สำหรับปุ่มกด (Streamlit Button) */
    .stButton button {
        font-family: 'Sarabun', sans-serif !important;
    }
    /* ปรับฟอนต์สำหรับช่องกรอกข้อมูล (Text Area) */
    .stTextArea textarea {
        font-family: 'Sarabun', sans-serif !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# TODO: ถ้ามีไอคอน/โลโก้ที่จะวางไว้หลังคำว่า "Jaay" ใส่โค้ด HTML ของไอคอนไว้ในตัวแปรนี้
# ตัวอย่าง (ไอคอนจาก URL): HEADER_ICON = '<img src="https://example.com/icon.png" width="36" style="vertical-align: middle; margin-left: 10px;">'
# ตัวอย่าง (ไอคอน SVG เอง): HEADER_ICON = '<svg ...>...</svg>'
HEADER_ICON = ""

st.markdown(
    f'<h1 style="display: flex; align-items: center; white-space: nowrap;">Jaay {HEADER_ICON}</h1>', 
    unsafe_allow_html=True
)

YEAR = 2026

# แก้ Bug: เดิมใช้เดือน "ปัจจุบันจริง" (now.month) กับทุกวันที่กรอกเสมอ
# ทำให้ถ้ากรอกรายการของเดือนก่อนหน้า (เช่น เข้าแอปวันที่ 2 ส.ค. แต่กรอกวันที่ 31 ก.ค.)
# โปรแกรมจะตีความผิดเป็นวันที่ 31 สิงหาคมทันที
# ใช้เดือนปัจจุบันจริงเป็นจุดเริ่ม แล้วเดาข้ามเดือนอัตโนมัติจากลำดับวันที่ (ดู Pass 2 ด้านล่าง)
# หรือจะระบุเดือนเองต่อวันที่ก็ได้ เช่น 27/7 หรือ 27-7
now = datetime.now()
current_month = now.month

def is_weekend(day_num, month_num):
    """ตรวจสอบว่าเป็นวันเสาร์-อาทิตย์ไหม โดยอิงจากวัน, เดือนที่ระบุ และปี 2026"""
    current_year = YEAR
    try:
        dt = datetime(current_year, month_num, int(day_num))
        return dt.weekday() >= 5, dt.strftime(f"%d/%m/{current_year}")
    except ValueError:
        return False, f"{day_num}/{month_num} (วันที่ไม่ถูกต้อง)"

def parse_day(day_part):
    """แยกวันที่ (และเดือน ถ้าระบุมาด้วย) จากส่วนหน้าสุดของบรรทัด
    รองรับ 'DD', 'DD/MM', 'DD-MM'. คืนค่า (day_num, explicit_month_or_None)"""
    sep = "/" if "/" in day_part else ("-" if "-" in day_part else None)
    if sep:
        d_str, _, m_str = day_part.partition(sep)
        if not (d_str.isdigit() and m_str.isdigit()):
            return None, None
        return int(d_str), int(m_str)
    if not day_part.isdigit():
        return None, None
    return int(day_part), None

# ช่องสำหรับกรอกข้อมูลค่าใช้จ่าย
data = st.text_area(
    "กรอกข้อมูลค่าใช้จ่ายของคุณ:",
    value="",
    height=200,
    placeholder="ตัวอย่างการกรอก:\n15 อเมซอน 60 สตาร์บัคส์ 160\n27 28 29 30 31 1 2  (คาบเกี่ยวเดือน ระบบจะเดาเดือนให้อัตโนมัติ)"
)

# ใส่คำอธิบายรูปแบบการกรอกใต้กล่องข้อความ
st.caption(
    "💡 รูปแบบที่รองรับ: `[วันที่] [รายการ] [จำนวนเงิน] ...` เรียงตามลำดับวันที่จริง — "
    "ระบบจะยึดเดือนปัจจุบันเป็นเดือนของรายการล่าสุด ถ้าเลขวันที่ \"ย้อนกลับ\" ระหว่างบรรทัด "
    "(เช่น จาก 31 ไป 1) จะถือว่าข้ามไปเดือนก่อนหน้าให้อัตโนมัติ หรือจะระบุเดือนเองต่อวันที่ก็ได้ เช่น `27/7` หรือ `27-7`"
)

# ปุ่มกดคำนวณเงิน
if st.button("คำนวณเงิน", type="primary"):
    if not data.strip():
        st.warning("โปรดกรอกข้อมูลก่อนคำนวณ")
    else:
        # คงตัวแปรภายในเป็นภาษาอังกฤษตามเดิม
        total_weekday = 0.0
        total_weekend = 0.0
        all_rows = []

        raw_lines = [ln.strip() for ln in data.strip().split('\n') if ln.strip()]

        # ---------- Pass 1: แยกวันที่/เดือน(ถ้ามี) ของแต่ละบรรทัด ----------
        parsed_lines = []  # list of dict: line, parts, day_num, explicit_month
        for line in raw_lines:
            parts = line.split()
            day_part = parts[0]
            day_num, explicit_month = parse_day(day_part)
            if day_num is None:
                st.error(f"⚠️ บรรทัดนี้ไม่ได้ขึ้นต้นด้วยวันที่ที่ถูกต้อง: '{line}'")
                continue
            parsed_lines.append({
                "line": line, "parts": parts,
                "day_num": day_num, "explicit_month": explicit_month,
            })

        # ---------- Pass 2: เดาเดือนอัตโนมัติ (ไล่จากบรรทัดสุดท้ายย้อนขึ้นไป) ----------
        # สมมติว่าผู้ใช้กรอกเรียงตามลำดับวันที่จริง (เก่า -> ใหม่)
        # ถ้าเลขวันที่ "ย้อนกลับ" เมื่อไล่จากท้ายขึ้นต้น (เช่น 1 -> 31) แปลว่าข้ามเดือนก่อนหน้า
        month_cursor = current_month
        prev_day = None
        for entry in reversed(parsed_lines):
            if entry["explicit_month"] is not None:
                month_cursor = entry["explicit_month"]
                entry["month_num"] = month_cursor
            else:
                if prev_day is not None and entry["day_num"] > prev_day:
                    month_cursor -= 1
                    if month_cursor < 1:
                        month_cursor = 12
                entry["month_num"] = month_cursor
            prev_day = entry["day_num"]

        # ---------- Pass 3: คำนวณยอดตามเดือน/วันที่ที่ระบุ ----------
        for entry in parsed_lines:
            line = entry["line"]
            parts = entry["parts"]
            day_part = parts[0]

            weekend, formatted_date = is_weekend(entry["day_num"], entry["month_num"])
            day_type = "Weekend" if weekend else "Weekday"
            items_part = " ".join(parts[1:])
            
            # ใช้ Regex ดึงคู่ [ชื่อรายการค่าใช้จ่าย] [จำนวนเงิน]
            items = re.findall(r'([^\d\s]+)\s+(\d+(?:\.\d+)?)', items_part)
            
            if not items:
                st.warning(f"🔎 ไม่พบรายการค่าใช้จ่ายในวันที่ {day_part}: '{items_part}'")
                continue

            for item, amount in items:
                amount = float(amount)

                if weekend:
                    total_weekend += amount
                else:
                    total_weekday += amount

                # ปรับการแสดงผลประเภทวันในตาราง (DataFrame) เป็นภาษาไทยทั้งหมด
                all_rows.append({
                    "วันที่": formatted_date,
                    "รายการ": item,
                    "จำนวนเงิน (บาท)": amount,
                    "ประเภทวัน": "วันหยุด" if day_type == "Weekend" else "วันทำงาน"
                })

        # แสดงผลลัพธ์เมื่อประมวลผลเสร็จ
        if all_rows:
            grand_total = total_weekday + total_weekend

            # ---------- สรุปยอดรวม (Summary) ----------
            # เดิมใช้ st.dataframe + ProgressColumn ซึ่งบนจอมือถือ (คอลัมน์ถูกบีบแคบ)
            # แถบสีของ ProgressColumn จะทับ/บดบังตัวเลขจนมองไม่เห็นยอดรวม
            # เปลี่ยนมาใช้ st.metric ซึ่ง responsive และตัวเลขจะไม่มีวันถูกบังหรือตัดขาด

            pct_weekday = (total_weekday / grand_total * 100) if grand_total else 0
            pct_weekend = (total_weekend / grand_total * 100) if grand_total else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🖲️ วันทำงาน", f"{total_weekday:,.2f} บาท", f"{pct_weekday:.1f}%")
            with col2:
                st.metric("🏕️ วันหยุด", f"{total_weekend:,.2f} บาท", f"{pct_weekend:.1f}%")
            with col3:
                st.metric("💵 ยอดรวมทั้งหมด", f"{grand_total:,.2f} บาท")

            st.markdown("---")

            # แสดงตารางสรุปรายการทั้งหมด
            st.subheader("📋 รายการทั้งหมด")
            df = pd.DataFrame(all_rows)
            df.index = df.index + 1  # เริ่ม Index ที่ 1

            def highlight_day_type(row):
                if row["ประเภทวัน"] == "วันหยุด":
                    return ['background-color: rgba(255, 148, 148, 0.18); color: #FF9494'] * len(row)
                else:
                    return ['background-color: rgba(179, 197, 255, 0.18); color: #B3C5FF'] * len(row)

            styled_df = df.style.apply(highlight_day_type, axis=1).format({"จำนวนเงิน (บาท)": "{:.2f}"})
            st.dataframe(styled_df, use_container_width=True)

            # ส่วนการสร้างไฟล์ Excel สำหรับดาวน์โหลด
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                export_df = df.copy()
                export_df["จำนวนเงิน (บาท)"] = export_df["จำนวนเงิน (บาท)"].round(2)
                export_df.to_excel(writer, index=False, sheet_name="รายการ")

                # สรุปยอดรวมในชีท Summary ให้ใช้ชื่อคอลัมน์ภาษาไทยตรงกับหน้าเว็บ
                summary_data = [
                    {"ประเภท": "วันทำงาน", "จำนวนเงิน (บาท)": round(total_weekday, 2)},
                    {"ประเภท": "วันหยุด", "จำนวนเงิน (บาท)": round(total_weekend, 2)},
                    {"ประเภท": "ยอดรวมทั้งหมด", "จำนวนเงิน (บาท)": round(grand_total, 2)}
                ]
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, index=False, sheet_name="สรุป")

                # กำหนดรูปแบบตัวเลขให้แสดงทศนิยม 2 ตำแหน่งในไฟล์ Excel ด้วย
                workbook = writer.book
                number_format = workbook.add_format({"num_format": "#,##0.00"})
                writer.sheets["รายการ"].set_column("C:C", 15, number_format)
                writer.sheets["สรุป"].set_column("B:B", 15, number_format)

            output.seek(0)

            st.download_button(
                label="📥 ดาวน์โหลดไฟล์ Excel (.xlsx)",
                data=output,
                file_name=f"jaay_report_{YEAR}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
