import os
import time
import requests
import threading
import telebot
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

# --- RENDER WEB SERVER (BẮT BUỘC ĐỂ BOT KHÔNG BỊ TẮT TRÊN RENDER) ---
app = Flask(__name__)
@app.route('/')
def index():
    return "Bot is running!"

# --- CẤU HÌNH ---
TOKEN = "8928629119:AAHFjOTJHrdwDHHJ8qqWkKE_vrF5kiC7lok"
FIREBASE_URL = "https://tcoin-e983b-default-rtdb.firebaseio.com/"

bot = telebot.TeleBot(TOKEN)
ALLOWED_THREAD_ID = 1

CONFIG_WEB = {
    "link4m": {"limit": 2, "tcoin": 1000, "name": "Link4M", "api_token": "667da5e0512ac00cba52fb6f"}
}

bot.set_my_commands([
    BotCommand("start", "Mở menu chính"),
    BotCommand("tk", "Kiểm tra TCOIN"),
    BotCommand("doithuong", "Đổi Key VIP"),
    BotCommand("help", "Hướng dẫn")
])

# --- CÁC HÀM TIỆN ÍCH ---
def delete_message_later(chat_id, message_id, delay=600):
    time.sleep(delay)
    try: bot.delete_message(chat_id, message_id)
    except: pass

def send_auto_delete_msg(chat_id, text, reply_markup=None, reply_to_id=None, thread_id=None):
    sent = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup, reply_to_message_id=reply_to_id, message_thread_id=thread_id)
    threading.Thread(target=delete_message_later, args=(chat_id, sent.message_id), daemon=True).start()

def edit_or_send(call, text, reply_markup=None):
    try: bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
    except: send_auto_delete_msg(call.message.chat.id, text, reply_markup=reply_markup, thread_id=getattr(call.message, 'message_thread_id', None))

# --- CÁC HÀM XỬ LÝ LOGIC ---
@bot.message_handler(commands=['start', 'help'])
def start_cmd(m):
    text = "🤖 *HỆ THỐNG VƯỢT LINK TCOIN*\nChào bạn! Chọn dịch vụ bên dưới:"
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🌐 Vượt Link4M (+1,000 TCOIN)", callback_data="v_link4m"),
               InlineKeyboardButton("👤 Tài Khoản", callback_data="menu_tk"),
               InlineKeyboardButton("🎁 Đổi Thưởng", callback_data="menu_doithuong"))
    send_auto_delete_msg(m.chat.id, text, reply_markup=markup, reply_to_id=m.message_id, thread_id=getattr(m, 'message_thread_id', None))

def handle_vuot_link(call, web_key):
    user_id_str = str(call.from_user.id)
    cfg = CONFIG_WEB[web_key]
    today = time.strftime("%Y-%m-%d")
    count = requests.get(f"{FIREBASE_URL}users/{user_id_str}/{today}/{web_key}.json").json() or 0
    if count >= cfg["limit"]:
        bot.answer_callback_query(call.id, "Đã đạt giới hạn hôm nay!", show_alert=True)
        return
    
    session_id = f"{web_key}_{user_id_str}_{int(time.time())}"
    requests.put(f"{FIREBASE_URL}sessions/{session_id}.json", json={"user_id": user_id_str, "web": web_key, "reward": cfg["tcoin"], "status": "pending"})
    final_url = f"https://link4m.co/st?api={cfg['api_token']}&url=https://thanhtoan244.github.io/tcoin/?session={session_id}"
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔗 NHẤN ĐỂ VƯỢT", url=final_url), InlineKeyboardButton("⬅️ Quay lại", callback_data="menu_home"))
    edit_or_send(call, f"🎁 *VƯỢT LINK {cfg['name']} ({count+1}/{cfg['limit']})*\nThưởng: +{cfg['tcoin']} TCOIN", reply_markup=markup)

def process_doi_thuong(call, package):
    costs = {"1lan": 1000, "1ngay": 3000, "1tuan": 10000, "1thang": 30000}
    user_id_str = str(call.from_user.id)
    tcoin = requests.get(f"{FIREBASE_URL}users/{user_id_str}/tcoin.json").json() or 0
    if tcoin < costs[package]:
        bot.answer_callback_query(call.id, "❌ Không đủ TCOIN!", show_alert=True)
        return
    new_tcoin = tcoin - costs[package]
    requests.patch(f"{FIREBASE_URL}users/{user_id_str}.json", json={"tcoin": new_tcoin})
    edit_or_send(call, f"🎉 *ĐỔI THÀNH CÔNG!*\nKey: `BANDVIP-{package.upper()}-{int(time.time())}`\nCòn lại: {new_tcoin} TCOIN", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Menu", callback_data="menu_home")))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    if data == "menu_home": 
        text = "🤖 *MENU CHÍNH*\nChọn dịch vụ bên dưới:"
        markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("🌐 Vượt Link4M", callback_data="v_link4m"), InlineKeyboardButton("👤 Tài Khoản", callback_data="menu_tk"), InlineKeyboardButton("🎁 Đổi Thưởng", callback_data="menu_doithuong"))
        edit_or_send(call, text, reply_markup=markup)
    elif data.startswith("v_"): handle_vuot_link(call, data.split("_")[1])
    elif data == "menu_tk": 
        tcoin = requests.get(f"{FIREBASE_URL}users/{call.from_user.id}/tcoin.json").json() or 0
        edit_or_send(call, f"👤 *TÀI KHOẢN*\n💰 TCOIN: {tcoin}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Quay lại", callback_data="menu_home")))
    elif data == "menu_doithuong":
        markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("🎟️ Key 1 Lần (1k)", callback_data="doi_1lan"), InlineKeyboardButton("🎟️ Key 1 Ngày (3k)", callback_data="doi_1ngay"), InlineKeyboardButton("⬅️ Quay lại", callback_data="menu_home"))
        edit_or_send(call, "🎁 *CHỌN KEY*", reply_markup=markup)
    elif data.startswith("doi_"): process_doi_thuong(call, data.split("_")[1])
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(skip_pending=True)
    
