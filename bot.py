import telebot
import time
import requests
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

TOKEN = "8928629119:AAEsNQyk81o5zSmykc5RO8jRJCBZ0zu7KOI"
FIREBASE_URL = "https://tcoin-e983b-default-rtdb.firebaseio.com/"

bot = telebot.TeleBot(TOKEN)

# Đã xác định Thread ID của "Band FF" là 1
ALLOWED_THREAD_ID = 1

CONFIG_WEB = {
    "link4m": {"limit": 2, "tcoin": 1000, "name": "Link4M", "api_token": "667da5e0512ac00cba52fb6f"}
}

bot.set_my_commands([
    BotCommand("start", "Mở menu chính & vượt link nhận TCOIN"),
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

def send_auto_delete_msg(chat_id, text, parse_mode="Markdown", reply_markup=None, reply_to_message_id=None, message_thread_id=None):
    kwargs = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": reply_markup,
        "reply_to_message_id": reply_to_message_id
    }
    if message_thread_id:
        kwargs["message_thread_id"] = message_thread_id
        
    sent = bot.send_message(**kwargs)
    t = threading.Thread(target=delete_message_later, args=(chat_id, sent.message_id, 600))
    t.daemon = True
    t.start()
    return sent

def edit_or_send(call, text, reply_markup=None, parse_mode="Markdown"):
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
    except:
        thread_id = getattr(call.message, 'message_thread_id', None)
        send_auto_delete_msg(call.message.chat.id, text, parse_mode=parse_mode, reply_markup=reply_markup, message_thread_id=thread_id)

def check_thread(message):
    thread_id = getattr(message, 'message_thread_id', None)
    if ALLOWED_THREAD_ID is not None and thread_id != ALLOWED_THREAD_ID:
        return False
    return True

@bot.message_handler(func=lambda m: not check_thread(m))
def ignore_other_threads(message):
    pass

@bot.message_handler(commands=['start', 'help'])
def start_cmd(m):
    user_name = m.from_user.first_name
    thread_id = getattr(m, 'message_thread_id', None)
    text = (
        f"🤖 *HỆ THỐNG VƯỢT LINK & TÍCH LŨY TCOIN*\n"
        f"──────────────────────────\n"
        f"Chào {user_name}! Hoàn thành vượt link Link4M để nhận thưởng TCOIN và đổi key VIP.\n"
        f"Chọn dịch vụ bên dưới để bắt đầu:"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🌐 Vượt Link4M (+1,000 TCOIN)", callback_data="v_link4m"),
        InlineKeyboardButton("👤 Tài Khoản & TCOIN", callback_data="menu_tk"),
        InlineKeyboardButton("🎁 Đổi Thưởng Key", callback_data="menu_doithuong")
    )
    
    send_auto_delete_msg(m.chat.id, text, reply_markup=markup, reply_to_message_id=m.message_id, message_thread_id=thread_id)

def handle_vuot_link(call, web_key):
    user_id = call.from_user.id
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
        bot.answer_callback_query(call.id, f"Bạn đã đạt giới hạn {limit}/{limit} lần vượt cho {cfg['name']} hôm nay!", show_alert=True)
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
    final_url = f"https://link4m.co/st?api={token}&url={target_url}"

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(f"🔗 NHẤN ĐỂ VƯỢT {cfg['name']}", url=final_url),
        InlineKeyboardButton("⬅️ Quay lại Menu Chính", callback_data="menu_home")
    )
    
    text = (
        f"🎁 *VƯỢT LINK {cfg['name']} ({count+1}/{limit})*\n"
        f"• Trạng thái: *Chờ hoàn thành*\n"
        f"• Thưởng nhận được: *+{cfg['tcoin']} TCOIN*\n"
        f"Bấm vào nút bên dưới để bắt đầu:"
    )
    edit_or_send(call, text, reply_markup=markup)

@bot.message_handler(commands=['tk'])
def tk_cmd(m):
    thread_id = getattr(m, 'message_thread_id', None)
    show_account_info_msg(m.chat.id, m.from_user.id, m.from_user.first_name, m.message_id, thread_id)

def show_account_info_msg(chat_id, user_id, user_name, reply_to_id=None, thread_id=None):
    user_id_str = str(user_id)
    today_str = time.strftime("%Y-%m-%d")
    try:
        user_data = requests.get(f"{FIREBASE_URL}users/{user_id_str}.json", timeout=5).json() or {}
        tcoin = user_data.get("tcoin", 0)
        today_data = user_data.get(today_str, {})
        l4m_c = today_data.get("link4m", 0)
    except:
        tcoin, l4m_c = 0, 0

    text = (
        f"👤 *THÔNG TIN TÀI KHOẢN*\n"
        f"• Tên: {user_name}\n"
        f"• ID Telegram: `{user_id}`\n"
        f"• 💰 TCOIN hiện có: *{tcoin} TCOIN*\n\n"
        f"📊 *Số lượt vượt Link4M hôm nay*: {l4m_c}/2"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 Làm mới", callback_data="menu_tk"),
        InlineKeyboardButton("⬅️ Quay lại", callback_data="menu_home")
    )
    send_auto_delete_msg(chat_id, text, reply_markup=markup, reply_to_message_id=reply_to_id, message_thread_id=thread_id)

