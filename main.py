# gacha.py
import streamlit as st
import random
import os
from pathlib import Path
from firebase_admin import firestore
import time

# --- Helper Functions ---

@st.cache_data
def get_all_cards_in_pool(pool_name):
    """
    掃描指定卡池的資料夾，獲取所有卡片的稀有度和路徑。
    """
    base_path = Path(f"image/gacha/{pool_name}")
    all_cards = {}
    rarities = ['R', 'SR', 'SSR', 'SP']
    
    for rarity in rarities:
        rarity_path = base_path / rarity
        if rarity_path.is_dir():
            all_cards[rarity] = sorted([p.as_posix() for p in rarity_path.glob('*.jpg')])
            
    card_back_path = base_path / "卡背.jpg"
    if card_back_path.exists():
        all_cards['card_back'] = card_back_path.as_posix()
    else:
        all_cards['card_back'] = None 
        
    return all_cards

def save_cards_to_db(username, drawn_cards, db):
    """將抽到的卡片儲存到使用者的 Firestore subcollection 中"""
    if not drawn_cards:
        return
    
    user_ref = db.collection('users').document(username)
    
    for card_path in drawn_cards:
        doc_id = card_path.replace('/', '_').replace('\\', '_')
        card_ref = user_ref.collection('cards').document(doc_id)
        card_ref.set({'path': card_path, 'count': firestore.Increment(1)}, merge=True)

# --- Core Game Logic ---

def perform_draw(pool_name, num_draws, username, current_popcorn, db_update_func, db):
    """執行抽卡邏輯，包含機率計算和保底"""
    cost = num_draws * 10
    if current_popcorn < cost:
        st.error(f"爆米花不足！本次抽卡需要 {cost} 🍿，您只有 {current_popcorn} 🍿。")
        return None

    db_update_func(username, -cost)
    st.success(f"已消耗 {cost} 爆米花...")
    time.sleep(1)

    pool_cards = get_all_cards_in_pool(pool_name)
    probabilities = {'R': 60, 'SR': 25, 'SSR': 10, 'SP': 5}
    rarities = list(probabilities.keys())
    weights = list(probabilities.values())
    
    drawn_cards = []
    
    def draw_one_card(custom_rarities=None, custom_weights=None):
        r_list = custom_rarities or rarities
        w_list = custom_weights or weights
        chosen_rarity = random.choices(r_list, weights=w_list, k=1)[0]
        if pool_cards.get(chosen_rarity) and pool_cards[chosen_rarity]:
            return random.choice(pool_cards[chosen_rarity])
        else:
            st.warning(f"警告：找不到稀有度為 {chosen_rarity} 的卡片，將重新抽取...")
            return draw_one_card(r_list, w_list)

    if num_draws == 10:
        guaranteed_rarity = random.choices(['SSR', 'SP'], weights=[90, 10], k=1)[0]
        if pool_cards.get(guaranteed_rarity) and pool_cards[guaranteed_rarity]:
            drawn_cards.append(random.choice(pool_cards[guaranteed_rarity]))
        else:
             st.warning(f"警告：找不到保底稀有度 {guaranteed_rarity} 的卡片，將改為普通抽卡...")
             drawn_cards.append(draw_one_card())
        
        for _ in range(9):
            drawn_cards.append(draw_one_card())
    else:
        for _ in range(num_draws):
            drawn_cards.append(draw_one_card())
            
    random.shuffle(drawn_cards)
    save_cards_to_db(username, drawn_cards, db)
    return drawn_cards

# --- UI Functions ---

def show_draw_page(pool_name, username, current_popcorn, db_update_func, db):
    """顯示指定卡池的抽卡介面"""
    st.header(f"卡池: {pool_name}")

    if st.button("⬅️ 返回卡池選擇"):
        st.session_state.gacha_page = 'main_menu'
        st.rerun()

    st.markdown("---")
    
    if st.session_state.get('last_draw_results'):
        st.subheader("🎉 抽卡結果 🎉")
        cols = st.columns(5)
        results = st.session_state.last_draw_results
        for i, card_path in enumerate(results):
            with cols[i % 5]:
                st.image(card_path, use_container_width=True)
        st.session_state.last_draw_results = None
        st.markdown("---")

    st.info(f"每次抽卡消耗 10 🍿，十連抽消耗 100 🍿。")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("抽一次", use_container_width=True):
            results = perform_draw(pool_name, 1, username, current_popcorn, db_update_func, db)
            if results:
                st.session_state.last_draw_results = results
                st.rerun()
    with col2:
        if st.button("十連抽 (保底 SSR 以上！)", use_container_width=True, type="primary"):
            results = perform_draw(pool_name, 10, username, current_popcorn, db_update_func, db)
            if results:
                st.session_state.last_draw_results = results
                st.rerun()

