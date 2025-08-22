# flash_card.py
import streamlit as st
import random
import time
import os

def start_game(user_email, db_update_func):
    """
    開始翻翻樂遊戲
    :param user_email: 當前登入的使用者ID
    :param db_update_func: 從 main.py 傳入的資料庫更新函式
    """
    st.title("🧠 記憶翻翻樂")

    # --- 遊戲狀態初始化 ---
    if 'game_started' not in st.session_state or not st.session_state.game_started:
        initialize_game()

    # --- 【速度優化】快速翻卡：檢查是否有計時中的翻錯卡片 ---
    # 將延遲時間從 0.8 秒縮短為 0.5 秒，讓程式感覺更流暢、不卡頓
    if st.session_state.get('mistake_timer') and time.time() - st.session_state.mistake_timer > 0.5:
        if len(st.session_state.flipped_indices) == 2:
            idx1, idx2 = st.session_state.flipped_indices
            if st.session_state.card_status[idx1] != 'matched':
                st.session_state.card_status[idx1] = 'hidden'
            if st.session_state.card_status[idx2] != 'matched':
                st.session_state.card_status[idx2] = 'hidden'
            st.session_state.flipped_indices = []
        st.session_state.mistake_timer = None
        st.rerun()

    # --- 遊戲結束 UI ---
    if st.session_state.get('game_over', False):
        st.success(f"時間到！你成功配對了 {st.session_state.matched_pairs} 組！")
        st.info(f"你獲得了 {st.session_state.matched_pairs} 個爆米花 🍿")
        
        if not st.session_state.get('reward_claimed', False):
            if db_update_func(user_email, st.session_state.matched_pairs):
                st.session_state.reward_claimed = True
                st.balloons()
            else:
                st.error("領取獎勵失敗，請稍後再試。")
        
        if st.button("返回大廳"):
            st.session_state.page = "主頁"
            reset_game_state()
            st.rerun()
        return

    # --- 顯示計時器和分數 ---
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, 60 - int(elapsed_time))
    
    col1, col2 = st.columns(2)
    col1.metric(label="剩餘時間", value=f"{remaining_time} 秒")
    col2.metric(label="已配對", value=f"{st.session_state.matched_pairs} 組")

    if remaining_time <= 0 and not st.session_state.get('mistake_timer'):
        st.session_state.game_over = True
        st.rerun()

    st.markdown("---")

    # --- 顯示遊戲板 ---
    image_folder = os.path.join("image", "flash_card")
    card_back_image = os.path.join(image_folder, "卡背.jpg")

    if not os.path.exists(card_back_image):
        st.error(f"找不到卡背圖片: {card_back_image}")
        st.stop()

    cols = st.columns(6)
    for i, card_value in enumerate(st.session_state.game_board):
        col = cols[i % 6]
        with col:
            card_status = st.session_state.card_status[i]
            
            is_clickable = card_status == 'hidden' and len(st.session_state.flipped_indices) < 2 and not st.session_state.get('mistake_timer')

            if card_status in ['flipped', 'matched']:
                image_name = f"{card_value}.jpg"
                image_path = os.path.join(image_folder, image_name)
                try:
                    # --- 【修復黃框】將 use_column_width 改為 use_container_width ---
                    col.image(image_path, use_container_width=True)
                except Exception:
                    col.error(f"找不到 {image_name}")
            else: # hidden
                # --- 【修復黃框】將 use_column_width 改為 use_container_width ---
                col.image(card_back_image, use_container_width=True)
                if col.button("翻開", key=f"card_{i}", use_container_width=True, disabled=not is_clickable):
                    handle_card_click(i)
                    st.rerun()

def initialize_game():
    """初始化或重置遊戲"""
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
    """處理卡片點擊事件"""
    if st.session_state.card_status[index] == 'hidden':
        st.session_state.card_status[index] = 'flipped'
        st.session_state.flipped_indices.append(index)
    
    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        card1 = st.session_state.game_board[idx1]
        card2 = st.session_state.game_board[idx2]

        if card1.split('-')[0] == card2.split('-')[0]: # 配對成功
            st.session_state.card_status[idx1] = 'matched'
            st.session_state.card_status[idx2] = 'matched'
            st.session_state.matched_pairs += 1
            st.session_state.flipped_indices = []
        else: # 配對失敗
            st.session_state.mistake_timer = time.time()

def reset_game_state():
    """清除遊戲相關的 session state"""
    keys_to_delete = [
        'game_board', 'card_status', 'flipped_indices', 'matched_pairs',
        'start_time', 'game_started', 'game_over', 'reward_claimed', 'mistake_timer'
    ]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]