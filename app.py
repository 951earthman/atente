import streamlit as st
import datetime
import pandas as pd

# --- 設定頁面 ---
st.set_page_config(page_title="急診護佐任務系統", page_icon="🏥", layout="wide")

# --- 初始化資料儲存 (Session State) ---
# 注意：Streamlit 的 session_state 預設只在單一瀏覽器分頁有效。
# 若要跨設備即時連動（護理站電腦與護佐手機），後續需加入資料庫（如 Firebase 或 Google Sheets）。
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'online_nas' not in st.session_state:
    st.session_state.online_nas = []
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

# --- 側邊欄：角色切換 ---
st.sidebar.title("🏥 系統導覽")
role = st.sidebar.radio("請選擇您的角色介面：", ["👩‍⚕️ 護理人員派發端", "🧑‍⚕️ 護佐接收端", "📊 後台任務紀錄"])

# ==========================================
# 畫面一：護理人員派發端
# ==========================================
if role == "👩‍⚕️ 護理人員派發端":
    st.title("👩‍⚕️ 護佐任務派發")
    
    # 顯示護佐動態
    st.info(f"🟢 目前線上護佐：{', '.join(st.session_state.online_nas) if st.session_state.online_nas else '目前無人上線'}")
    
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
        
        st.subheader("📋 步驟 2：需要協助的項目 (可複選)")
        task_options = ["翻身", "換尿布", "倒尿/回報", "餵食", "NG feeding", "更換全套被服", "pre OP", "pre MRI"]
        selected_tasks = st.multiselect("病人端照護", task_options)
        
        col4, col5 = st.columns(2)
        with col4:
            other_task = st.text_input("其他照護協助 (自行輸入)")
        with col5:
            iv_cart = st.text_input("區域後勤：第幾號 IV車輛/醫材需要撥補？")
            
        st.divider()
        
        st.subheader("🚨 步驟 3：急件設定")
        is_priority = st.checkbox("⭐ 優先處理 (打勾後此任務會置頂)")
        
        # 送出按鈕
        if st.button("🚀 送出呼叫 (Submit)", type="primary"):
            final_tasks = selected_tasks.copy()
            if other_task: final_tasks.append(f"其他: {other_task}")
            if iv_cart: final_tasks.append(f"撥補: {iv_cart}")
            
            if not final_tasks:
                st.error("請至少選擇或輸入一項任務！")
            else:
                new_task = {
                    "id": len(st.session_state.tasks) + 1,
                    "time_created": datetime.datetime.now().strftime("%H:%M:%S"),
                    "location": f"{main_area} - {sub_area} {bed if bed not in ['急救區', '檢傷', '縫合室', '超音波室'] else ''}",
                    "items": ", ".join(final_tasks),
                    "priority": is_priority,
                    "status": "待處理", # 狀態：待處理, 執行中, 已完成
                    "assigned_to": "",
                    "est_time": "",
                    "time_completed": ""
                }
                st.session_state.tasks.append(new_task)
                st.success("任務已成功送出！")

# ==========================================
# 畫面二：護佐接收端
# ==========================================
elif role == "🧑‍⚕️ 護佐接收端":
    st.title("🧑‍⚕️ 護佐任務看板")
    
    # 登入機制 (綽號)
    if not st.session_state.current_user:
        with st.container(border=True):
            st.write("請輸入您的專屬綽號上線接單：")
            nickname = st.text_input("綽號 (例如：阿明)")
            if st.button("上線開始接單"):
                if nickname:
                    st.session_state.current_user = nickname
                    if nickname not in st.session_state.online_nas:
                        st.session_state.online_nas.append(nickname)
                    st.rerun()
                else:
                    st.warning("請輸入綽號！")
    else:
        st.success(f"歡迎上線，{st.session_state.current_user}！")
        if st.button("下線"):
            st.session_state.online_nas.remove(st.session_state.current_user)
            st.session_state.current_user = None
            st.rerun()
            
        st.divider()
        
        # 新增自辦任務
        with st.expander("➕ 新增自辦任務 (定時撥補、口頭交辦等)"):
            self_task_type = st.selectbox("任務類型", ["定時醫材/IV撥補", "定時被服撥補", "接獲口頭交辦", "其他"])
            self_task_other = st.text_input("備註說明")
            self_est_time = st.selectbox("預估執行時間", ["5 分鐘", "10 分鐘", "15 分鐘", "30 分鐘"])
            if st.button("開始執行自辦任務"):
                new_task = {
                    "id": len(st.session_state.tasks) + 1,
                    "time_created": datetime.datetime.now().strftime("%H:%M:%S"),
                    "location": "自主任務",
                    "items": f"{self_task_type} - {self_task_other}",
                    "priority": False,
                    "status": "執行中",
                    "assigned_to": st.session_state.current_user,
                    "est_time": self_est_time,
                    "time_completed": ""
                }
                st.session_state.tasks.append(new_task)
                st.success("自辦任務已登錄！")
                st.rerun()

        st.subheader("🔔 待處理任務")
        # 篩選待處理任務，並將優先任務排在前面
        pending_tasks = [t for t in st.session_state.tasks if t["status"] == "待處理"]
        pending_tasks.sort(key=lambda x: (not x["priority"], x["id"])) 
        
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
                            task["status"] = "執行中"
                            task["assigned_to"] = st.session_state.current_user
                            task["est_time"] = est
                            st.rerun()

        st.divider()
        st.subheader("🟡 我的執行中任務")
        my_tasks = [t for t in st.session_state.tasks if t["status"] == "執行中" and t["assigned_to"] == st.session_state.current_user]
        
        if not my_tasks:
            st.write("目前無執行中任務，🟢 待命中。")
        else:
            for task in my_tasks:
                with st.container(border=True):
                    st.warning(f"地點：{task['location']} | 任務：{task['items']} | 預估：{task['est_time']}")
                    if st.button("✅ 任務完成", key=f"done_{task['id']}"):
                        task["status"] = "已完成"
                        task["time_completed"] = datetime.datetime.now().strftime("%H:%M:%S")
                        st.rerun()

# ==========================================
# 畫面三：後台任務紀錄
# ==========================================
elif role == "📊 後台任務紀錄":
    st.title("📊 任務執行紀錄與統計")
    if not st.session_state.tasks:
        st.write("目前尚無任何任務紀錄。")
    else:
        df = pd.DataFrame(st.session_state.tasks)
        st.dataframe(df, use_container_width=True)
