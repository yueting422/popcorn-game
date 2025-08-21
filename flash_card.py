# flash_card.py
import streamlit as st
import random
import time

def start_game(user_email, db_update_func):
    """
    開始翻翻樂遊戲
    :param user_email: 當前登入的使用者信箱，用於紀錄
    :param db_update_func: 從 main.py 傳入的資料庫更新函式
    """
    st.title("🧠 記憶翻翻樂")

    # --- 遊戲狀態初始化 ---
    if 'game_started' not in st.session_state or not st.session_state.game_started:
        initialize_game()

    # --- 遊戲 UI 和邏輯 ---
    if st.session_state.game_over:
        st.success(f"時間到！你成功配對了 {st.session_state.matched_pairs} 組！")
        st.info(f"你獲得了 {st.session_state.matched_pairs} 個爆米花 🍿")
        
        # 檢查是否已經領取獎勵
        if not st.session_state.reward_claimed:
            if db_update_func(user_email, st.session_state.matched_pairs):
                st.session_state.reward_claimed = True # 標記已領取
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
    
    st.metric(label="剩餘時間", value=f"{remaining_time} 秒")
    st.metric(label="已配對", value=f"{st.session_state.matched_pairs} 組")

    if remaining_time <= 0:
        st.session_state.game_over = True
        st.rerun()

    # --- 顯示遊戲板 ---
    cols = st.columns(7) # 7x6 的版面
    for i, card_value in enumerate(st.session_state.game_board):
        col = cols[i % 7]
        with col:
            card_status = st.session_state.card_status[i]
            
            # 如果卡片被翻開或已配對，顯示卡面
            if card_status in ['flipped', 'matched']:
                st.button(card_value, key=f"card_{i}", disabled=True)
            else: # 否則顯示卡背
                if st.button("❔", key=f"card_{i}"):
                    handle_card_click(i)
                    st.rerun()

def initialize_game():
    """初始化或重置遊戲"""
    # 產生卡片對
    base_cards = [
        "12", "13", "14", "15", "16", "17",
        "23", "24", "25", "26", "27",
        "34", "35", "36", "37",
        "45", "46", "47",
        "56", "57",
        "67"
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
    st.session_state.reward_claimed = False # 是否已領取獎勵

def handle_card_click(index):
    """處理卡片點擊事件"""
    # 如果已經翻了兩張，先進行判斷和重置
    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        card1 = st.session_state.game_board[idx1]
        card2 = st.session_state.game_board[idx2]

        # 檢查是否配對成功
        if card1.split('-')[0] == card2.split('-')[0]:
            st.session_state.card_status[idx1] = 'matched'
            st.session_state.card_status[idx2] = 'matched'
            st.session_state.matched_pairs += 1
        else: # 配對失敗，蓋回去
            st.session_state.card_status[idx1] = 'hidden'
            st.session_state.card_status[idx2] = 'hidden'
        
        st.session_state.flipped_indices = []

    # 翻開當前點擊的卡片
    if st.session_state.card_status[index] == 'hidden':
        st.session_state.card_status[index] = 'flipped'
        st.session_state.flipped_indices.append(index)
    
    # 如果剛好翻了第二張，立即檢查是否配對 (這會讓配對成功的卡片立刻固定)
    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        card1 = st.session_state.game_board[idx1]
        card2 = st.session_state.game_board[idx2]

        if card1.split('-')[0] == card2.split('-')[0]:
            st.session_state.card_status[idx1] = 'matched'
            st.session_state.card_status[idx2] = 'matched'
            st.session_state.matched_pairs += 1
            st.session_state.flipped_indices = []


def reset_game_state():
    """清除遊戲相關的 session state"""
    keys_to_delete = [
        'game_board', 'card_status', 'flipped_indices', 
        'matched_pairs', 'start_time', 'game_started', 'game_over',
        'reward_claimed'
    ]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]