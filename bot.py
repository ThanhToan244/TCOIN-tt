import telebot
import time
import requests
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

TOKEN = "8928629119:AAEsNQyk81o5zSmykc5RO8jRJCBZ0zu7KOI"
FIREBASE_URL = "https://tcoin-e983b-default-rtdb.firebaseio.com/"

bot = telebot.TeleBot(TOKEN)

CONFIG_WEB = {
    "bbmkts": {"limit": 1, "tcoin": 300, "name": "BBMKTS", "api_token": "0c6640c5ab85b8cd3780f3f7"},
    "link4m": {"limit": 2, "tcoin": 300, "name": "Link4M", "api_token": "667da5e0512ac00cba52fb6f"},
    "layma": {"limit": 2, "tcoin": 500, "name": "Lấy Mã", "api_token": "16a395f95d56b42320bbb730a209ac09"}
}

bot.set_my_commands([
    BotCommand("start", "Mở menu chính & chọn dịch vụ vượt link"),
    BotCommand("tk", "Kiểm tra TCOIN và số lượt vượt hôm nay"),
    BotCommand("doithuong", "Đổi TCOIN lấy Key (1 ngày, 1 tuần, 1 tháng)"),
    BotCommand("help", "Hướng dẫn sử dụng bot")
])

def delete_message_later(chat_id, message_id, delay_seconds=600):
    time.sleep(delay_seconds)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

def send_auto_delete_msg(chat_id, text, parse_mode="Markdown", reply_markup=None):
    sent = bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    t = threading.Thread(target=delete_message_later, args=(chat_id, sent.message_id, 600))
    t.daemon = True
    t.start()
    return sent

@bot.message_handler(commands=['start', 'help'])
def start_cmd(m):
    user_name = m.from_user.first_name
    text = (
        f"🤖 *HỆ THỐNG VƯỢT LINK & TÍCH LŨY TCOIN*\n"
        f"──────────────────────────\n"
        f"Chào {user_name}! Hệ thống chỉ cộng TCOIN khi bạn hoàn thành vượt link thành công.\n"
        f"Chọn dịch vụ bên dưới để bắt đầu:"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🌐 BBMKTS (300 TCOIN)", callback_data="v_bbmkts"),
        InlineKeyboardButton("🌐 Link4M (300 TCOIN)", callback_data="v_link4m"),
        InlineKeyboardButton("🌐 Lấy Mã (500 TCOIN)", callback_data="v_layma"),
        InlineKeyboardButton("👤 Tài Khoản & TCOIN", callback_data="menu_tk"),
        InlineKeyboardButton("🎁 Đổi Thưởng Key", callback_data="menu_doithuong")
    )
    
    send_auto_delete_msg(m.chat.id, text, reply_markup=markup)

def handle_vuot_link(chat_id, user_id, web_key):
    user_id_str = str(user_id)
    cfg = CONFIG_WEB[web_key]
    
    today_str = time.strftime("%Y-%m-%d")
    try:
        res = requests.get(f"{FIREBASE_URL}users/{user_id_str}/{today_str}/{web_key}.json", timeout=5).json()
        count = res if res is not None else 0
    except:
        count = 0

    limit = cfg["limit"]
    if count >= limit:
        send_auto_delete_msg(chat_id, f"🚫 *Bạn đã đạt giới hạn {limit}/{limit} lần vượt cho {cfg['name']} hôm nay!*")
        return

    session_id = f"{web_key}_{user_id}_{int(time.time())}"
    
    requests.put(f"{FIREBASE_URL}sessions/{session_id}.json", json={
        "user_id": user_id_str,
        "web": web_key,
        "reward": cfg["tcoin"],
        "status": "pending"
    })

    target_url = f"https://thanhtoan244.github.io/tcoin/?session={session_id}"
    
    token = cfg["api_token"]
    if web_key == "bbmkts":
        final_url = f"https://bbmkts.com/st?api={token}&url={target_url}"
    elif web_key == "link4m":
        final_url = f"https://link4m.co/st?api={token}&url={target_url}"
    else:
        final_url = f"https://layma.net/st?api={token}&url={target_url}"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"🔗 NHẤN ĐỂ VƯỢT {cfg['name']}", url=final_url))
    
    send_auto_delete_msg(
        chat_id, 
        f"🎁 *VƯỢT LINK {cfg['name']} ({count+1}/{limit})*\n"
        f"• Trạng thái: *Chờ hoàn thành*\n"
        f"• Thưởng nhận được: *+{cfg['tcoin']} TCOIN* (Chỉ cộng sau khi vượt thành công)\n"
        f"Bấm vào nút bên dưới để bắt đầu:", 
        reply_markup=markup
    )

