import telebot
import requests
import threading
import time
import sqlite3
from telebot import types

# --- CONFIGURATIONS ---
API_TOKEN = '8600054596:AAFkDYPWhxlf9B5i8_-KrFksF0Fal09yUMA'
OWNER_ID = 8442352135
# Nayi API bina kisi key ke
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

# --- SEARCH LOGIC (SAME UI AS REQUESTED) ---
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
        res = requests.get(API_URL_TEMPLATE.format(mobile=mobile), timeout=15).json()
        
        # Structure set karna naye API ke liye
        records = []
        if
        
