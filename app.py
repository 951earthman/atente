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
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 每次網頁重整或操作時，讀取最新資料
db_data = load_data()

# --- 初始化個人設備記憶 (Session State) ---
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- 床位資料字典 ---
LOCATIONS = {
    "留觀(OBS)": {
        "OBS 1": ["1", "2", "3", "5", "6", "7", "8", "9", "10", "35", "36", "37", "38"],
        "OBS 2": ["11", "12", "13", "15", "16", "17", "18", "19", "20", "21", "22", "23"],
        "OBS 3": ["25", "26", "27", "28", "29", "30", "31", "32", "33", "39"]
    },
    "診間": {
        "第一診間": ["11", "12", "13", "15", "21", "22", "23", "25"],
        "第二診間": ["16", "17", "18", "19", "20", "36", "37", "38"],
        "第三診間": ["5", "6", "27", "28", "29", "30", "31", "32", "33", "39"]
    },
    "兒科": {
        "兒科區": ["501", "502", "503", "505", "506", "507", "508", "509"]
    },
    "急救區": {"無特定床號": ["急救區"]},
    "檢傷": {"無特定床號": ["檢傷"]},
    "縫合室": {"無特定床號": ["縫合室"]},
    "超音波室": {"無特定床號": ["超音波室"]}
}

# --- 側邊欄與同步按鈕 ---
st.sidebar.title("🏥 系統導覽")
role = st.sidebar.radio("請選擇您的角色介面：", [
    "👩‍⚕️ 護理人員派發端", 
    "🧑‍⚕️ 護佐接收端", 
    "🖥️ 急診動態看板 (觀察系統)", 
    "📊 後台任務紀錄"
])

st.sidebar.divider()
st.sidebar.caption("即時同步設定：")
default_refresh = True if role == "🖥️ 急診動態看板 (觀察系統)" else False
auto_refresh = st.sidebar.checkbox("🔄 開啟自動更新 (10秒刷新)", value=default_refresh)

if st.sidebar.button("👉 立即手動同步", type="primary", use_container_width=True):
    st.rerun()

# ==========================================
# 畫面一：護理人員派發端
# ==========================================
if role == "👩‍⚕️ 護理人員派發端":
    st.title("👩‍⚕️ 護佐任務派發")
    
    online_list = db_data.get("online_nas", [])
    # 單純顯示名單，將管理權限移交給護佐端
    st.info(f"🟢 目前線上護佐：{', '.join(online_list) if online_list else '目前無人上線'}")
    
    with st.container(border=True):
        st.subheader("📍 步驟 1：選擇位置")
        col1, col2, col3 = st.columns(3)
        with col1:
            main_area = st.selectbox("大區域", list(LOCATIONS.keys()))
        with col2:
            sub_area = st.selectbox("次區域/分區", list(LOCATIONS[main_area].keys()))
        with col3:
            bed = st.selectbox("床號", LOCATIONS[main_area][sub_area])
            
        st.divider()
        
        st.subheader("📋 步驟 2：需要協助的項目 (單選)")
        task_options = ["(無)", "翻身", "換尿布", "倒尿/回報", "餵食", "NG feeding", "更換全套被服", "pre OP", "pre MRI"]
        selected_task = st.selectbox("病人端照護", task_options)
        
        col4, col5 = st.columns(2)
        with col4:
            other_task = st.text_input("其他照護協助 (自行輸入)")
        with col5:
            iv_cart = st.text_input("區域後勤：第幾號 IV車輛/醫材需要撥補？")
            
        st.divider()
        
        st.subheader("🚨 步驟 3：急件設定")
        is_priority = st.checkbox("⭐ 優先處理 (打勾後此任務會置頂)")
        
        if st.button("🚀 送出呼叫 (Submit)", type="primary"):
            final_tasks = []
            if selected_task != "(無)": final_tasks.append(selected_task)
            if other_task: final_tasks.append(f"其他: {other_task}")
            if iv_cart: final_tasks.append(f"撥補: {iv_cart}")
            
            if not final_tasks:
                st.error("請至少選擇或輸入一項任務！")
            else:
                current_db = load_data()
                new_task = {
                    "id": str(uuid.uuid4()),
                    "time_created": datetime.datetime.now().strftime("%H:%M:%S"),
                    "location": f"{main_area} - {sub_area} {bed if bed not in ['急救區', '檢傷', '縫合室', '超音波室'] else ''}",
                    "items": ", ".join(final_tasks),
                    "priority": is_priority,
                    "status": "待處理", 
                    "assigned_to": "",
                    "est_time": "",
                    "time_completed": ""
                }
                current_db["tasks"].append(new_task)
                save_data(current_db)
                st.success("任務已成功送出！")
                time.sleep(1)
                st.rerun()

