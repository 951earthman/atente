import streamlit as st
import datetime
import pandas as pd
import json
import os
import uuid
import time

# --- 設定頁面 ---
st.set_page_config(page_title="急診護佐任務系統", page_icon="🏥", layout="wide")

# --- 共用筆記本 (JSON) 設定 ---
DB_FILE = "data.json"

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"tasks": [], "online_nas": []}, f, ensure_ascii=False, indent=4)

def load_data():
    init_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"tasks": [], "online_nas": []}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db_data = load_data()

# --- 初始化個人設備記憶 ---
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- 床位資料 (簡化版：拿掉次區域) ---
BED_DATA = {
    "留觀(OBS)": ["1", "2", "3", "5", "6", "7", "8", "9", "10", "11", "12", "13", "15", "16", "17", "18", "19", "20", "21", "22", "23", "25", "26", "27", "28", "29", "30", "31", "32", "33", "35", "36", "37", "38", "39"],
    "診間": ["5", "6", "11", "12", "13", "15", "16", "17", "18", "19", "20", "21", "22", "23", "25", "27", "28", "29", "30", "31", "32", "33", "36", "37", "38", "39"],
    "兒科": ["501", "502", "503", "505", "506", "507", "508", "509"],
    "急救區": [],
    "檢傷": [],
    "縫合室": [],
    "超音波室": []
}

# --- 側邊欄 ---
st.sidebar.title("🏥 系統導覽")
role = st.sidebar.radio("請選擇角色介面：", [
    "👩‍⚕️ 護理人員派發端", 
    "🧑‍⚕️ 護佐接收端", 
    "🖥️ 急診動態看板", 
    "📊 歷史紀錄"
])

st.sidebar.divider()
auto_refresh = st.sidebar.checkbox("🔄 開啟自動更新 (10秒)", value=(role == "🖥️ 急診動態看板"))
if st.sidebar.button("👉 立即手動同步", type="primary", use_container_width=True):
    st.rerun()

# ==========================================
# 畫面一：護理人員派發端
# ==========================================
if role == "👩‍⚕️ 護理人員派發端":
    st.title("👩‍⚕️ 任務派發")
    
    online_list = db_data.get("online_nas", [])
    st.info(f"🟢 目前線上：{', '.join(online_list) if online_list else '無人上線'}")
    
    # --- 步驟 1：位置 ---
    with st.container(border=True):
        st.subheader("📍 步驟 1：選擇位置")
        col1, col2 = st.columns(2)
        with col1:
            area = st.selectbox("大區域", list(BED_DATA.keys()))
        with col2:
            beds_in_area = BED_DATA[area]
            if beds_in_area:
                bed_options = ["(區域撥補/不需床號)"] + beds_in_area
                bed = st.selectbox("床號", bed_options)
            else:
                st.write("\n")
                st.info("此區域不需選擇床號")
                bed = ""

        st.divider()
        
        # --- 步驟 2：項目視覺化勾選 ---
        st.subheader("📋 步驟 2：需要協助的項目 (可多選)")
        task_list = ["翻身", "換尿布", "倒尿/回報", "餵食", "NG feeding", "更換全套被服", "pre OP", "pre MRI"]
        
        selected_checkboxes = []
        # 分成三欄顯示，視覺更清晰
        check_cols = st.columns(3)
        for i, t_name in enumerate(task_list):
            with check_cols[i % 3]:
                if st.checkbox(t_name, key=f"chk_{t_name}"):
                    selected_checkboxes.append(t_name)
        
        col_other1, col_other2 = st.columns(2)
        with col_other1:
            other_input = st.text_input("其他協助 (自行輸入)")
        with col_other2:
            iv_input = st.text_input("IV車/醫材撥補 (填入車號)")

        st.divider()
        
        # --- 步驟 3：優先與送出 ---
        is_priority = st.toggle("⭐ 優先處理 (急件請開啟)", value=False)
        
        if st.button("🚀 送出呼叫 (Submit)", type="primary", use_container_width=True):
            final_items = selected_checkboxes.copy()
            if other_input: final_items.append(f"其他:{other_input}")
            if iv_input: final_items.append(f"撥補:{iv_input}")
            
            if not final_items:
                st.error("請至少選擇或輸入一個項目！")
            else:
                current_db = load_data()
                loc_str = f"{area}" + (f" - {bed}" if bed and bed != "(區域撥補/不需床號)" else " (全區/撥補)")
                new_task = {
                    "id": str(uuid.uuid4()),
                    "time_created": datetime.datetime.now().strftime("%H:%M:%S"),
                    "location": loc_str,
                    "items": "、".join(final_items),
                    "priority": is_priority,
                    "status": "待處理", 
                    "assigned_to": "",
                    "est_time": "",
                    "time_completed": ""
                }
                current_db["tasks"].append(new_task)
                save_data(current_db)
                st.success("任務已送出！")
                time.sleep(0.5)
                st.rerun()

    # --- 增加：任務取消按鈕 (護理端可取消誤點任務) ---
    st.divider()
    st.subheader("🗑️ 進行中任務管理 (可取消)")
    active_tasks = [t for t in db_data.get("tasks", []) if t["status"] in ["待處理", "執行中"]]
    if active_tasks:
        for t in active_tasks:
            with st.expander(f"【{t['status']}】{t['location']} - {t['items']}"):
                if st.button(f"❌ 取消此任務", key=f"cancel_nurse_{t['id']}"):
                    current_db = load_data()
                    # 改為狀態標記或直接移除，這裡採取直接標記為「已取消」
                    for item in current_db["tasks"]:
                        if item["id"] == t["id"]:
                            item["status"] = "已取消"
                            item["time_completed"] = datetime.datetime.now().strftime("%H:%M:%S")
                            break
                    save_data(current_db)
                    st.rerun()

