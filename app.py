import streamlit as st
from PIL import Image
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# --- 讀取你的 API 金鑰 ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-2.5-flash')

# --- 基礎設定：資料夾與資料庫 ---
SAVE_DIR = "wardrobe_images"
DB_FILE = "wardrobe_db.json"

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

wardrobe_data = load_db()

st.title("我的 AI 數位衣櫥 👕👗")
tab1, tab2, tab3 = st.tabs(["📤 上傳與 AI 辨識", "🚪 我的衣櫥與篩選", "🪄 智能穿搭建議"])

# --- 第一個分頁：上傳區 ---
with tab1:
    st.write("上傳衣服，AI 會自動幫你分析並貼上標籤！")
    uploaded_file = st.file_uploader("選擇衣服照片", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="準備辨識中...", use_container_width=True)
        
        if st.button("✨ 讓 AI 自動產生標籤"):
            with st.spinner("AI 正在仔細看這件衣服..."):
                save_path = os.path.join(SAVE_DIR, uploaded_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                prompt = "這是一件衣服的圖片。請用繁體中文，給這件衣服 4 個標籤：1.季節(如:夏季/冬季)、2.類型(如:短袖/外套/長褲)、3.顏色(如:黑色/白色)、4.風格(如:休閒/正式/運動)。請直接輸出這4個標籤，用逗號隔開，不要講其他廢話。"
                
                response = model.generate_content([prompt, image])
                tags_text = response.text.strip()
                tags = tags_text.replace('，', ',').split(',')
                tags = [tag.strip() for tag in tags if tag.strip()]
                
                wardrobe_data[uploaded_file.name] = tags
                save_db(wardrobe_data)
                
                st.success(f"辨識完成！AI 貼上的標籤是：{', '.join(tags)}")

# --- 第二個分頁：瀏覽區 (新增垃圾桶功能！) ---
with tab2:
    st.write("用標籤快速找衣服，或把不要的衣服丟進垃圾桶 🗑️")
    
    all_tags = []
    for tags in wardrobe_data.values():
        all_tags.extend(tags)
    unique_tags = list(set(all_tags))
    
    selected_tags = st.multiselect("🔍 選擇你想找的標籤", unique_tags)
    
    filtered_images = []
    for file_name, tags in wardrobe_data.items():
        if not selected_tags or all(tag in tags for tag in selected_tags):
            filtered_images.append(file_name)
    
    if len(filtered_images) == 0:
        st.info("目前沒有符合條件的衣服喔！")
    else:
        cols = st.columns(3)
        for i, file_name in enumerate(filtered_images):
            img_path = os.path.join(SAVE_DIR, file_name)
            if os.path.exists(img_path):
                img = Image.open(img_path)
                with cols[i % 3]:
                    st.image(img, use_container_width=True)
                    st.caption(f"🏷️ {', '.join(wardrobe_data[file_name])}")
                    
                    # === 垃圾桶按鈕的核心邏輯 ===
                    # 注意：Streamlit 規定每個按鈕都要有一個獨一無二的 key，我們用檔案名稱當作 key
                    if st.button("🗑️ 刪除這件", key=f"del_{file_name}"):
                        # 1. 從圖片資料夾中刪除檔案
                        try:
                            os.remove(img_path)
                        except:
                            pass
                        # 2. 從文字資料庫中刪除標籤紀錄
                        del wardrobe_data[file_name]
                        save_db(wardrobe_data)
                        
                        # 3. 讓網頁瞬間重新整理，畫面上的衣服就會消失！
                        st.rerun()

# --- 第三個分頁：穿搭建議區 ---
with tab3:
    st.write("告訴我你今天的行程和天氣，我來幫你搭衣服！")
    
    schedule = st.text_input("📍 今天的行程或目的地？", placeholder="例如：去小酒館約會、去健身運動，或是準備去京都/大阪旅遊")
    weather = st.text_input("🌤️ 天氣狀況如何？", placeholder="例如：台南目前天氣很熱，或是大約 15 度有點冷")
    
    if st.button("👗 請 AI 幫我搭配！"):
        if not schedule or not weather:
            st.warning("請先輸入行程和天氣喔！")
        elif len(wardrobe_data) < 2:
            st.warning("衣櫥裡的衣服還太少，請先去「上傳區」多新增幾件衣服吧！")
        else:
            with st.spinner("AI 造型師正在翻找你的衣櫥..."):
                wardrobe_str = ""
                for file_name, tags in wardrobe_data.items():
                    wardrobe_str += f"- 檔名: {file_name}, 標籤: {', '.join(tags)}\n"
                
                outfit_prompt = f"""
                你是一個專業的穿搭顧問。以下是我衣櫥裡目前所有的衣服和它們的標籤：
                {wardrobe_str}
                
                我今天的行程是：「{schedule}」，天氣/地點狀況是：「{weather}」。
                請從我的衣櫥中，挑選出一套最適合的穿搭組合。
                請用輕鬆、朋友般的口吻，用繁體中文告訴我為什麼這樣搭配，並在文字中具體提到衣服的「檔名」。
                """
                
                try:
                    response = model.generate_content(outfit_prompt)
                    st.write("### ✨ AI 穿搭建議")
                    st.write(response.text)
                    
                    st.write("### 👕 推薦單品預覽")
                    cols = st.columns(3)
                    col_idx = 0
                    for file_name in wardrobe_data.keys():
                        if file_name in response.text:
                            img_path = os.path.join(SAVE_DIR, file_name)
                            if os.path.exists(img_path):
                                img = Image.open(img_path)
                                with cols[col_idx % 3]:
                                    st.image(img, caption=file_name, use_container_width=True)
                                col_idx += 1
                                
                except Exception as e:
                    st.error(f"產生建議時發生錯誤：{e}")