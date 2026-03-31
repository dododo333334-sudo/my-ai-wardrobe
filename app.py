import streamlit as st
from PIL import Image
import json
import requests
import google.generativeai as genai
import pillow_heif
import cloudinary
import cloudinary.uploader

# --- iPhone 照片翻譯蒟蒻 ---
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
.css-1v0mbdj { border-radius: 15px; }
</style>
""", unsafe_allow_html=True)

# === 🔑 讀取雲端機密鑰匙 (直接從 Streamlit Secrets 讀取) ===
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

cloudinary.config(
    cloud_name = st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key = st.secrets["CLOUDINARY_API_KEY"],
    api_secret = st.secrets["CLOUDINARY_API_SECRET"],
    secure = True
)

JSONBIN_ID = st.secrets["JSONBIN_BIN_ID"]
JSONBIN_KEY = st.secrets["JSONBIN_API_KEY"]
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"

# === ☁️ 雲端資料庫讀寫函數 ===
def load_db():
    headers = {"X-Master-Key": JSONBIN_KEY}
    try:
        req = requests.get(JSONBIN_URL, headers=headers)
        data = req.json()
        return data.get("record", {})
    except:
        return {}

def save_db(data):
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_KEY
    }
    requests.put(JSONBIN_URL, json=data, headers=headers)

# 每次網頁重新整理，就從雲端抓取最新衣櫥資料
wardrobe_data = load_db()

st.markdown("<h1 style='text-align: center; color: #4A4A4A;'>✨ 我的 AI 數位衣櫥 ✨</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888; margin-bottom: 20px;'>真正的雲端全端架構</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📤 上傳新衣", "🚪 瀏覽衣櫥", "🪄 穿搭建議"])

# --- 第一個分頁：上傳區 ---
with tab1:
    uploaded_file = st.file_uploader("拍張照或選擇圖片", type=["jpg", "jpeg", "png", "heic", "heif", "dng", "raw"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="準備收進雲端衣櫥...", use_container_width=True)
        
        # 使用一個專屬按鈕來執行上傳動作
        if st.button("🚀 確認上傳到雲端", use_container_width=True):
            with st.spinner("正在把照片送到 Cloudinary 雲端金庫..."):
                # 1. 將圖片上傳到 Cloudinary
                upload_result = cloudinary.uploader.upload(uploaded_file.getvalue())
                public_id = upload_result["public_id"] # 圖片專屬身分證
                secure_url = upload_result["secure_url"] # 圖片公開網址
                
                # 2. 將資料存進 JSONBin
                wardrobe_data[public_id] = {
                    "url": secure_url,
                    "tags": ["未分類"]
                }
                save_db(wardrobe_data)
                
                st.session_state['last_uploaded_id'] = public_id
                st.success("✅ 照片已永久存入雲端衣櫥！（目前標籤：未分類）")

        # 如果剛剛有上傳成功，就顯示 AI 辨識按鈕
        if 'last_uploaded_id' in st.session_state:
            pid = st.session_state['last_uploaded_id']
            if st.button("✨ 讓 AI 幫這件新衣服自動貼標籤", use_container_width=True):
                with st.spinner("AI 正在仔細看這件衣服..."):
                    prompt = "這是一件衣服的圖片。請用繁體中文，給這件衣服 4 個標籤：1.季節(如:夏季/冬季)、2.類型(如:短袖/外套/長褲)、3.顏色(如:黑色/白色)、4.風格(如:休閒/正式/運動)。請直接輸出這4個標籤，用逗號隔開，不要講其他廢話。"
                    
                    if image.mode != "RGB":
                        image = image.convert("RGB")
                        
                    response = model.generate_content([prompt, image])
                    tags_text = response.text.strip()
                    tags = tags_text.replace('，', ',').split(',')
                    tags = [tag.strip() for tag in tags if tag.strip()]
                    
                    # 更新雲端資料庫裡的標籤
                    wardrobe_data[pid]["tags"] = tags
                    save_db(wardrobe_data)
                    
                    st.success(f"辨識完成！標籤已更新為：{', '.join(tags)}")

# --- 第二個分頁：瀏覽區 ---
with tab2:
    all_tags = []
    for data in wardrobe_data.values():
        if isinstance(data, dict): # 避開我們一開始建立的虛擬垃圾資料
            all_tags.extend(data.get("tags", []))
    unique_tags = list(set(all_tags))
    
    selected_tags = st.multiselect("🔍 選擇你想找的標籤", unique_tags)
    
    filtered_items = []
    for pid, data in wardrobe_data.items():
        if not isinstance(data, dict): continue
        tags = data.get("tags", [])
        if not selected_tags or all(tag in tags for tag in selected_tags):
            filtered_items.append(pid)
    
    if len(filtered_items) == 0:
        st.info("目前沒有符合條件的衣服喔！")
    else:
        cols = st.columns(3)
        for i, pid in enumerate(filtered_items):
            data = wardrobe_data[pid]
            with cols[i % 3]:
                # 直接從 Cloudinary 網址讀取圖片！
                st.image(data["url"], use_container_width=True)
                st.caption(f"🏷️ {', '.join(data['tags'])}")
                
                # 刪除功能：同時刪除 Cloudinary 圖片與 JSONBin 紀錄
                if st.button("🗑️ 刪除", key=f"del_{pid}", use_container_width=True):
                    try:
                        cloudinary.uploader.destroy(pid)
                    except:
                        pass
                    del wardrobe_data[pid]
                    save_db(wardrobe_data)
                    st.rerun()

# --- 第三個分頁：穿搭建議區 ---
with tab3:
    schedule = st.text_input("📍 今天的行程或目的地？", placeholder="例如：去小酒館約會、去健身運動...")
    weather = st.text_input("🌤️ 天氣狀況如何？", placeholder="例如：台南目前 26 度晴天...")
    
    if st.button("👗 請 AI 幫我搭配！", use_container_width=True):
        if not schedule or not weather:
            st.warning("請先輸入行程和天氣喔！")
        else:
            with st.spinner("AI 造型師正在翻找你的衣櫥..."):
                wardrobe_str = ""
                for pid, data in wardrobe_data.items():
                    if isinstance(data, dict):
                        wardrobe_str += f"- 單品代號: {pid}, 標籤: {', '.join(data['tags'])}\n"
                
                outfit_prompt = f"""
                你是一個專業的穿搭顧問。以下是我衣櫥裡目前所有的衣服代號和標籤：
                {wardrobe_str}
                
                我今天的行程是：「{schedule}」，天氣/地點狀況是：「{weather}」。
                請從我的衣櫥中，挑選出一套最適合的穿搭組合。
                請用輕鬆、朋友般的口吻，用繁體中文告訴我為什麼這樣搭配，並在文字中具體提到衣服的「單品代號」。
                """
                
                try:
                    response = model.generate_content(outfit_prompt)
                    st.markdown("### ✨ AI 穿搭建議")
                    st.info(response.text)
                    
                    st.markdown("### 👕 推薦單品預覽")
                    cols = st.columns(3)
                    col_idx = 0
                    for pid in wardrobe_data.keys():
                        if pid in response.text:
                            with cols[col_idx % 3]:
                                st.image(wardrobe_data[pid]["url"], use_container_width=True)
                            col_idx += 1
                                
                except Exception as e:
                    st.error(f"產生建議時發生錯誤：{e}")