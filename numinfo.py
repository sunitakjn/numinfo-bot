import telebot
import requests
import threading
import time
import sqlite3
from telebot import types

# --- CONFIGURATIONS ---
API_TOKEN = '8600054596:AAFkDYPWhxlf9B5i8_-KrFksF0Fal09yUMA'
OWNER_ID = 8442352135
API_URL_TEMPLATE = "https://num-info-rajput.vercel.app/search?num={mobile}"

CHANNELS = {
    "1 🚀": {"id": "@snxhub", "url": "https://t.me/snxhub"},
    "2 🚀": {"id": "@snnetwork7", "url": "https://t.me/snnetwork7"},
    "3 🚀": {"id": "@snxhub1", "url": "https://t.me/snxhub1"}
}

bot = telebot.TeleBot(API_TOKEN)

# --- DATABASE ENGINE ---
def db_query(query, params=(), fetch=False):
    try:
        conn = sqlite3.connect('bot_data.db', timeout=30)
        cursor = conn.cursor()
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return res
    except Exception as e:
        print(f"Database Error: {e}")
        return None

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
    threading.Thread(target=delete, daemon=True).start()

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
@bot.message_handler(commands=['approvenumgc', 'disapprovenumgc', 'disaapprovenumgcall', 'listapprovenumgc'])
def handle_group_cmds(message):
    if message.from_user.id != OWNER_ID: return
    cmd = message.text.split()[0].lower()
    
    if 'approvenumgc' in cmd:
        db_query('INSERT OR IGNORE INTO groups (id) VALUES (?)', (message.chat.id,))
        bot.reply_to(message, "✅ Group Approved.")
    elif 'disapprovenumgc' in cmd:
        db_query('DELETE FROM groups WHERE id = ?', (message.chat.id,))
        bot.reply_to(message, "❌ Group Removed.")
    elif 'disaapprovenumgcall' in cmd:
        db_query('DELETE FROM groups')
        bot.reply_to(message, "🗑 All Groups Cleared.")
    elif 'listapprovenumgc' in cmd:
        rows = db_query('SELECT id FROM groups', fetch=True)
        text = "👥 **Approved Groups:**\n\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "No groups."
        bot.reply_to(message, text, parse_mode="Markdown")

# --- 2. USER COMMANDS (Personal & Unlimited) ---
@bot.message_handler(commands=['approvenum', 'disapprovenum', 'disapprovenumall', 'listapprovenum', 'unlimitednum', 'disunlimitednum', 'disunlimitednumall', 'listunlimitednum'])
def handle_user_cmds(message):
    if message.from_user.id != OWNER_ID: return
    cmd = message.text.split()[0].lower()
    
    try:
        if 'list' in cmd:
            table = 'personal_users' if 'approvenum' in cmd else 'unlimited_users'
            rows = db_query(f'SELECT id FROM {table}', fetch=True)
            bot.reply_to(message, f"📋 List:\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "Empty.")
            return

        if 'all' in cmd:
            table = 'personal_users' if 'approvenum' in cmd else 'unlimited_users'
            db_query(f'DELETE FROM {table}')
            bot.reply_to(message, "🗑 Cleared all.")
            return

        uid = int(message.text.split()[1])
        if cmd.startswith('/approve'):
            db_query('INSERT OR IGNORE INTO personal_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"✅ User {uid} Granted Access.")
        elif cmd.startswith('/disapprove'):
            db_query('DELETE FROM personal_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ User {uid} Access Removed.")
        elif cmd.startswith('/unlimited'):
            db_query('INSERT OR IGNORE INTO unlimited_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"⭐ User {uid} is now Unlimited.")
        elif cmd.startswith('/disunlimited'):
            db_query('DELETE FROM unlimited_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ User {uid} Unlimited Removed.")
    except: bot.reply_to(message, "⚠️ Error in Command.")

# --- 3. BROADCAST ---
@bot.message_handler(commands=['broadcastnum'])
def broadcast(message):
    if message.from_user.id != OWNER_ID: return
    text = message.text.replace('/broadcastnum', '').strip()
    if not text: return
    groups = db_query('SELECT id FROM groups', fetch=True)
    for g in groups:
        try: bot.send_message(g[0], f"📢 **BROADCAST**\n\n{text}", parse_mode="Markdown")
        except: pass
    bot.reply_to(message, "✅ Done.")

# --- 4. SEARCH LOGIC (FIXED N/A) ---
@bot.message_handler(commands=['num'])
def search_num(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if not check_force_join(user_id):
        markup = types.InlineKeyboardMarkup()
        for key, data in CHANNELS.items():
            markup.add(types.InlineKeyboardButton(f"Join {key}", url=data['url']))
        markup.add(types.InlineKeyboardButton("Verify ✅", callback_data="verify_join"))
        bot.reply_to(message, "❌ **Join Channels First!**", reply_markup=markup)
        return

    # Permissions
    is_owner = (user_id == OWNER_ID)
    approved_gcs = [r[0] for r in db_query('SELECT id FROM groups', fetch=True) or []]
    approved_users = [r[0] for r in db_query('SELECT id FROM personal_users', fetch=True) or []]
    unlimited_users = [r[0] for r in db_query('SELECT id FROM unlimited_users', fetch=True) or []]

    if message.chat.type in ['group', 'supergroup'] and chat_id not in approved_gcs:
        bot.reply_to(message, "❌ Group Not Approved.")
        return
    if message.chat.type == 'private' and not is_owner and user_id not in approved_users:
        bot.reply_to(message, "❌ Personal Access Required.")
        return

    is_unl = (is_owner or user_id in unlimited_users)
    count = get_search_info(user_id)
    if not is_unl and count >= 15:
        bot.reply_to(message, "⚠️ Daily Limit (15/15) Reached.")
        return

    try:
        mobile = message.text.split()[1]
    except:
        bot.reply_to(message, "⚠️ Usage: `/num [Number]`")
        return

    status = bot.reply_to(message, "🔍 Processing...")

    try:
        res = requests.get(API_URL_TEMPLATE.format(mobile=mobile), timeout=15).json()
        
        # Parse Data
        records = res if isinstance(res, list) else (res.get("data") or res.get("records") or [res])
        valid_records = [r for r in records if isinstance(r, dict) and len(r) > 1]

        if not valid_records:
            bot.edit_message_text(f"⚠️ No data found for `{mobile}`.", chat_id, status.message_id)
            return

        db_query('UPDATE
        
