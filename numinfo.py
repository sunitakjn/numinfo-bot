import telebot
import requests
import threading
import time
import sqlite3
from telebot import types

# --- CONFIGURATIONS ---
# Replace 'YOUR_NEW_API_TOKEN' with your actual bot token
API_TOKEN = 'YOUR_NEW_API_TOKEN'
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
        # Added timeout to handle concurrent requests in groups
        conn = sqlite3.connect('bot_data.db', timeout=20)
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
        except Exception: 
            return False # Usually happens if bot is not admin in channel
    return True

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['approvenumgc', 'disapprovenumgc', 'listapprovenumgc'])
def handle_group_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Unauthorized.")
        return
    
    cmd = message.text.split()[0].lower()
    if 'approvenumgc' in cmd:
        db_query('INSERT OR IGNORE INTO groups (id) VALUES (?)', (message.chat.id,))
        bot.reply_to(message, f"✅ Group `{message.chat.id}` Approved.")
    elif 'disapprovenumgc' in cmd:
        db_query('DELETE FROM groups WHERE id = ?', (message.chat.id,))
        bot.reply_to(message, "❌ Group Removed.")
    elif 'listapprovenumgc' in cmd:
        rows = db_query('SELECT id FROM groups', fetch=True)
        text = "👥 Approved Groups:\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "No groups."
        bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['approvenum', 'disapprovenum', 'listapprovenum'])
def handle_user_admin(message):
    if message.from_user.id != OWNER_ID: return
    cmd = message.text.split()[0].lower()
    try:
        if 'list' in cmd:
            rows = db_query('SELECT id FROM personal_users', fetch=True)
            text = "👤 Users:\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "No users."
            bot.reply_to(message, text, parse_mode="Markdown")
            return
        
        uid = int(message.text.split()[1])
        if 'approvenum' == cmd[1:]: # handle /approvenum
            db_query('INSERT OR IGNORE INTO personal_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"✅ User `{uid}` access granted.")
        else:
            db_query('DELETE FROM personal_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ User `{uid}` access revoked.")
    except: bot.reply_to(message, "⚠️ Usage: `/[command] [User_ID]`")

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
        bot.reply_to(message, "❌ **Access Denied!**\nPlease join our channels to use this bot.", reply_markup=markup)
        return

    # Permissions Check
    is_owner = (user_id == OWNER_ID)
    approved_gcs = [r[0] for r in db_query('SELECT id FROM groups', fetch=True) or []]
    approved_users = [r[0] for r in db_query('SELECT id FROM personal_users', fetch=True) or []]
    unlimited_users = [r[0] for r in db_query('SELECT id FROM unlimited_users', fetch=True) or []]

    if message.chat.type in ['group', 'supergroup'] and chat_id not in approved_gcs:
        bot.reply_to(message, "❌ This group is not authorized.")
        return
    if message.chat.type == 'private' and not is_owner and user_id not in approved_users:
        bot.reply_to(message, "❌ Private access is for premium users only.")
        return

    is_unl = (is_owner or user_id in unlimited_users)
    count = get_search_info(user_id)
    if not is_unl and count >= 15:
        bot.reply_to(message, "⚠️ Daily limit reached (15/15). Try again tomorrow.")
        return

    try:
        mobile = message.text.split()[1]
        if len(mobile) < 10: raise ValueError
    except:
        bot.reply_to(message, "⚠️ Usage: `/num [10_Digit_Number]`")
        return

    status = bot.reply_to(message, "🔍 Searching database...")
    
    try:
        response = requests.get(API_URL_TEMPLATE.format(mobile=mobile), timeout=15)
        res = response.json()

        # Dynamic data parsing
        records = []
        if isinstance(res, list): records = res
        elif isinstance(res, dict):
            records = res.get("data") or res.get("records") or res.get("result") or ([res] if 'name' in str(res).lower() else [])
        
        if not records:
            bot.edit_message_text(f"⚠️ No data found for `{mobile}`.", chat_id, status.message_id)
            return

        # Update search count
        db_query('UPDATE user_searches SET count = count + 1 WHERE user_id = ?', (user_id,))
        rem = "Unlimited" if is_unl else (15 - (count + 1))
        
        txt = f"📊 **TOTAL RECORDS: {len(records)}**\n📉 **REMAINING: {rem}**\n\n"
        for i, r in enumerate(records, 1):
            if i > 5: break # Limit output length to prevent Telegram message limits
            name = r.get('NAME') or r.get('name') or "N/A"
            fname = r.get('FATHER') or r.get('fname') or "N/A"
            addr = r.get('ADDRESS') or r.get('address') or "N/A"
            
            txt += f"**REC {i}:**\n👤 **NAME:** `{name}`\n🤠 **FATHER:** `{fname}`\n🏠 **ADR:** `{addr}`\n───────────────────\n"
        
        txt += "\n🗑 *Deleting in 60s for privacy.*"
        bot.edit_message_text(txt[:4000], chat_id, status.message_id, parse_mode="Markdown")
        auto_delete(chat_id, status.message_id, 60)
        
    except Exception as e:
        bot.edit_message_text(f"⚠️ API Error: Connection timed out.", chat_id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify(call):
    if check_force_join(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Access Granted!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Please join all channels first.", show_alert=True)

# Run Bot
print("Bot is running...")
bot.infinity_polling()
