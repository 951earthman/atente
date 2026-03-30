import streamlit as st
import datetime
import pandas as pd
import json
import os
import uuid
import time
import streamlit.components.v1 as components

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
    st.session_state.current_user = None # 護佐用
if 'current_nurse' not in st.session_state:
    st.session_state.current_nurse = None # 護理師用
if 'alerted_tasks' not in st.session_state:
    st.session_state.alerted_tasks = set()

# --- 床位資料 ---
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
auto_refresh = st.sidebar.checkbox("🔄 開啟自動更新 (10秒)", value=(role == "🖥️ 急診動態看板" or role == "🧑‍⚕️ 護佐接收端"))
if st.sidebar.button("👉 立即手動同步", type="primary", use_container_width=True):
    st.rerun()

# ==========================================
# 畫面一：護理人員派發端
# ==========================================
if role == "👩‍⚕️ 護理人員派發端":
    st.title("👩‍⚕️ 任務派發")
    
    # 🌟 新增：護理人員登入機制
    if not st.session_state.current_nurse:
        with st.container(border=True):
            st.info("💡 首次使用請先輸入綽號，方便護佐執行完畢後向您回報。")
            nurse_name = st.text_input("輸入您的綽號 (例如：小莉、A段護理師)：")
            if st.button("開始派發任務", type="primary"):
                if nurse_name:
                    st.session_state.current_nurse = nurse_name
                    st.rerun()
                else:
                    st.warning("請先輸入綽號！")
    else:
        # 已登入的派發畫面
        col_greet, col_logout = st.columns([4, 1])
        with col_greet:
            st.success(f"你好，護理師 {st.session_state.current_nurse}")
        with col_logout:
            if st.button("登出更換人員"):
                st.session_state.current_nurse = None
                st.rerun()

        online_list = db_data.get("online_nas", [])
        st.info(f"🟢 目前線上護佐：{', '.join(online_list) if online_list else '無人上線'}")
        
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
            
            st.subheader("📋 步驟 2：需要協助的項目 (可多選)")
            task_list = ["翻身", "換尿布", "倒尿/回報", "餵食", "NG feeding", "更換全套被服", "pre OP", "pre MRI"]
            
            selected_checkboxes = []
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
                        "time_completed": "",
                        "dispatched_by": st.session_state.current_nurse # 🌟 紀錄是誰發的單
                    }
                    current_db["tasks"].append(new_task)
                    save_data(current_db)
                    st.success("任務已送出！")
                    time.sleep(0.5)
                    st.rerun()

        st.divider()
        st.subheader("🗑️ 進行中任務管理 (可取消)")
        active_tasks = [t for t in db_data.get("tasks", []) if t["status"] in ["待處理", "執行中"]]
        if active_tasks:
            for t in active_tasks:
                with st.expander(f"【{t['status']}】{t['location']} - {t['items']}"):
                    if st.button(f"❌ 取消此任務", key=f"cancel_nurse_{t['id']}"):
                        current_db = load_data()
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
        if st.button("本人下線"):
            current_db = load_data()
            if st.session_state.current_user in current_db.get("online_nas", []):
                current_db["online_nas"].remove(st.session_state.current_user)
                save_data(current_db)
            st.session_state.current_user = None
            st.rerun()
        
        st.divider()
        
        # 🌟 修改：小組長協助下線 (改成下拉選單防呆，且拿掉協助上線)
        with st.expander("⚙️ 小組長協助夥伴下線"):
            online_nas_list = db_data.get("online_nas", [])
            if online_nas_list:
                col_sel, col_btn = st.columns([3, 1])
                with col_sel:
                    target_na = st.selectbox("選擇忘記登出的夥伴：", online_nas_list)
                with col_btn:
                    st.write("\n") # 排版對齊用
                    if st.button("強制下線"):
                        current_db = load_data()
                        if target_na in current_db.get("online_nas", []):
                            current_db["online_nas"].remove(target_na)
                            save_data(current_db)
                        st.success(f"已將 {target_na} 下線")
                        time.sleep(0.5)
                        st.rerun()
            else:
                st.write("目前無夥伴在線上。")

        # 優先任務警報系統邏輯
        pending = [t for t in db_data.get("tasks", []) if t["status"] == "待處理"]
        pending.sort(key=lambda x: (not x["priority"], x["time_created"]))
        
        new_priority_found = False
        for t in pending:
            if t["priority"] and t["id"] not in st.session_state.alerted_tasks:
                st.toast(f"🚨 優先任務：{t['location']} 需要協助！", icon="🚨")
                st.session_state.alerted_tasks.add(t["id"])
                new_priority_found = True
        
        if new_priority_found:
            audio_js = """
            <script>
                if (navigator.vibrate) { navigator.vibrate([500, 200, 500, 200, 500]); }
                var audio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
                audio.play().catch(function(e) { console.log("音效遭瀏覽器阻擋"); });
            </script>
            """
            components.html(audio_js, height=0)

        # 任務清單顯示 (🌟 加上發單人資訊)
        st.subheader("🔔 待接單")
        if not pending:
            st.info("目前無待處理任務。")
        for t in pending:
            with st.container(border=True):
                col_t, col_b = st.columns([3, 1])
                with col_t:
                    dispatch_info = f" (發單：{t.get('dispatched_by', '未紀錄')})"
                    if t["priority"]:
                        st.error(f"⭐ [優先] {t['location']} - {t['items']}{dispatch_info}")
                    else:
                        st.write(f"{t['location']} - {t['items']}{dispatch_info}")
                with col_b:
                    est = st.selectbox("預估時間", ["5分", "10分", "15分"], key=f"est_{t['id']}")
                    if st.button("接單", key=f"get_{t['id']}", type="primary"):
                        current_db = load_data()
                        for item in current_db["tasks"]:
                            if item["id"] == t["id"]:
                                item["status"] = "執行中"; item["assigned_to"] = st.session_state.current_user; item["est_time"] = est
                        save_data(current_db); st.rerun()
                    if st.button("取消", key=f"cancel_na_{t['id']}"):
                        current_db = load_data()
                        for item in current_db["tasks"]:
                            if item["id"] == t["id"]: item["status"] = "已取消"
                        save_data(current_db); st.rerun()

        st.divider()
        st.subheader("🟡 我的執行中任務")
        my_tasks = [t for t in db_data.get("tasks", []) if t["status"] == "執行中" and t["assigned_to"] == st.session_state.current_user]
        if not my_tasks:
            st.write("目前無執行中任務。")
        for t in my_tasks:
            with st.container(border=True):
                dispatch_info = f" (發單：{t.get('dispatched_by', '未紀錄')})"
                st.warning(f"{t['location']} - {t['items']}{dispatch_info} / 預估:{t['est_time']}")
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
        st.warning(f"🧑‍⚕️ **{t['assigned_to']}** 於 **{t['location']}**：{t['items']} (發單:{t.get('dispatched_by', '未紀錄')} / 剩餘約 {t['est_time']})")
    
    st.divider()
    st.subheader("📋 待處理清單")
    pending.sort(key=lambda x: (not x["priority"], x["time_created"]))
    for t in pending:
        if t["priority"]:
            st.error(f"🚨 [急件] {t['location']} ➔ {t['items']} (發單:{t.get('dispatched_by', '未紀錄')} / {t['time_created']})")
        else:
            st.info(f"📍 {t['location']} ➔ {t['items']} (發單:{t.get('dispatched_by', '未紀錄')} / {t['time_created']})")

# ==========================================
# 畫面四：歷史紀錄
# ==========================================
elif role == "📊 歷史紀錄":
    st.title("📊 任務紀錄")
    df = pd.DataFrame(db_data.get("tasks", []))
    if not df.empty:
        # 🌟 將發單人 (dispatched_by) 也加入報表
        cols_to_show = ["time_created", "status", "dispatched_by", "location", "items", "assigned_to", "time_completed"]
        # 確保即使舊資料沒有 dispatched_by 欄位也不會報錯
        for col in cols_to_show:
            if col not in df.columns:
                df[col] = "未紀錄"
                
        st.dataframe(df[cols_to_show], use_container_width=True)
    else:
        st.write("尚無資料")

# --- 自動刷新 ---
if auto_refresh:
    time.sleep(10)
    st.rerun()
