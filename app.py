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

def is_weekend(day_num):
    """ตรวจสอบว่าเป็นวันเสาร์-อาทิตย์ไหม โดยอิงจากวัน, เดือนปัจจุบัน และปี 2026"""
    now = datetime.now()
    current_month = now.month
    current_year = YEAR
    
    try:
        dt = datetime(current_year, current_month, int(day_num))
        return dt.weekday() >= 5, dt.strftime(f"%d/%m/{current_year}")
    except ValueError:
        return False, f"{day_num} (วันที่ไม่ถูกต้อง)"

# ช่องสำหรับกรอกข้อมูลค่าใช้จ่าย
data = st.text_area(
    "กรอกข้อมูลค่าใช้จ่ายของคุณ:",
    value="",
    height=200,
    placeholder="ตัวอย่างการกรอก:\n15 อเมซอน 60 สตาร์บัคส์ 160"
)

# ใส่คำอธิบายรูปแบบการกรอกใต้กล่องข้อความ
st.caption("💡 รูปแบบที่รองรับ: `[วันที่] [รายการ] [จำนวนเงิน] [รายการ] [จำนวนเงิน] ...` (เว้นวรรคแยกแต่ละส่วน)")

# ปุ่มกดคำนวณเงิน
if st.button("คำนวณเงิน", type="primary"):
    if not data.strip():
        st.warning("โปรดกรอกข้อมูลก่อนคำนวณ")
    else:
        # คงตัวแปรภายในเป็นภาษาอังกฤษตามเดิม
        total_weekday = 0.0
        total_weekend = 0.0
        all_rows = []

        for line in data.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            day_part = parts[0]
            
            if not day_part.isdigit():
                st.error(f"⚠️ บรรทัดนี้ไม่ได้ขึ้นต้นด้วยวันที่ที่ถูกต้อง: '{line}'")
                continue
                
            weekend, formatted_date = is_weekend(day_part)
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

            # ---------- ตารางสรุปยอดรวม (Summary Table) ----------

            pct_weekday = (total_weekday / grand_total * 100) if grand_total else 0
            pct_weekend = (total_weekend / grand_total * 100) if grand_total else 0

            summary_display_df = pd.DataFrame([
                {"ประเภทวัน": "🖍️ วันทำงาน", "ยอดรวม (บาท)": round(total_weekday, 2), "สัดส่วน (%)": round(pct_weekday, 1)},
                {"ประเภทวัน": "🏕️ วันหยุด", "ยอดรวม (บาท)": round(total_weekend, 2), "สัดส่วน (%)": round(pct_weekend, 1)},
                {"ประเภทวัน": "💵 ยอดรวมทั้งหมด", "ยอดรวม (บาท)": round(grand_total, 2), "สัดส่วน (%)": 100.0},
            ])

            st.dataframe(
                summary_display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ประเภทวัน": st.column_config.TextColumn("ประเภทวัน", width="medium"),
                    "ยอดรวม (บาท)": st.column_config.NumberColumn("ยอดรวม (บาท)", format="%.2f บาท"),
                    "สัดส่วน (%)": st.column_config.ProgressColumn(
                        "สัดส่วน (%)", format="%.1f%%", min_value=0, max_value=100
                    ),
                },
            )

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
