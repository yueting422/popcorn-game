# main.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from passlib.hash import pbkdf2_sha256 # 用於密碼雜湊與驗證

# 引入遊戲模組
import flash_card

# --- 網頁基礎設定 ---
st.set_page_config(page_title="爆米花遊樂場", page_icon="🍿", layout="wide")

# --- Firebase 初始化 ---
try:
    # 檢查 st.session_state 中是否已存在 db 物件，避免重複初始化
    if 'db' not in st.session_state:
        # 從 Streamlit Secrets 讀取憑證，這是部署的標準做法
        creds_dict = {
            "type": st.secrets["firebase_credentials"]["type"],
            "project_id": st.secrets["firebase_credentials"]["project_id"],
            "private_key_id": st.secrets["firebase_credentials"]["private_key_id"],
            "private_key": st.secrets["firebase_credentials"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["firebase_credentials"]["client_email"],
            "client_id": st.secrets["firebase_credentials"]["client_id"],
            "auth_uri": st.secrets["firebase_credentials"]["auth_uri"],
            "token_uri": st.secrets["firebase_credentials"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase_credentials"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase_credentials"]["client_x509_cert_url"],
        }
        cred = credentials.Certificate(creds_dict)
        # 檢查 Firebase app 是否已經初始化
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        # 將 db client 存入 session_state
        st.session_state['db'] = firestore.client()
except Exception as e:
    st.error("Firebase 初始化失敗，請檢查 Streamlit Secrets 中的金鑰設定。")
    st.error(e)
    # 如果初始化失敗，則停止應用程式執行
    st.stop()

# 從 session_state 中取得 db client
db = st.session_state['db']

# --- 登入與註冊邏輯 (來自 app.py) ---
def show_login_register_page():
    st.title("🍿 歡迎來到爆米花遊樂場")
    login_tab, register_tab = st.tabs(["登入 (Login)", "註冊 (Register)"])
    
    with login_tab:
        st.subheader("會員登入")
        with st.form("login_form"):
            username = st.text_input("使用者名稱", key="login_user").lower()
            password = st.text_input("密碼", type="password", key="login_pass")
            login_submitted = st.form_submit_button("登入")
            
            if login_submitted:
                if not username or not password:
                    st.error("使用者名稱和密碼不可為空！")
                else:
                    user_ref = db.collection('users').document(username).get()
                    if not user_ref.exists:
                        st.error("使用者不存在！")
                    else:
                        user_data = user_ref.to_dict()
                        # 驗證雜湊後的密碼
                        if pbkdf2_sha256.verify(password, user_data.get('password_hash', '')):
                            st.session_state['authentication_status'] = True
                            st.session_state['username'] = username
                            st.session_state['name'] = user_data.get('name', username)
                            st.session_state['popcorn'] = user_data.get('popcorn', 0) # 登入時讀取爆米花數量
                            st.rerun()
                        else:
                            st.error("密碼不正確！")

    with register_tab:
        st.subheader("建立新帳號")
        with st.form("register_form"):
            new_name = st.text_input("您的暱稱", key="reg_name")
            new_username = st.text_input("設定使用者名稱 (僅限英文和數字)", key="reg_user").lower()
            new_password = st.text_input("設定密碼", type="password", key="reg_pass")
            confirm_password = st.text_input("確認密碼", type="password", key="reg_confirm")
            register_submitted = st.form_submit_button("註冊")

            if register_submitted:
                if not all([new_name, new_username, new_password, confirm_password]):
                    st.error("所有欄位都必須填寫！")
                elif new_password != confirm_password:
                    st.error("兩次輸入的密碼不一致！")
                elif not new_username.isalnum():
                    st.error("使用者名稱只能包含英文和數字！")
                else:
                    user_ref = db.collection('users').document(new_username)
                    if user_ref.get().exists:
                        st.error("此使用者名稱已被註冊！")
                    else:
                        # 將密碼進行雜湊加密
                        password_hash = pbkdf2_sha256.hash(new_password)
                        # 建立使用者資料，並給予初始 100 爆米花
                        user_data = {
                            "name": new_name, 
                            "password_hash": password_hash,
                            "popcorn": 100
                        }
                        user_ref.set(user_data)
                        st.success("註冊成功！請前往登入分頁進行登入。")

# --- 主應用程式邏輯 ---
def main_app():
    # 將歡迎訊息和登出按鈕放在側邊欄
    st.sidebar.title(f"歡迎, {st.session_state['name']}!")
    st.sidebar.write(f"您目前擁有 {st.session_state.get('popcorn', 0)} 🍿")
    if st.sidebar.button("登出"):
        # 清空 session state 以登出
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.sidebar.markdown("---")

    # 遊戲頁面導航
    if 'page' not in st.session_state:
        st.session_state.page = "主頁"
        
    if st.session_state.page == "主頁":
        st.title("🕹️ 遊戲大廳")
        st.write("選擇一個你想玩的遊戲！")
        if st.button("🧠 記憶翻翻樂"):
            st.session_state.page = "翻翻樂"
            st.rerun()
        if st.button("⚖️ 比大小 (尚未開放)"):
            st.info("此遊戲正在開發中，敬請期待！")

    elif st.session_state.page == "翻翻樂":
        # 呼叫 flash_card 模組中的函式來玩遊戲
        # 將 username 傳遞給遊戲，以便更新分數
        update_popcorn_func = lambda username, amount: db.collection('users').document(username).update({'popcorn': firestore.Increment(amount)})
        flash_card.start_game(st.session_state['username'], update_popcorn_in_db)


def update_popcorn_in_db(username, amount):
    """更新資料庫中的爆米花數量"""
    try:
        user_ref = db.collection('users').document(username)
        user_ref.update({'popcorn': firestore.Increment(amount)})
        st.session_state.popcorn += amount # 同時更新 session_state
        return True
    except Exception as e:
        st.error(f"更新爆米花失敗: {e}")
        return False

# --- 程式進入點 ---
# 檢查 session_state 中是否已定義 'authentication_status'
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# 根據登入狀態顯示不同頁面
if st.session_state.get('authentication_status'):
    main_app()
else:
    show_login_register_page()