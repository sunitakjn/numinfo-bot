import telebot
import requests
import threading
import time
import sqlite3
from telebot import types

# --- CONFIGURATIONS ---
API_TOKEN = '8600054596:AAFkDYPWhxlf9B5i8_-KrFksF0Fal09yUMA'
OWNER_ID = 8442352135
# API URL Updated
API_URL_TEMPLATE = "https://num-info-rajput.vercel.app/search?num={mobile}"

CHANNELS = {
    "1 🚀": {"id": "@snxhub", "url": "https://t.me/snxhub"},
    "2 🚀": {"id": "@snnetwork7", "url": "https://t.me/snnetwork7"},
    "3 🚀": {"id": "@snxhub1", "url": "https://t.me/snxhub1"}
}

bot = telebot.TeleBot(API_TOKEN)

# --- DATABASE ENGINE ---
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

def init_db():
    db_query('CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY)')
    db_query('CREATE TABLE IF NOT EXISTS personal_users (id INTEGER PRIMARY KEY)')
    db_query('CREATE TABLE IF NOT EXISTS unlimited_users (id INTEGER PRIMARY KEY)')
    db_query('CREATE TABLE IF NOT EXISTS user_searches (user_id INTEGER PRIMARY KEY, count INTEGER, date TEXT)')

init_db()

# --- HELPERS ---
def auto_delete(chat_id, message_id, delay=60):
    def delete():
        time.sleep(delay)
        try: bot.delete_message(chat_id, message_id)
        except: pass
    threading.Thread(target=delete).start()

def get_search_info(user_id):
    today = time.strftime("%Y-%m-%d")
    res = db_query('SELECT count, date FROM user_searches WHERE user_id = ?', (user_id,), fetch=True)
    if not res or res[0][1] != today:
        db_query('INSERT OR REPLACE INTO user_searches (user_id, count, date) VALUES (?, ?, ?)', (user_id, 0, today))
        return 0
    return res[0][0]

def check_force_join(user_id):
    for key, data in CHANNELS.items():
        try:
            status = bot.get_chat_member(data['id'], user_id).status
            if status in ['left', 'kicked']: return False
        except: return False
    return True

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['approvenumgc'])
def app_gc(message):
    if message.from_user.id == OWNER_ID:
        db_query('INSERT OR IGNORE INTO groups (id) VALUES (?)', (message.chat.id,))
        bot.reply_to(message, f"✅ Group `{message.chat.id}` Approved.")

@bot.message_handler(commands=['approvenum'])
def app_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            db_query('INSERT OR IGNORE INTO personal_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"👤 User `{uid}` Approved.")
        except: bot.reply_to(message, "Usage: `/approvenum ID`")

# --- SEARCH LOGIC ---
@bot.message_handler(commands=['num'])
def search_num(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if not check_force_join(user_id):
        markup = types.InlineKeyboardMarkup()
        for key, data in CHANNELS.items():
            markup.add(types.InlineKeyboardButton(f"Join {key}", url=data['url']))
        markup.add(types.InlineKeyboardButton("Verify ✅", callback_data="verify_join"))
        bot.reply_to(message, "❌ **Please join channels first!**", reply_markup=markup)
        return

    approved_gcs = [r[0] for r in db_query('SELECT id FROM groups', fetch=True)]
    approved_users = [r[0] for r in db_query('SELECT id FROM personal_users', fetch=True)]
    unlimited_users = [r[0] for r in db_query('SELECT id FROM unlimited_users', fetch=True)]

    if message.chat.type in ['group', 'supergroup'] and chat_id not in approved_gcs: return
    if message.chat.type == 'private' and user_id != OWNER_ID and user_id not in approved_users:
        bot.reply_to(message, "❌ No Personal Access.")
        return

    is_unl = (user_id == OWNER_ID or user_id in unlimited_users)
    count = get_search_info(user_id)
    if not is_unl and count >= 15:
        bot.reply_to(message, "⚠️ Daily Limit (15) Reached!")
        return

    try:
        mobile = message.text.split()[1]
    except:
        bot.reply_to(message, "Usage: `/num 91xxxxxx`")
        return

    status = bot.reply_to(message, "🔍 Searching...")
    try:
        response = requests.get(API_URL_TEMPLATE.format(mobile=mobile), timeout=15)
        res = response.json()

        # Complex Data Extraction Logic to prevent "No Data Found"
        records = []
        if isinstance(res, list):
            records = res
        elif isinstance(res, dict):
            # Check for common data keys
            records = res.get("data") or res.get("records") or res.get("result")
            # If no keys but dictionary has direct info
            if not records and (res.get("NAME") or res.get("name")):
                records = [res]
        
        if not records:
            bot.edit_message_text("No Data Found ⚠️", chat_id, status.message_id)
            return

        db_query('UPDATE user_searches SET count = count + 1 WHERE user_id = ?', (user_id,))
        rem = "Unlimited" if is_unl else (15 - (count + 1))
        
        txt = f"📊 **TOTAL RECORDS: {len(records) if isinstance(records, list) else 1}**\n"
        txt += f"📉 **SEARCHES LEFT: {rem}**\n\n"
        
        for i, r in enumerate(records if isinstance(records, list) else [records], 1):
            if i > 10: break # Avoid too long messages
            name = r.get('NAME') or r.get('name') or "N/A"
            fname = r.get('fname') or r.get('FNAME') or r.get('father_name') or "N/A"
            addr = r.get('ADDRESS') or r.get('address') or "N/A"
            phone = r.get('MOBILE') or r.get('mobile') or r.get('num') or mobile
            
            txt += f"**RECORD:** {i}\n"
            txt += f"📱 **MOB:** `{phone}`\n"
            txt += f"👤 **NAME:** `{name}`\n"
            txt += f"🤠 **FATHER:** `{fname}`\n"
            txt += f"🏠 **ADR:** `{addr}`\n"
            txt += "───────────────────\n"
        
        txt += "\n⚠️ *This message will be deleted in 1 minute.*"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("𝐒𝐍 𝐗 𝐃𝐀𝐃 🦁", url="https://t.me/sxdad"))
        bot.edit_message_text(txt[:4000], chat_id, status.message_id, parse_mode="Markdown", reply_markup=markup)
        
        auto_delete(chat_id, status.message_id, 60)
    except Exception as e:
        print(f"Error: {e}")
        bot.edit_message_text("No Data Found ⚠️", chat_id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify(call):
    if check_force_join(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

# Increased polling timeout for stability
bot.infinity_polling(timeout=90, long_polling_timeout=90)
