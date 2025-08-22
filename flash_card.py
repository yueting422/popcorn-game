# flash_card.py
import streamlit as st
import random
import time
import os
import base64
from pathlib import Path
from streamlit_card import card

@st.cache_data
def image_to_base64(image_path: str) -> str:
    """將圖片檔案轉換為 Base64 字串"""
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

    # --- 【Bug 修復】重構點擊處理邏輯 ---
    # 先檢查是否有被點擊的卡片，再執行相應的處理函式
    # 這樣可以避免在 Streamlit 的渲染迴圈中發生狀態錯亂
    if st.session_state.get("clicked_card_index") is not None:
        clicked_index = st.session_state.pop("clicked_card_index") # 取出值後立刻清除
        handle_card_click(clicked_index)
        st.rerun() # 處理完點擊後立即重繪

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
            
            if b64_image:
                is_clicked = card(
                    title="", text="", image=b64_image,
                    styles={
                        "card": {"width": "100%", "height": "150px", "margin": "0px", "padding": "0px"},
                        "filter": {"background-color": "rgba(0, 0, 0, 0)"},
                        "div": {"padding": "0px"},
                        # --- 【大小統一】新增此行CSS來讓圖片填滿空間且不變形 ---
                        "img": {"object-fit": "cover", "height": "100%"}
                    },
                    key=f"card_{i}"
                )
                
                # --- 【Bug 修復】修改點擊處理方式 ---
                # 當卡片被點擊時，只記錄被點擊的索引，不做其他事
                if is_clicked and card_status == 'hidden':
                    st.session_state.clicked_card_index = i
                    st.rerun()

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
    # 用來處理點擊事件的 session state
    if "clicked_card_index" not in st.session_state:
        st.session_state.clicked_card_index = None

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
        'game_started', 'game_over', 'reward_claimed', 'mistake_timer', 'clicked_card_index'
    ]
    for key in keys_to_delete:
        if key in st.session_state: del st.session_state[key]