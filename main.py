# main.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from passlib.hash import pbkdf2_sha256
import time

# 引入遊戲模組
import flash_card
import more_less
import gacha # <-- 新增：引入抽卡遊戲

# --- 網頁基礎設定 ---
st.set_page_config(page_title="爆米花遊樂場", page_icon="🍿", layout="wide")

# --- Firebase 初始化 ---
try:
    if 'db' not in st.session_state:
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
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        st.session_state['db'] = firestore.client()
except Exception as e:
    st.error("Firebase 初始化失敗，請檢查 Streamlit Secrets 中的金鑰設定。")
    st.error(e)
    st.stop()

db = st.session_state['db']

# --- 登入與註冊邏輯 ---
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
                        if pbkdf2_sha256.verify(password, user_data.get('password_hash', '')):
                            st.session_state['authentication_status'] = True
                            st.session_state['username'] = username
                            st.session_state['name'] = user_data.get('name', username)
                            st.session_state['popcorn'] = user_data.get('popcorn', 0)
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
                        password_hash = pbkdf2_sha256.hash(new_password)
                        user_data = {
                            "name": new_name, 
                            "password_hash": password_hash,
                            "popcorn": 100
                        }
                        user_ref.set(user_data)
                        st.success("註冊成功！請前往登入分頁進行登入。")

# --- 刪除帳號後端邏輯 ---
def delete_user_account():
    username = st.session_state['username']
    
    password = st.session_state.get("delete_password", "")
    confirmation = st.session_state.get("delete_confirm", "")

    user_ref = db.collection('users').document(username).get()
    if not user_ref.exists:
        st.sidebar.error("找不到使用者資料。")
        return

    user_data = user_ref.to_dict()

    if not pbkdf2_sha256.verify(password, user_data.get('password_hash', '')):
        st.sidebar.error("密碼不正確！無法刪除帳號。")
        return
    
    if confirmation.strip().upper() != 'DELETE':
        st.sidebar.error("確認文字不符，請輸入 'DELETE'。")
        return

    try:
        # 刪除 Firestore 中的卡片子集合 (如果存在)
        cards_ref = db.collection('users').document(username).collection('cards')
        for doc in cards_ref.stream():
            doc.reference.delete()
        
        # 刪除使用者主文件
        db.collection('users').document(username).delete()
        
        st.success("您的帳號與所有資料已成功刪除。")
        time.sleep(2)
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"刪除時發生錯誤: {e}")


# --- 主應用程式邏輯 ---
def main_app():
    st.sidebar.title(f"歡迎, {st.session_state['name']}!")
    st.sidebar.write(f"您目前擁有 {st.session_state.get('popcorn', 0)} 🍿")
    if st.sidebar.button("登出"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.sidebar.markdown("---")
    
    with st.sidebar.expander("⚙️ 帳號管理"):
        st.warning("注意：刪除帳號將會永久移除您的所有資料，此操作無法復原。")
        st.text_input("請輸入您的密碼以進行驗證", type="password", key="delete_password")
        st.text_input("請輸入 'DELETE' 以確認刪除", key="delete_confirm")
        st.button("永久刪除我的帳號", on_click=delete_user_account, type="primary")

    st.sidebar.markdown("---")

    st.sidebar.caption("圖源皆來自微博 : 小姚宋敏")
    st.sidebar.caption("程式開發者 : 玥庭(IG : lyw._.sxh)")

    if 'page' not in st.session_state:
        st.session_state.page = "主頁"
        
    if st.session_state.page == "主頁":
        st.title("🕹️ 遊戲大廳")
        st.write("選擇一個你想玩的遊戲！")
        if st.button("🧠 記憶翻翻樂"):
            st.session_state.page = "翻翻樂"
            st.rerun()
            
        if st.button("⚖️ 比大小"):
            st.session_state.page = "比大小"
            st.rerun()

        # --- 新增：抽卡遊戲按鈕 ---
        if st.button("🎰 抽卡遊戲"):
            st.session_state.page = "抽卡"
            st.rerun()

    elif st.session_state.page == "翻翻樂":
        flash_card.start_game(st.session_state['username'], update_popcorn_in_db)
    
    elif st.session_state.page == "比大小":
        more_less.start_game(st.session_state['username'], update_popcorn_in_db)

    # --- 新增：導航到抽卡遊戲 ---
    elif st.session_state.page == "抽卡":
        gacha.start_game(st.session_state['username'], update_popcorn_in_db)


def update_popcorn_in_db(username, amount):
    """更新資料庫中的爆米花數量"""
    try:
        user_ref = db.collection('users').document(username)
        user_ref.update({'popcorn': firestore.Increment(amount)})
        st.session_state.popcorn = st.session_state.get('popcorn', 0) + amount
        return True
    except Exception as e:
        st.error(f"更新爆米花失敗: {e}")
        return False

# --- 程式進入點 ---
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

if st.session_state.get('authentication_status'):
    main_app()
else:
    show_login_register_page()