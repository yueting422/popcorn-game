# flash_card.py
import streamlit as st
import random
import time
import os
import base64
from pathlib import Path

# (image_to_base64 函式維持不變)
@st.cache_data
def image_to_base64(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        st.error(f"找不到圖片檔案：{image_path}")
        return ""
    with open(path, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    mime_type = "image/jpeg" if path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
    return f"data:{mime_type};base64,{b64_string}"

def start_game(user_email, db_update_func):
    st.title("🧠 記憶翻翻樂")

    if 'game_started' not in st.session_state or not st.session_state.game_started:
        initialize_game()

    # --- 【核心修改】使用 st.query_params 處理點擊事件 ---
    # 這是最穩定的方法，可以精準捕捉使用者的點擊
    params = st.query_params
    if "card_click" in params:
        clicked_index = int(params["card_click"])
        # 使用 st.query_params.clear() 來清除參數，避免重複觸發
        st.query_params.clear()
        handle_card_click(clicked_index)
        st.rerun()

    if st.session_state.get('mistake_timer') and time.time() - st.session_state.mistake_timer > 0.5:
        if len(st.session_state.flipped_indices) == 2:
            idx1, idx2 = st.session_state.flipped_indices
            if st.session_state.card_status[idx1] != 'matched': st.session_state.card_status[idx1] = 'hidden'
            if st.session_state.card_status[idx2] != 'matched': st.session_state.card_status[idx2] = 'hidden'
            st.session_state.flipped_indices = []
        st.session_state.mistake_timer = None
        st.rerun()

    if st.session_state.get('game_over', False):
        st.success(f"時間到！你成功配對了 {st.session_state.matched_pairs} 組！")
        st.info(f"你獲得了 {st.session_state.matched_pairs} 個爆米花 🍿")
        if not st.session_state.get('reward_claimed', False):
            if db_update_func(user_email, st.session_state.matched_pairs):
                st.session_state.reward_claimed = True
                st.balloons()
        if st.button("返回大廳"):
            st.session_state.page = "主頁"
            reset_game_state()
            st.rerun()
        return

    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, 60 - int(elapsed_time))
    
    col1, col2 = st.columns(2)
    col1.metric(label="剩餘時間", value=f"{remaining_time} 秒")
    col2.metric(label="已配對", value=f"{st.session_state.matched_pairs} 組")

    if remaining_time <= 0 and not st.session_state.get('mistake_timer'):
        st.session_state.game_over = True
        st.rerun()

    st.markdown("---")

    image_folder = os.path.join("image", "flash_card")
    card_back_image_path = os.path.join(image_folder, "卡背.jpg")

    cols = st.columns(6)
    for i, card_value in enumerate(st.session_state.game_board):
        col = cols[i % 6]
        with col:
            card_status = st.session_state.card_status[i]
            
            if card_status in ['flipped', 'matched']:
                image_name = f"{card_value}.jpg"
                current_image_path = os.path.join(image_folder, image_name)
            else:
                current_image_path = card_back_image_path
            
            b64_image = image_to_base64(current_image_path)
            
            # --- 【核心修改】使用 st.markdown 和 HTML/CSS 建立可點擊的圖片 ---
            if b64_image:
                # 只有覆蓋的牌才能點擊
                if card_status == 'hidden':
                    html_code = f'''
                        <a href="?card_click={i}" target="_self" style="text-decoration: none;">
                            <img src="{b64_image}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 10px; border: 2px solid #eee;">
                        </a>
                    '''
                else: # 翻開的牌不能點擊
                    html_code = f'''
                        <div style="width: 100%; height: 150px;">
                            <img src="{b64_image}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 10px;">
                        </div>
                    '''
                st.markdown(html_code, unsafe_allow_html=True)

# (initialize_game, handle_card_click, reset_game_state 函式與前一版相同)
def initialize_game():
    base_cards = [
        "12", "13", "14", "15", "16", "17", "23", "24", "25", "26", "27",
        "34", "35", "36", "37", "45", "46", "47", "56", "57", "67"
    ]
    card_pairs = [f"{c}-1" for c in base_cards] + [f"{c}-2" for c in base_cards]
    random.shuffle(card_pairs)
    st.session_state.game_board = card_pairs
    st.session_state.card_status = ['hidden'] * 42
    st.session_state.flipped_indices = []
    st.session_state.matched_pairs = 0
    st.session_state.start_time = time.time()
    st.session_state.game_started = True
    st.session_state.game_over = False
    st.session_state.reward_claimed = False
    st.session_state.mistake_timer = None

def handle_card_click(index):
    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        if st.session_state.card_status[idx1] != 'matched': st.session_state.card_status[idx1] = 'hidden'
        if st.session_state.card_status[idx2] != 'matched': st.session_state.card_status[idx2] = 'hidden'
        st.session_state.flipped_indices = []
        st.session_state.mistake_timer = None
    if st.session_state.card_status[index] == 'hidden':
        st.session_state.card_status[index] = 'flipped'
        st.session_state.flipped_indices.append(index)
    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        card1, card2 = st.session_state.game_board[idx1], st.session_state.game_board[idx2]
        if card1.split('-')[0] == card2.split('-')[0]:
            st.session_state.card_status[idx1] = 'matched'
            st.session_state.card_status[idx2] = 'matched'
            st.session_state.matched_pairs += 1
            st.session_state.flipped_indices = []
            st.session_state.mistake_timer = None
        else:
            st.session_state.mistake_timer = time.time()

def reset_game_state():
    keys_to_delete = [
        'game_board', 'card_status', 'flipped_indices', 'matched_pairs', 'start_time',
        'game_started', 'game_over', 'reward_claimed', 'mistake_timer'
    ]
    for key in keys_to_delete:
        if key in st.session_state: del st.session_state[key]