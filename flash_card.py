# flash_card.py
import streamlit as st
import random
import time
import os
import streamlit.components.v1 as components

# 這次我們不再需要 image_to_base64，因為 st.image 可以直接處理路徑
# 這也讓程式碼更簡潔

def trigger_auto_flip():
    """
    使用 JavaScript 的 setTimeout 在前端觸發頁面刷新，
    這是實現非同步延遲後操作的最可靠方法。
    """
    components.html(
        f"""
        <script>
            setTimeout(function() {{
                window.parent.location.href = window.parent.location.href;
            }}, 500); // 500 毫秒 = 0.5 秒
        </script>
        """,
        height=0,
        width=0,
    )

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
    remaining_time = max(0, 60 - int(elapsed_time))
    
    col1, col2 = st.columns(2)
    col1.metric(label="剩餘時間", value=f"{remaining_time} 秒")
    col2.metric(label="已配對", value=f"{st.session_state.matched_pairs} 組")

    if remaining_time <= 0 and len(st.session_state.flipped_indices) < 2:
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
            
            if card_status in ['flipped', 'matched']:
                image_name = f"{card_value}.jpg"
                current_image_path = os.path.join(image_folder, image_name)
                st.image(current_image_path, use_container_width=True)
            else: # hidden
                st.image(card_back_image_path, use_container_width=True)
                
                # 按鈕是否可點擊的邏輯
                # 只有當翻開的牌少於2張時，才能點擊
                is_clickable = len(st.session_state.flipped_indices) < 2
                if st.button("翻開", key=f"card_{i}", use_container_width=True, disabled=not is_clickable):
                    handle_card_click(i)
                    st.rerun()

# (initialize_game, reset_game_state 函式不變)
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

def handle_card_click(index):
    # 【核心修改】當點擊時，如果已有兩張牌，則先將它們翻回去
    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        if st.session_state.card_status[idx1] != 'matched': st.session_state.card_status[idx1] = 'hidden'
        if st.session_state.card_status[idx2] != 'matched': st.session_state.card_status[idx2] = 'hidden'
        st.session_state.flipped_indices = []

    # 翻開當前點擊的牌
    if st.session_state.card_status[index] == 'hidden':
        st.session_state.card_status[index] = 'flipped'
        st.session_state.flipped_indices.append(index)

    # 如果翻開後剛好是第二張，檢查是否配對
    if len(st.session_state.flipped_indices) == 2:
        idx1, idx2 = st.session_state.flipped_indices
        card1, card2 = st.session_state.game_board[idx1], st.session_state.game_board[idx2]
        
        if card1.split('-')[0] == card2.split('-')[0]: # 配對成功
            st.session_state.card_status[idx1] = 'matched'
            st.session_state.card_status[idx2] = 'matched'
            st.session_state.matched_pairs += 1
            st.session_state.flipped_indices = []
        else: # 配對失敗
            # 【核心修改】呼叫 JavaScript 計時器來觸發刷新
            trigger_auto_flip()

def reset_game_state():
    keys_to_delete = [
        'game_board', 'card_status', 'flipped_indices', 'matched_pairs', 'start_time',
        'game_started', 'game_over', 'reward_claimed'
    ]
    for key in keys_to_delete:
        if key in st.session_state: del st.session_state[key]