# ==========================================
# 畫面二：護佐接收端
# ==========================================
elif role == "🧑‍⚕️ 護佐接收端":
    st.title("🧑‍⚕️ 護佐任務看板")
    
    # 🌟 新增：小組長派發 (協助上下線管理)
    online_list_leader = db_data.get("online_nas", [])
    with st.expander("⚙️ 小組長派發 (協助夥伴上下線)"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("##### 🔴 協助下線")
            if not online_list_leader:
                st.write("目前無人上線")
            else:
                for na in online_list_leader:
                    if st.button(f"將「{na}」設為下線", key=f"offline_{na}"):
                        current_db = load_data()
                        if na in current_db.get("online_nas", []):
                            current_db["online_nas"].remove(na)
                            save_data(current_db)
                        st.rerun()
        with col_b:
            st.markdown("##### 🟢 協助上線")
            leader_na_name = st.text_input("輸入夥伴綽號：", key="leader_on_input")
            if st.button("設定為上線"):
                if leader_na_name:
                    current_db = load_data()
                    if leader_na_name not in current_db.get("online_nas", []):
                        current_db.setdefault("online_nas", []).append(leader_na_name)
                        save_data(current_db)
                    st.success(f"已協助 {leader_na_name} 上線！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("請先輸入綽號")
                    
    st.divider()
    
    if not st.session_state.current_user:
        with st.container(border=True):
            st.write("請輸入您的專屬綽號登入接單：")
            nickname = st.text_input("綽號 (例如：阿明)")
            if st.button("上線開始接單"):
                if nickname:
                    st.session_state.current_user = nickname
                    current_db = load_data()
                    if nickname not in current_db.get("online_nas", []):
                        current_db.setdefault("online_nas", []).append(nickname)
                        save_data(current_db)
                    st.rerun()
                else:
                    st.warning("請輸入綽號！")
    else:
        st.success(f"歡迎上線，{st.session_state.current_user}！")
        if st.button("本人下線"):
            current_db = load_data()
            if st.session_state.current_user in current_db.get("online_nas", []):
                current_db["online_nas"].remove(st.session_state.current_user)
                save_data(current_db)
            st.session_state.current_user = None
            st.rerun()
            
        st.divider()
        
        with st.expander("➕ 新增自辦任務 (定時撥補、口頭交辦等)"):
            self_task_type = st.selectbox("任務類型", ["定時醫材/IV撥補", "定時被服撥補", "接獲口頭交辦", "其他"])
            self_task_other = st.text_input("備註說明")
            self_est_time = st.selectbox("預估執行時間", ["5 分鐘", "10 分鐘", "15 分鐘", "30 分鐘"])
            if st.button("開始執行自辦任務"):
                current_db = load_data()
                new_task = {
                    "id": str(uuid.uuid4()),
                    "time_created": datetime.datetime.now().strftime("%H:%M:%S"),
                    "location": "自主任務",
                    "items": f"{self_task_type} - {self_task_other}",
                    "priority": False,
                    "status": "執行中",
                    "assigned_to": st.session_state.current_user,
                    "est_time": self_est_time,
                    "time_completed": ""
                }
                current_db["tasks"].append(new_task)
                save_data(current_db)
                st.success("自辦任務已登錄！")
                time.sleep(1)
                st.rerun()

        st.subheader("🔔 待處理任務")
        pending_tasks = [t for t in db_data.get("tasks", []) if t["status"] == "待處理"]
        pending_tasks.sort(key=lambda x: (not x["priority"], x["time_created"])) 
        
        if not pending_tasks:
            st.info("目前沒有待處理的任務。")
        else:
            for task in pending_tasks:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if task["priority"]:
                            st.error(f"⭐ [優先] 地點：{task['location']} | 任務：{task['items']} | 送出時間：{task['time_created']}")
                        else:
                            st.write(f"地點：{task['location']} | 任務：{task['items']} | 送出時間：{task['time_created']}")
                    with col2:
                        est = st.selectbox("預估時間", ["5 分鐘", "10 分鐘", "15 分鐘"], key=f"est_{task['id']}")
                        if st.button("點擊接單", key=f"btn_{task['id']}", type="primary"):
                            current_db = load_data()
                            for t in current_db["tasks"]:
                                if t["id"] == task["id"]:
                                    t["status"] = "執行中"
                                    t["assigned_to"] = st.session_state.current_user
                                    t["est_time"] = est
                                    break
                            save_data(current_db)
                            st.rerun()

        st.divider()
        st.subheader("🟡 我的執行中任務")
        my_tasks = [t for t in db_data.get("tasks", []) if t["status"] == "執行中" and t["assigned_to"] == st.session_state.current_user]
        
        if not my_tasks:
            st.write("目前無執行中任務，🟢 待命中。")
        else:
            for task in my_tasks:
                with st.container(border=True):
                    st.warning(f"地點：{task['location']} | 任務：{task['items']} | 預估：{task['est_time']}")
                    if st.button("✅ 任務完成", key=f"done_{task['id']}"):
                        current_db = load_data()
                        for t in current_db["tasks"]:
                            if t["id"] == task["id"]:
                                t["status"] = "已完成"
                                t["time_completed"] = datetime.datetime.now().strftime("%H:%M:%S")
                                break
                        save_data(current_db)
                        st.rerun()

# ==========================================
# 畫面三：急診動態看板 (觀察系統)
# ==========================================
elif role == "🖥️ 急診動態看板 (觀察系統)":
    st.title("🖥️ 急診護佐即時動態看板")
    st.info("💡 提示：左側欄的「自動更新」打勾後，此畫面會每 10 秒自動抓取最新動態。")
    
    all_tasks = db_data.get("tasks", [])
    pending_tasks = [t for t in all_tasks if t["status"] == "待處理"]
    doing_tasks = [t for t in all_tasks if t["status"] == "執行中"]
    online_nas = db_data.get("online_nas", [])

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 目前上線護佐", f"{len(online_nas)} 人")
    col2.metric("🟡 執行中任務", f"{len(doing_tasks)} 件")
    col3.metric("🔴 待處理任務", f"{len(pending_tasks)} 件")
    
    st.divider()
    
    st.subheader("🏃‍♂️ 護佐執行中動態")
    if not doing_tasks:
        st.write("目前大家都在待命，沒有執行中的任務。")
    else:
        for t in doing_tasks:
            st.warning(f"🧑‍⚕️ **【{t['assigned_to']}】** 正在 **{t['location']}** 執行：{t['items']}  ⏳ 預估時間：{t['est_time']} (任務發出於 {t['time_created']})")

    st.divider()

    st.subheader("📋 等待救援清單 (待處理)")
    pending_tasks.sort(key=lambda x: (not x["priority"], x["time_created"])) 
    if not pending_tasks:
        st.success("目前沒有積壓的任務，太棒了！")
    else:
        for t in pending_tasks:
            if t["priority"]:
                st.error(f"🚨 **[急件優先]** {t['location']} ➔ 需要：{t['items']} (等待中，發出時間：{t['time_created']})")
            else:
                st.info(f"📍 {t['location']} ➔ 需要：{t['items']} (等待中，發出時間：{t['time_created']})")

# ==========================================
# 畫面四：後台任務紀錄
# ==========================================
elif role == "📊 後台任務紀錄":
    st.title("📊 任務執行紀錄與統計")
    all_tasks = db_data.get("tasks", [])
    if not all_tasks:
        st.write("目前尚無任何任務紀錄。")
    else:
        df = pd.DataFrame(all_tasks)
        df = df[["time_created", "status", "priority", "location", "items", "assigned_to", "est_time", "time_completed", "id"]]
        st.dataframe(df, use_container_width=True)

# ==========================================
# 自動刷新邏輯
# ==========================================
if auto_refresh:
    time.sleep(10)
    st.rerun()
