import streamlit as st
from PIL import Image
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import pillow_heif # 🌟 新增：載入蘋果照片翻譯蒟蒻

# 🌟 新增：讓系統正式支援讀取 iPhone 的 HEIC 照片
pillow_heif.register_heif_opener()

# === 🌟 介面大美容 ===
st.set_page_config(page_title="我的 AI 數位衣櫥", page_icon="👗", layout="centered")

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.stButton>button {
    border-radius: 20px;
    background-color: #9FB1A6; 
    color: white;
    border: none;
    padding: 10px 24px;
    box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
    font-weight: bold;
}

.stButton>button:hover {
    background-color: #82968A;
    transform: translateY(-2px);
    box-shadow: 2px 4px 12px rgba(0,0,0,0.15);
    color: white;
}

.css-1v0mbdj {
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)

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

st.markdown("<h1 style='text-align: center; color: #4A4A4A;'>✨ 我的 AI 數位衣櫥 ✨</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888; margin-bottom: 20px;'>你的專屬智能穿搭管家</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📤 上傳新衣", "🚪 瀏覽衣櫥", "🪄 穿搭建議"])

# --- 第一個分頁：上傳區 ---
with tab1:
    # 🌟 修改：在 type 裡面加入 heic, heif, dng, raw 這些蘋果可能出現的格式
    uploaded_file = st.file_uploader("拍張照或選擇圖片", type=["jpg", "jpeg", "png", "heic", "heif", "dng", "raw"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="上傳的衣服照片", use_container_width=True)
        
        save_path = os.path.join(SAVE_DIR, uploaded_file.name)
        
        if uploaded_file.name not in wardrobe_data:
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            wardrobe_data[uploaded_file.name] = ["未分類"]
            save_db(wardrobe_data)
            st.success("✅ 照片已自動存入衣櫥！（目前標籤：未分類）")
        else:
            current_tags = wardrobe_data[uploaded_file.name]
            st.info(f"這件衣服已經在衣櫥裡囉！目前標籤：{', '.join(current_tags)}")
        
        if st.button("✨ 讓 AI 幫這件衣服自動貼標籤", use_container_width=True):
            with st.spinner("AI 正在仔細看這件衣服..."):
                prompt = "這是一件衣服的圖片。請用繁體中文，給這件衣服 4 個標籤：1.季節(如:夏季/冬季)、2.類型(如:短袖/外套/長褲)、3.顏色(如:黑色/白色)、4.風格(如:休閒/正式/運動)。請直接輸出這4個標籤，用逗號隔開，不要講其他廢話。"
                
                # 🌟 如果是 HEIC 檔，AI 模型可能也吃不消，我們在傳給 AI 前順手把它轉成通用 RGB 模式
                if image.mode != "RGB":
                    image = image.convert("RGB")
                    
                response = model.generate_content([prompt, image])
                tags_text = response.text.strip()
                tags = tags_text.replace('，', ',').split(',')
                tags = [tag.strip() for tag in tags if tag.strip()]
                
                wardrobe_data[uploaded_file.name] = tags
                save_db(wardrobe_data)
                
                st.success(f"辨識完成！標籤已更新為：{', '.join(tags)}")

# --- 第二個分頁：瀏覽區 ---
with tab2:
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
                    
                    if st.button("🗑️ 刪除", key=f"del_{file_name}", use_container_width=True):
                        try:
                            os.remove(img_path)
                        except:
                            pass
                        del wardrobe_data[file_name]
                        save_db(wardrobe_data)
                        st.rerun()

# --- 第三個分頁：穿搭建議區 ---
with tab3:
    schedule = st.text_input("📍 今天的行程或目的地？", placeholder="例如：去小酒館約會、去健身運動...")
    weather = st.text_input("🌤️ 天氣狀況如何？", placeholder="例如：台南目前 26 度晴天...")
    
    if st.button("👗 請 AI 幫我搭配！", use_container_width=True):
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
                    st.markdown("### ✨ AI 穿搭建議")
                    st.info(response.text)
                    
                    st.markdown("### 👕 推薦單品預覽")
                    cols = st.columns(3)
                    col_idx = 0
                    for file_name in wardrobe_data.keys():
                        if file_name in response.text:
                            img_path = os.path.join(SAVE_DIR, file_name)
                            if os.path.exists(img_path):
                                img = Image.open(img_path)
                                with cols[col_idx % 3]:
                                    st.image(img, use_container_width=True)
                                col_idx += 1
                                
                except Exception as e:
                    st.error(f"產生建議時發生錯誤：{e}")