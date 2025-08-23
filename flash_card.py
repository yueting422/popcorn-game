# flash_card.py
import streamlit as st
import random
import time
import os
import base64
from pathlib import Path

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
    
    # --- 【新增】加上提示訊息 ---
    st.info("💡 建議使用電腦或將手機橫置遊玩，以獲得最佳體驗。")

    if 'game_started' not in st.session_state or not st.session_state.game_started:
        initialize_game()

    params = st.query_params
    if "card_click" in params:
        clicked_index = int(params["card_click"])
        st.query_params.clear()
        handle_card_click(clicked_index)
        st.rerun()

    # 遊戲結束 UI
    if st.session_state.get('game_over', False):
        if st.session_state.matched_pairs == st.session_state.total_pairs:
            st.balloons()
            st.success(f"恭喜！您在時間內完成了所有配對！")
        else:
            st.success(f"時間到！")
        st.info(f"最終成績：成功配對 {st.session_state.matched_pairs} 組！")
        st.info(f"你獲得了 {st.session_state.matched_pairs} 個爆米花 🍿")
        if not st.session_state.get('reward_claimed', False):
            if db_update_func(user_email, st.session_state.matched_pairs):
                st.session_state.reward_claimed = True
        if st.button("返回大廳"):
            st.session_state.page = "主頁"
            reset_game_state()
            st.rerun()
        return

    # 顯示計時器和分數
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = max(0, 90 - int(elapsed_time))
    col1, col2 = st.columns(2)
    col1.metric(label="剩餘時間", value=f"{remaining_time} 秒")
    col2.metric(label="已配對", value=f"{st.session_state.matched_pairs} / {st.session_state.total_pairs} 組")
    if remaining_time <= 0:
        st.session_state.game_over = True
        st.rerun()

    st.markdown("---")

    st.markdown("""
        <style>
            .card-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 10px;
            }
            .card-container {
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 5px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            .card-container img {
                width: 100%;
                height: 180px;
                object-fit: cover;
                border-radius: 5px;
            }
            .card-container a {
                text-decoration: none;
            }
        </style>
    """, unsafe_allow_html=True)

    image_folder = os.path.join("image", "flash_card")
    card_back_image_path = os.path.join(image_folder, "卡背.jpg")

    cards_html_list = []
    for i, card_value in enumerate(st.session_state.game_board):
        card_status = st.session_state.card_status[i]
        
        if card_status in ['flipped', 'matched']:
            # --- 【卡面修改】圖片名稱直接使用卡片值 (例如 "1.jpg") ---
            image_name = f"{card_value}.jpg"
            current_image_path = os.path.join(image_folder, image_name)
        else: # hidden
            current_image_path = card_back_image_path
        
        b64_image = image_to_base64(current_image_path)
        
        if card_status == 'hidden':
            card_content = f'<a href="?card_click={i}" target="_self"><img src="{b64_image}"></a>'
        else: 
            card_content = f'<img src="{b64_image}">'
        
        cards_html_list.append(f'<div class="card-container">{card_content}</div>')

    st.markdown(f'<div class="card-grid">{"".join(cards_html_list)}</div>', unsafe_allow_html=True)


def initialize_game():
    """初始化或重置遊戲"""
    # --- 【卡面修改】卡池改為 1~8 ---
    base_cards = ["1", "2", "3", "4", "5", "6", "7", "8"]
    
    # --- 【卡面修改】每種卡片各有兩張 ---
    card_pairs = base_cards * 2
    random.shuffle(card_pairs)

    st.session_state.game_board = card_pairs
    st.session_state.card_status = ['hidden'] * 16
    st.session_state.flipped_indices = []
    st.session_state.matched_pairs = 0
    st.session_state.total_pairs = len(base_cards)
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
        
        # --- 【規則修改】配對邏輯改為比較兩張卡是否完全相同 ---
        if card1 == card2: # 配對成功
            st.session_state.card_status[idx1] = 'matched'
            st.session_state.card_status[idx2] = 'matched'
            st.session_state.matched_pairs += 1
            st.session_state.flipped_indices = []
            if st.session_state.matched_pairs == st.session_state.total_pairs:
                st.session_state.game_over = True

def reset_game_state():
    """清除遊戲相關的 session state"""
    keys_to_delete = [
        'game_board', 'card_status', 'flipped_indices', 'matched_pairs', 'start_time',
        'game_started', 'game_over', 'reward_claimed', 'total_pairs'
    ]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]