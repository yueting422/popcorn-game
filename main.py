# main.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
# import json  <-- 這個版本不再需要 json 函式庫

# 引入遊戲模組
import flash_card

# -------------------- Firebase 初始化 --------------------
# 檢查是否已經初始化，避免重複初始化
if not firebase_admin._apps:
    try:
        # --- 修改開始 (為了配合您的 Secrets 設定) ---
        # 直接讀取您在 Secrets 中設定的 [firebase_credentials] 區塊。
        # Streamlit 會自動將其解析為一個字典 (dictionary)。
        cred = credentials.Certificate(st.secrets["firebase_credentials"])
        # --- 修改結束 ---
        
        firebase_admin.initialize_app(cred)
    except KeyError:
        # 如果在本機測試且沒有設定 secrets，可以提示使用者檢查金鑰檔案
        st.warning("找不到 Streamlit Secrets 中的 'firebase_credentials'。正在嘗試使用本地 firebase_key.json 檔案。")
        try:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        except FileNotFoundError:
            st.error("在本機和 Streamlit Secrets 中都找不到 Firebase 金鑰！請確認 firebase_key.json 存在或已設定 Secrets。")
            st.stop()
    except Exception as e:
        st.error(f"Firebase 初始化失敗: {e}")
        st.stop()

db = firestore.client()

# -------------------- Session State 初始化 --------------------
# 用 st.session_state 來儲存使用者的登入狀態和資訊
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.session_state.popcorn = 0
    st.session_state.page = "主頁" # 用於頁面導航

# -------------------- 函式定義 --------------------

def update_popcorn_in_db(email, amount):
    """更新資料庫中的爆米花數量"""
    try:
        user_ref = db.collection('users').document(email)
        # 使用 Increment 來安全地增加數值
        user_ref.update({'popcorn': firestore.Increment(amount)})
        st.session_state.popcorn += amount # 同時更新 session_state
        return True
    except Exception as e:
        st.error(f"更新爆米花失敗: {e}")
        return False

# -------------------- UI 介面 --------------------

# 將登入/註冊/登出介面放在側邊欄
st.sidebar.title("🍿 爆米花遊樂場")

if not st.session_state.logged_in:
    # --- 登入/註冊選擇 ---
    auth_choice = st.sidebar.radio("導航", ["登入", "註冊"])

    if auth_choice == "登入":
        st.sidebar.subheader("會員登入")
        with st.sidebar.form("login_form"):
            email = st.text_input("信箱")
            password = st.text_input("密碼", type="password")
            login_button = st.form_submit_button("登入")

            if login_button:
                if email and password:
                    try:
                        user_ref = db.collection('users').document(email).get()
                        if user_ref.exists:
                            user_data = user_ref.to_dict()
                            if user_data.get('password') == password:
                                st.session_state.logged_in = True
                                st.session_state.user_email = email
                                st.session_state.popcorn = user_data.get('popcorn', 0)
                                st.session_state.page = "主頁"
                                st.rerun()
                            else:
                                st.sidebar.error("密碼錯誤！")
                        else:
                            st.sidebar.error("此帳號不存在！")
                    except Exception as e:
                        st.sidebar.error(f"登入失敗: {e}")
                else:
                    st.sidebar.warning("請輸入信箱和密碼。")

    elif auth_choice == "註冊":
        st.sidebar.subheader("建立新帳號")
        with st.sidebar.form("register_form"):
            new_email = st.text_input("信箱")
            new_password = st.text_input("密碼", type="password")
            confirm_password = st.text_input("確認密碼", type="password")
            register_button = st.form_submit_button("註冊")

            if register_button:
                if new_email and new_password and confirm_password:
                    if new_password == confirm_password:
                        try:
                            user_ref = db.collection('users').document(new_email)
                            if not user_ref.get().exists:
                                # 註冊送100爆米花
                                user_data = {'password': new_password, 'popcorn': 100}
                                user_ref.set(user_data)
                                st.sidebar.success("註冊成功！請前往登入頁面。")
                            else:
                                st.sidebar.error("此信箱已被註冊！")
                        except Exception as e:
                            st.sidebar.error(f"註冊失敗: {e}")
                    else:
                        st.sidebar.error("兩次輸入的密碼不一致！")
                else:
                    st.sidebar.warning("所有欄位皆為必填。")

else: # 如果已登入
    st.sidebar.success(f"歡迎, {st.session_state.user_email}!")
    st.sidebar.write(f"您目前擁有 {st.session_state.popcorn} 🍿")

    if st.sidebar.button("登出"):
        # 清空 session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# -------------------- 主畫面內容 --------------------

if not st.session_state.logged_in:
    st.title("歡迎來到爆米花遊樂場")
    st.write("請從左方側邊欄登入或註冊以開始遊戲。")

else: # 已登入後的主畫面
    # --- 頁面導航 ---
    if st.session_state.page == "主頁":
        st.title("遊戲大廳")
        st.write("選擇一個你想玩的遊戲！")
        if st.button("🧠 記憶翻翻樂"):
            st.session_state.page = "翻翻樂"
            st.rerun()
        if st.button("⚖️ 比大小 (尚未開放)"):
            st.info("此遊戲正在開發中，敬請期待！")

    elif st.session_state.page == "翻翻樂":
        # 呼叫 flash_card 模組中的函式來玩遊戲
        flash_card.start_game(st.session_state.user_email, update_popcorn_in_db)