@bot.message_handler(commands=['tk'])
def tk_cmd(m):
    show_account_info(m.chat.id, m.from_user.id, m.from_user.first_name)

def show_account_info(chat_id, user_id, user_name):
    user_id_str = str(user_id)
    today_str = time.strftime("%Y-%m-%d")
    try:
        user_data = requests.get(f"{FIREBASE_URL}users/{user_id_str}.json", timeout=5).json() or {}
        tcoin = user_data.get("tcoin", 0)
        today_data = user_data.get(today_str, {})
        
        bb_c = today_data.get("bbmkts", 0)
        l4m_c = today_data.get("link4m", 0)
        lm_c = today_data.get("layma", 0)
    except:
        tcoin, bb_c, l4m_c, lm_c = 0, 0, 0, 0

    text = (
        f"👤 *THÔNG TIN TÀI KHOẢN*\n"
        f"• Tên: {user_name}\n"
        f"• ID Telegram: `{user_id}`\n"
        f"• 💰 TCOIN hiện có: *{tcoin} TCOIN*\n\n"
        f"📊 *Số lượt vượt hôm nay*:\n"
        f"• BBMKTS: {bb_c}/1\n"
        f"• Link4M: {l4m_c}/2\n"
        f"• Lấy Mã: {lm_c}/2"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Làm mới", callback_data="menu_tk"))
    send_auto_delete_msg(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['doithuong'])
def doithuong_cmd(m):
    show_doi_thuong_menu(m.chat.id)

def show_doi_thuong_menu(chat_id):
    text = (
        f"🎁 *HỆ THỐNG ĐỔI THƯỞNG KEY*\n"
        f"──────────────────────────\n"
        f"Chọn mốc TCOIN bạn muốn đổi:\n\n"
        f"1️⃣ 3,000 TCOIN ➔ Key 1 Ngày\n"
        f"2️⃣ 10,000 TCOIN ➔ Key 1 Tuần\n"
        f"3️⃣ 30,000 TCOIN ➔ Key 1 Tháng"
    )
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎟️ Đổi Key 1 Ngày (3k TCOIN)", callback_data="doi_1ngay"),
        InlineKeyboardButton("🎟️ Đổi Key 1 Tuần (10k TCOIN)", callback_data="doi_1tuan"),
        InlineKeyboardButton("🎟️ Đổi Key 1 Tháng (30k TCOIN)", callback_data="doi_1thang")
    )
    send_auto_delete_msg(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data
    
    if data.startswith("v_"):
        web_key = data.split("_")[1]
        handle_vuot_link(chat_id, user_id, web_key)
    elif data == "menu_tk":
        show_account_info(chat_id, user_id, call.from_user.first_name)
    elif data == "menu_doithuong":
        show_doi_thuong_menu(chat_id)
    elif data.startswith("doi_"):
        package = data.split("_")[1]
        process_doi_thuong(chat_id, user_id, package)
        
    bot.answer_callback_query(call.id)

def process_doi_thuong(chat_id, user_id, package):
    costs = {"1ngay": 3000, "1tuan": 10000, "1thang": 30000}
    names = {"1ngay": "Key 1 Ngày", "1tuan": "Key 1 Tuần", "1thang": "Key 1 Tháng"}
    required_tcoin = costs[package]
    
    user_id_str = str(user_id)
    try:
        user_data = requests.get(f"{FIREBASE_URL}users/{user_id_str}.json", timeout=5).json() or {}
        current_tcoin = user_data.get("tcoin", 0)
    except:
        current_tcoin = 0
        
    if current_tcoin < required_tcoin:
        send_auto_delete_msg(chat_id, f"❌ Bạn không đủ TCOIN! Cần {required_tcoin} TCOIN nhưng bạn chỉ có {current_tcoin} TCOIN.")
        return
        
    new_tcoin = current_tcoin - required_tcoin
    generated_key = f"BANDVIP-{package.upper()}-{int(time.time())}"
    
    requests.patch(f"{FIREBASE_URL}users/{user_id_str}.json", json={"tcoin": new_tcoin})
    
    send_auto_delete_msg(
        chat_id, 
        f"🎉 *ĐỔI THƯỞNG THÀNH CÔNG!*\n"
        f"• Phần quà: *{names[package]}*\n"
        f"• Mã Key của bạn: `{generated_key}`\n"
        f"• TCOIN còn lại: {new_tcoin} TCOIN"
    )

print("Bot TCOIN đang chạy...")
bot.infinity_polling(skip_pending=True)