# ==========================================
# 畫面二：護佐接收端
# ==========================================
elif role == "🧑‍⚕️ 護佐接收端":
    st.title("🧑‍⚕️ 接收端")
    
    if not st.session_state.current_user:
        with st.container(border=True):
            nickname = st.text_input("輸入綽號登入：")
            if st.button("登入"):
                if nickname:
                    st.session_state.current_user = nickname
                    current_db = load_data()
                    if nickname not in current_db.get("online_nas", []):
                        current_db.setdefault("online_nas", []).append(nickname)
                        save_data(current_db)
                    st.rerun()
    else:
        st.success(f"你好，{st.session_state.current_user}")
        if st.button("下線"):
            current_db = load_data()
            if st.session_state.current_user in current_db.get("online_nas", []):
                current_db["online_nas"].remove(st.session_state.current_user)
                save_data(current_db)
            st.session_state.current_user = None
            st.rerun()
        
        st.divider()
        # 小組長派發
        with st.expander("⚙️ 小組長管理夥伴狀態"):
            leader_na = st.text_input("夥伴綽號：")
            btn_on, btn_off = st.columns(2)
            if btn_on.button("協助上線"):
                current_db = load_data(); current_db.setdefault("online_nas", []).append(leader_na); save_data(current_db); st.rerun()
            if btn_off.button("協助下線"):
                current_db = load_data(); current_db["online_nas"].remove(leader_na); save_data(current_db); st.rerun()

        # 任務清單
        st.subheader("🔔 待接單")
        pending = [t for t in db_data.get("tasks", []) if t["status"] == "待處理"]
        pending.sort(key=lambda x: (not x["priority"], x["time_created"]))
        
        for t in pending:
            with st.container(border=True):
                col_t, col_b = st.columns([3, 1])
                with col_t:
                    st.error(f"⭐ [優先] {t['location']} - {t['items']}") if t["priority"] else st.write(f"{t['location']} - {t['items']}")
                with col_b:
                    est = st.selectbox("預估時間", ["5分", "10分", "15分"], key=f"est_{t['id']}")
                    if st.button("接單", key=f"get_{t['id']}", type="primary"):
                        current_db = load_data()
                        for item in current_db["tasks"]:
                            if item["id"] == t["id"]:
                                item["status"] = "執行中"; item["assigned_to"] = st.session_state.current_user; item["est_time"] = est
                        save_data(current_db); st.rerun()
                    # 護佐端也可以取消（例如點錯或口頭取消）
                    if st.button("取消", key=f"cancel_na_{t['id']}"):
                        current_db = load_data()
                        for item in current_db["tasks"]:
                            if item["id"] == t["id"]: item["status"] = "已取消"
                        save_data(current_db); st.rerun()

        st.divider()
        st.subheader("🟡 我的執行中任務")
        my_tasks = [t for t in db_data.get("tasks", []) if t["status"] == "執行中" and t["assigned_to"] == st.session_state.current_user]
        for t in my_tasks:
            with st.container(border=True):
                st.warning(f"{t['location']} - {t['items']} (預估:{t['est_time']})")
                if st.button("✅ 完成任務", key=f"done_{t['id']}"):
                    current_db = load_data()
                    for item in current_db["tasks"]:
                        if item["id"] == t["id"]:
                            item["status"] = "已完成"; item["time_completed"] = datetime.datetime.now().strftime("%H:%M:%S")
                    save_data(current_db); st.rerun()

# ==========================================
# 畫面三：急診動態看板
# ==========================================
elif role == "🖥️ 急診動態看板":
    st.title("🖥️ 即時看板")
    all_tasks = db_data.get("tasks", [])
    pending = [t for t in all_tasks if t["status"] == "待處理"]
    doing = [t for t in all_tasks if t["status"] == "執行中"]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 線上護佐", f"{len(db_data.get('online_nas', []))}人")
    col2.metric("🟡 執行中", f"{len(doing)}件")
    col3.metric("🔴 待處理", f"{len(pending)}件")
    
    st.divider()
    st.subheader("🏃 執行中動態")
    for t in doing:
        st.warning(f"🧑‍⚕️ **{t['assigned_to']}** 於 **{t['location']}**：{t['items']} (剩餘約 {t['est_time']})")
    
    st.divider()
    st.subheader("📋 待處理清單")
    pending.sort(key=lambda x: (not x["priority"], x["time_created"]))
    for t in pending:
        if t["priority"]:
            st.error(f"🚨 [急件] {t['location']} ➔ {t['items']} ({t['time_created']})")
        else:
            st.info(f"📍 {t['location']} ➔ {t['items']} ({t['time_created']})")

# ==========================================
# 畫面四：歷史紀錄 (包含已取消)
# ==========================================
elif role == "📊 歷史紀錄":
    st.title("📊 任務紀錄")
    df = pd.DataFrame(db_data.get("tasks", []))
    if not df.empty:
        st.dataframe(df[["time_created", "status", "location", "items", "assigned_to", "time_completed"]], use_container_width=True)
    else:
        st.write("尚無資料")

# --- 自動刷新 ---
if auto_refresh:
    time.sleep(10)
    st.rerun()
