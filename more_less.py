# more_less.py
import streamlit as st
import random
import os
import time

def start_game(user_email, db_update_func):
    """開始比大小遊戲"""
    st.title("⚖️ 比大小")
    st.info("💡 遊戲規則：下注後選擇一張牌，再猜測您的牌中人物年齡比電腦的大還是小。")

    # --- 遊戲狀態初始化 ---
    if 'mg_stage' not in st.session_state:
        initialize_game()

    # 顯示當前爆米花數量
    current_popcorn = st.session_state.get('popcorn', 0)
    st.sidebar.success(f"您目前擁有 {current_popcorn} 🍿")

    # --- 根據不同遊戲階段顯示對應介面 ---
    if st.session_state.mg_stage == 'betting':
        show_betting_stage(current_popcorn)
    elif st.session_state.mg_stage == 'player_chooses':
        show_player_choice_stage()
    elif st.session_state.mg_stage == 'player_guesses':
        show_guessing_stage()
    elif st.session_state.mg_stage == 'reveal':
        show_reveal_stage(user_email, db_update_func)

def initialize_game():
    """初始化或重置遊戲狀態"""
    st.session_state.mg_stage = 'betting'
    st.session_state.mg_deck = list(range(1, 8))
    st.session_state.mg_player_card = None
    st.session_state.mg_computer_card = None
    st.session_state.mg_bet_amount = 0
    st.session_state.mg_game_message = ""
    st.session_state.mg_result_claimed = False # 用於確保獎勵只領取一次

def show_betting_stage(current_popcorn):
    """顯示下注介面"""
    st.subheader("STEP 1: 請下注")
    if current_popcorn == 0:
        st.warning("您的爆米花為 0，無法下注！請先去玩翻翻樂賺取爆米花。")
        if st.button("返回大廳"):
            st.session_state.page = "主頁"
            st.rerun()
        return

    with st.form("bet_form"):
        bet_amount = st.number_input(
            f"請輸入您要下注的爆米花數量 (您有 {current_popcorn})",
            min_value=1,
            max_value=current_popcorn,
            step=1
        )
        submitted = st.form_submit_button("下好離手！")
        if submitted:
            st.session_state.mg_bet_amount = bet_amount
            st.session_state.mg_stage = 'player_chooses'
            random.shuffle(st.session_state.mg_deck)
            st.rerun()

def show_player_choice_stage():
    """顯示玩家選牌介面"""
    st.subheader(f"STEP 2: 請選擇一張牌 (已下注 {st.session_state.mg_bet_amount} 🍿)")
    image_folder = os.path.join("image", "more_less")
    card_back_path = os.path.join(image_folder, "卡背.jpg")

    cols = st.columns(7)
    for i in range(7):
        with cols[i]:
            st.image(card_back_path, use_container_width=True)
            if st.button(f"選擇", key=f"choice_{i}", use_container_width=True):
                handle_player_choice(i)
                st.rerun()

def handle_player_choice(choice_index):
    """處理玩家選牌邏輯"""
    deck = st.session_state.mg_deck
    st.session_state.mg_player_card = deck.pop(choice_index)
    st.session_state.mg_computer_card = random.choice(deck)
    st.session_state.mg_stage = 'player_guesses'

def show_guessing_stage():
    """顯示猜大小介面"""
    st.subheader("STEP 3: 您的牌比電腦的大還是小？")
    image_folder = os.path.join("image", "more_less")
    card_back_path = os.path.join(image_folder, "卡背.jpg")
    player_card_path = os.path.join(image_folder, f"{st.session_state.mg_player_card}.jpg")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h4 style='text-align: center;'>您的牌</h4>", unsafe_allow_html=True)
        st.image(player_card_path, use_container_width=True)
    with col2:
        st.markdown("<h4 style='text-align: center;'>電腦的牌</h4>", unsafe_allow_html=True)
        st.image(card_back_path, use_container_width=True)

    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("🔼 比電腦大", use_container_width=True):
        handle_guess('bigger')
        st.rerun()
    if c2.button("🔽 比電腦小", use_container_width=True):
        handle_guess('smaller')
        st.rerun()

def handle_guess(guess):
    """處理猜測邏輯並計算結果"""
    player_card = st.session_state.mg_player_card
    computer_card = st.session_state.mg_computer_card
    bet = st.session_state.mg_bet_amount

    result = "win" if (guess == 'bigger' and player_card > computer_card) or \
                       (guess == 'smaller' and player_card < computer_card) else "lose"
    
    if player_card == computer_card:
        result = "tie"

    if result == "win":
        st.session_state.mg_game_message = f"✅ 猜對了！您贏得了 {bet} 爆米花！"
    elif result == "lose":
        st.session_state.mg_game_message = f"❌ 猜錯了！您失去了 {bet} 爆米花！"
    else: # tie
        st.session_state.mg_game_message = f"🤝 平手！下注的 {bet} 爆米花已退還。"
    
    st.session_state.mg_stage = 'reveal'

def show_reveal_stage(user_email, db_update_func):
    """顯示最終結果"""
    st.subheader("🎉 結果揭曉！")
    image_folder = os.path.join("image", "more_less")
    player_card_path = os.path.join(image_folder, f"{st.session_state.mg_player_card}.jpg")
    computer_card_path = os.path.join(image_folder, f"{st.session_state.mg_computer_card}.jpg")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<h4 style='text-align: center;'>您的牌</h4>", unsafe_allow_html=True)
        st.image(player_card_path, use_container_width=True)
    with col2:
        st.markdown(f"<h4 style='text-align: center;'>電腦的牌</h4>", unsafe_allow_html=True)
        st.image(computer_card_path, use_container_width=True)
    
    st.markdown("---")

    message = st.session_state.mg_game_message
    if "贏得" in message:
        st.success(message)
    elif "失去" in message:
        st.error(message)
    else:
        st.info(message)
    
    # 更新資料庫中的爆米花數量 (只在第一次顯示結果時執行)
    if not st.session_state.mg_result_claimed:
        popcorn_change = 0
        if "贏得" in message:
            popcorn_change = st.session_state.mg_bet_amount
        elif "失去" in message:
            popcorn_change = -st.session_state.mg_bet_amount
        
        if popcorn_change != 0:
            db_update_func(user_email, popcorn_change)
        
        st.session_state.mg_result_claimed = True

    c1, c2 = st.columns(2)
    if c1.button("再玩一局", use_container_width=True):
        initialize_game()
        st.rerun()
    if c2.button("返回大廳", use_container_width=True):
        initialize_game()
        st.session_state.page = "主頁"
        st.rerun()