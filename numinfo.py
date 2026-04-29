import telebot
import requests
import threading
import time
import sqlite3
from telebot import types

# --- CONFIGURATIONS ---
API_TOKEN = '8600054596:AAFkDYPWhxlf9B5i8_-KrFksF0Fal09yUMA'
OWNER_ID = 8442352135
API_URL_TEMPLATE = "https://hitackgrop-19xe.vercel.app/get_data?key=ottt&mobile={mobile}"

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

# --- 1. GROUP COMMANDS ---
@bot.message_handler(commands=['approvenumgc'])
def app_gc(message):
    if message.from_user.id == OWNER_ID:
        db_query('INSERT OR IGNORE INTO groups (id) VALUES (?)', (message.chat.id,))
        bot.reply_to(message, f"✅ Group `{message.chat.id}` Approved.")

@bot.message_handler(commands=['disapprovenumgc'])
def dis_gc(message):
    if message.from_user.id == OWNER_ID:
        db_query('DELETE FROM groups WHERE id = ?', (message.chat.id,))
        bot.reply_to(message, "❌ Group Removed.")

@bot.message_handler(commands=['disaapprovenumgcall'])
def dis_all_gc(message):
    if message.from_user.id == OWNER_ID:
        db_query('DELETE FROM groups')
        bot.reply_to(message, "🗑 All Groups Removed.")

@bot.message_handler(commands=['listapprovenumgc'])
def list_gc(message):
    if message.from_user.id == OWNER_ID:
        rows = db_query('SELECT id FROM groups', fetch=True)
        text = "👥 **Approved Groups:**\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "No Groups."
        bot.reply_to(message, text, parse_mode="Markdown")

# --- 2. PERSONAL COMMANDS ---
@bot.message_handler(commands=['approvenum'])
def app_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            db_query('INSERT OR IGNORE INTO personal_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"👤 User `{uid}` Approved.")
        except: bot.reply_to(message, "Usage: `/approvenum 12345`")

@bot.message_handler(commands=['disapprovenum'])
def dis_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            db_query('DELETE FROM personal_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ User `{uid}` Removed.")
        except: pass

@bot.message_handler(commands=['disapprovenumall'])
def dis_all_user(message):
    if message.from_user.id == OWNER_ID:
        db_query('DELETE FROM personal_users')
        bot.reply_to(message, "🗑 All Personal Users Removed.")

@bot.message_handler(commands=['listapprovenum'])
def list_user(message):
    if message.from_user.id == OWNER_ID:
        rows = db_query('SELECT id FROM personal_users', fetch=True)
        text = "👤 **Personal Users:**\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "Empty."
        bot.reply_to(message, text, parse_mode="Markdown")

# --- 3. UNLIMITED COMMANDS ---
@bot.message_handler(commands=['unlimitednum'])
def app_unl(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            db_query('INSERT OR IGNORE INTO unlimited_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"⭐ User `{uid}` is Unlimited.")
        except: pass

@bot.message_handler(commands=['disunlimitednum'])
def dis_unl(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            db_query('DELETE FROM unlimited_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ User `{uid}` Unlimited Removed.")
        except: pass

@bot.message_handler(commands=['disunlimitednumall'])
def dis_all_unl(message):
    if message.from_user.id == OWNER_ID:
        db_query('DELETE FROM unlimited_users')
        bot.reply_to(message, "🗑 All Unlimited Removed.")

@bot.message_handler(commands=['listunlimitednum'])
def list_unl(message):
    if message.from_user.id == OWNER_ID:
        rows = db_query('SELECT id FROM unlimited_users', fetch=True)
        text = "⭐ **Unlimited Users:**\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "Empty."
        bot.reply_to(message, text, parse_mode="Markdown")

# --- 4. BROADCAST ---
@bot.message_handler(commands=['broadcastnum'])
def bcast(message):
    if message.from_user.id == OWNER_ID:
        msg_text = message.text.replace('/broadcastnum', '').strip()
        if not msg_text: return
        groups = db_query('SELECT id FROM groups', fetch=True)
        for g_id in groups:
            try: bot.send_message(g_id[0], f"📢 **BROADCAST**\n\n{msg_text}")
            except: continue
        bot.reply_to(message, "✅ Broadcast sent to all groups.")

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
        res = requests.get(API_URL_TEMPLATE.format(mobile=mobile), timeout=10).json()
        records = res.get("data", [])
        if not records:
            bot.edit_message_text("No Data Found ⚠️", chat_id, status.message_id)
            return

        db_query('UPDATE user_searches SET count = count + 1 WHERE user_id = ?', (user_id,))
        rem = "Unlimited" if is_unl else (15 - (count + 1))
        
        txt = f"📊 **TOTAL: {res.get('total_records', 0)}**\n📉 **REMAINING: {rem}**\n\n"
        for i, r in enumerate(records, 1):
            alt = r.get("alt") or r.get("ALT") or "N/A"
            txt += f"RECORDS: {i}\n📱 MOB: {r.get('MOBILE', mobile)}\n👤 NAME: {r.get('NAME', 'N/A')}\n🤠 FATHER: {r.get('fname', 'N/A')}\n🏠 ADR: {r.get('ADDRESS', 'N/A')}\n📞 ALT: {alt}\n───────────────────\n"
        
        txt += "\n⚠️ *This message will be deleted in 1 minute.*"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("𝐒𝐍 𝐗 𝐃𝐀𝐃 🦁", url="https://t.me/sxdad"))
        bot.edit_message_text(txt[:4000], chat_id, status.message_id, parse_mode="Markdown", reply_markup=markup)
        
        auto_delete(chat_id, status.message_id, 60)
    except:
        bot.edit_message_text("No Data Found ⚠️", chat_id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify(call):
    if check_force_join(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Join all 3 first!", show_alert=True)

bot.infinity_polling()