def show_collection_page(username, db):
    st.header("📚 我的卡冊")
    if st.button("⬅️ 返回抽卡主選單"):
        st.session_state.gacha_page = 'main_menu'
        st.session_state.collection_selected_pool = None
        st.rerun()

    if st.session_state.collection_selected_pool is None:
        st.subheader("請選擇要查看的卡池")
        pool_names = ["春日記憶"]
        for pool in pool_names:
            if st.button(pool, use_container_width=True):
                st.session_state.collection_selected_pool = pool
                st.rerun()
    else:
        selected_pool = st.session_state.collection_selected_pool
        
        if st.button(f"⬅️ 返回卡冊主頁"):
            st.session_state.collection_selected_pool = None
            st.rerun()
        
        st.subheader(f"卡池: {selected_pool}")
        show_owned_only = st.checkbox("✅ 僅顯示已擁有", key=f"filter_{selected_pool}")
        
        pool_data = get_all_cards_in_pool(selected_pool)
        try:
            cards_ref = db.collection('users').document(username).collection('cards').stream()
            owned_cards = {doc.to_dict()['path']: doc.to_dict()['count'] for doc in cards_ref}
        except Exception as e:
            st.error(f"讀取卡冊資料失敗: {e}")
            return
        
        card_back = pool_data.get('card_back')
        if not card_back:
            st.warning(f"找不到「{selected_pool}」的卡背圖片，無法顯示未擁有卡片。")
            return

        rarities_to_show = ['SP', 'SSR', 'SR', 'R']
        for rarity in rarities_to_show:
            if pool_data.get(rarity):
                cards_in_rarity = pool_data[rarity]
                owned_in_rarity = [card for card in cards_in_rarity if card in owned_cards]
                if show_owned_only and not owned_in_rarity:
                    continue

                st.markdown(f"**{rarity} ({len(owned_in_rarity)} / {len(cards_in_rarity)})**")
                cols = st.columns(6)
                
                col_index = 0
                for card_path in cards_in_rarity:
                    count = owned_cards.get(card_path, 0)
                    if show_owned_only and count == 0:
                        continue
                    
                    with cols[col_index % 6]:
                        if count > 0:
                            st.image(card_path, caption=f"擁有: {count}", use_container_width=True)
                        else:
                            st.image(card_back, caption="未擁有", use_container_width=True)
                    col_index += 1
        st.markdown("---")

def show_main_menu(username, db):
    st.header("🎁 卡池選擇")

    # --- 【新增】返回遊戲大廳按鈕 ---
    if st.button("⬅️ 返回遊戲大廳"):
        st.session_state.page = "主頁"
        st.rerun()
        return # 加上 return 避免執行後續程式碼

    st.markdown("---")
    
    if st.button("📚 查看我的卡冊"):
        st.session_state.gacha_page = 'collection_page'
        st.session_state.collection_selected_pool = None
        st.rerun()
        
    st.markdown("---")

    pools = ["春日記憶", "夏日記憶", "秋日記憶", "冬日記憶"]
    cols = st.columns(len(pools))
    
    for i, pool_name in enumerate(pools):
        with cols[i]:
            pool_image_path = Path(f"image/gacha/{pool_name}/卡池封面.jpg")
            if pool_image_path.exists():
                st.image(pool_image_path.as_posix(), use_container_width=True)
            
            if st.button(pool_name, key=pool_name, use_container_width=True):
                if pool_name == "春日記憶":
                    st.session_state.gacha_page = 'draw_page'
                    st.session_state.selected_pool = pool_name
                    st.session_state.last_draw_results = None
                    st.rerun()
                else:
                    st.warning("此卡池正在開發中，敬請期待！")

def start_game(username, db_update_func):
    st.title("🎰 抽卡遊戲")
    db = st.session_state['db']
    current_popcorn = st.session_state.get('popcorn', 0)
    
    if 'gacha_page' not in st.session_state:
        st.session_state.gacha_page = 'main_menu'
    if 'collection_selected_pool' not in st.session_state:
        st.session_state.collection_selected_pool = None

    if st.session_state.gacha_page == 'main_menu':
        show_main_menu(username, db)
    elif st.session_state.gacha_page == 'draw_page':
        show_draw_page(st.session_state.selected_pool, username, current_popcorn, db_update_func, db)
    elif st.session_state.gacha_page == 'collection_page':
        show_collection_page(username, db)