def show_account_info_call(call):
    user_id = call.from_user.id
    user_id_str = str(user_id)
    today_str = time.strftime("%Y-%m-%d")
    try:
        user_data = requests.get(f"{FIREBASE_URL}users/{user_id_str}.json", timeout=5).json() or {}
        tcoin = user_data.get("tcoin", 0)
        today_data = user_data.get(today_str, {})
        l4m_c = today_data.get("link4m", 0)
    except:
        tcoin, l4m_c = 0, 0

    text = (
        f"👤 *THÔNG TIN TÀI KHOẢN*\n"
        f"• Tên: {call.from_user.first_name}\n"
        f"• ID Telegram: `{user_id}`\n"
        f"• 💰 TCOIN hiện có: *{tcoin} TCOIN*\n\n"
        f"📊 *Số lượt vượt Link4M hôm nay*: {l4m_c}/2"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 Làm mới", callback_data="menu_tk"),
        InlineKeyboardButton("⬅️ Quay lại", callback_data="menu_home")
    )
    edit_or_send(call, text, reply_markup=markup)

@bot.message_handler(commands=['doithuong'])
def doithuong_cmd(m):
    thread_id = getattr(m, 'message_thread_id', None)
    show_doi_thuong_msg(m.chat.id, m.message_id, thread_id)

def show_doi_thuong_msg(chat_id, reply_to_id=None, thread_id=None):
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
        InlineKeyboardButton("🎟️ Đổi Key 1 Tháng (30k TCOIN)", callback_data="doi_1thang"),
        InlineKeyboardButton("⬅️ Quay lại Menu Chính", callback_data="menu_home")
    )
    send_auto_delete_msg(chat_id, text, reply_markup=markup, reply_to_message_id=reply_to_id, message_thread_id=thread_id)

def show_doi_thuong_call(call):
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
        InlineKeyboardButton("🎟️ Đổi Key 1 Tháng (30k TCOIN)", callback_data="doi_1thang"),
        InlineKeyboardButton("⬅️ Quay lại Menu Chính", callback_data="menu_home")
    )
    edit_or_send(call, text, reply_markup=markup)

def show_home_menu(call):
    text = (
        f"🤖 *HỆ THỐNG VƯỢT LINK & TÍCH LŨY TCOIN*\n"
        f"──────────────────────────\n"
        f"Chào {call.from_user.first_name}! Hoàn thành vượt link Link4M để nhận thưởng TCOIN và đổi key VIP.\n"
        f"Chọn dịch vụ bên dưới để bắt đầu:"
    )
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🌐 Vượt Link4M (+1,000 TCOIN)", callback_data="v_link4m"),
        InlineKeyboardButton("👤 Tài Khoản & TCOIN", callback_data="menu_tk"),
        InlineKeyboardButton("🎁 Đổi Thưởng Key", callback_data="menu_doithuong")
    )
    edit_or_send(call, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    
    if data == "menu_home":
        show_home_menu(call)
    elif data.startswith("v_"):
        web_key = data.split("_")[1]
        handle_vuot_link(call, web_key)
    elif data == "menu_tk":
        show_account_info_call(call)
    elif data == "menu_doithuong":
        show_doi_thuong_call(call)
    elif data.startswith("doi_"):
        package = data.split("_")[1]
        process_doi_thuong(call, package)
        
    bot.answer_callback_query(call.id)

def process_doi_thuong(call, package):
    user_id = call.from_user.id
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
        bot.answer_callback_query(call.id, f"❌ Bạn không đủ TCOIN! Cần {required_tcoin} TCOIN nhưng bạn có {current_tcoin} TCOIN.", show_alert=True)
        return
        
    new_tcoin = current_tcoin - required_tcoin
    generated_key = f"BANDVIP-{package.upper()}-{int(time.time())}"
    
    requests.patch(f"{FIREBASE_URL}users/{user_id_str}.json", json={"tcoin": new_tcoin})
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬅️ Quay lại Menu Chính", callback_data="menu_home"))
    
    text = (
        f"🎉 *ĐỔI THƯỞNG THÀNH CÔNG!*\n"
        f"• Phần quà: *{names[package]}*\n"
        f"• Mã Key của bạn: `{generated_key}`\n"
        f"• TCOIN còn lại: {new_tcoin} TCOIN"
    )
    edit_or_send(call, text, reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    text_lower = message.text.lower()
    chat_id = message.chat.id
    thread_id = getattr(message, 'message_thread_id', None)
    
    if "admin" in text_lower or "chủ" in text_lower:
        reply_text = "📞 Vui lòng liên hệ Admin nếu bạn cần hỗ trợ thêm nhé!"
    elif "chào" in text_lower or "hi" in text_lower or "hello" in text_lower:
        reply_text = f"👋 Chào {message.from_user.first_name}! Bạn hãy bấm /start để mở menu chính vượt link tích lũy TCOIN."
    else:
        reply_text = "🤖 Tôi là bot quản lý TCOIN tự động. Vui lòng sử dụng lệnh `/start` để mở bảng điều khiển chính."
        
    send_auto_delete_msg(chat_id, reply_text, reply_to_message_id=message.message_id, message_thread_id=thread_id)

print("Bot TCOIN (Chỉ chạy ở Band FF - Thread ID: 1) đang chạy...")
bot.infinity_polling(skip_pending=True)
                        
