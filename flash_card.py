# flash_card.py
import streamlit as st
import random
import time
import os

def start_game(user_email, db_update_func):
    st.title("🧠 記憶翻翻樂")

    if 'game_started' not in st.session_state or not st.session_state.game_started:
        initialize_game()

    # 遊戲結束 UI
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

    # 顯示計時器和分數
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, 120 - int(elapsed_time))
    
    col1, col2 = st.columns(2)
    col1.metric(label="剩餘時間", value=f"{remaining_time} 秒")
    col2.metric(label="已配對", value=f"{st.session_state.matched_pairs} 組")

    if remaining_time <= 0:
        st.session_state.game_over = True
        st.rerun()

    st.markdown("---")

    image_folder = os.path.join("image", "flash_card")
    card_back_image_path = os.path.join(image_folder, "卡背.jpg")

    cols = st.columns(6)
    for i, card_value in enumerate(st.session_state.game_board):
        col = cols[i % 6]
        with col.container(border=True):
            card_status = st.session_state.card_status[i]
            
            # --- 【排版修改】統一渲染邏輯 ---
            # 1. 決定要顯示正面還是背面
            if card_status in ['flipped', 'matched']:
                image_name = f"{card_value}.jpg"
                current_image_path = os.path.join(image_folder, image_name)
            else: # hidden
                current_image_path = card_back_image_path
            
            # 2. 顯示圖片
            st.image(current_image_path, use_container_width=True)
            
            # 3. 總是顯示按鈕，但根據狀態決定是否禁用
            # 只有當卡片是覆蓋 ('hidden') 狀態時，按鈕才可點擊
            is_disabled = (card_status != 'hidden')
            
            if st.button("翻開", key=f"card_{i}", use_container_width=True, disabled=is_disabled):
                handle_card_click(i)
                st.rerun()

def initialize_game():
    """初始化或重置遊戲"""
    base_cards = [
        "12-1", "13-1", "14-1", "15-1", "16-1", "17-1", "23-1", "24-1", 
        "25-1", "26-1", "27-1", "34-1", "35-1", "36-1", "37-1", "45-1", 
        "46-1", "47-1", "56-1", "57-1", "67-1"
    ]
    card_pairs = base_cards * 2
    random.shuffle(card_pairs)

    st.session_state.game_board = card_pairs
    st.session_state.card_status = ['hidden'] * 42
    st.session_state.flipped_indices = []
    st.session_state.matched_pairs = 0
    st.session_state.start_time = time.time()
    st.session_state.game_started = True
    st.session_state.game_over = False
    st.session_state.reward_claimed = False

def handle_card_click(index):
    """處理卡片點擊事件"""
    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        if st.session_state.card_status[idx1] != 'matched':
            st.session_state.card_status[idx1] = 'hidden'
        if st.session_state.card_status[idx2] != 'matched':
            st.session_state.card_status[idx2] = 'hidden'
        st.session_state.flipped_indices = []

    if st.session_state.card_status[index] == 'hidden':
        st.session_state.card_status[index] = 'flipped'
        st.session_state.flipped_indices.append(index)

    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        card1 = st.session_state.game_board[idx1]
        card2 = st.session_state.game_board[idx2]
        
        if card1 == card2: # 配對成功
            st.session_state.card_status[idx1] = 'matched'
            st.session_state.card_status[idx2] = 'matched'
            st.session_state.matched_pairs += 1
            st.session_state.flipped_indices = []

def reset_game_state():
    """清除遊戲相關的 session state"""
    keys_to_delete = [
        'game_board', 'card_status', 'flipped_indices', 'matched_pairs', 'start_time',
        'game_started', 'game_over', 'reward_claimed'
    ]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]