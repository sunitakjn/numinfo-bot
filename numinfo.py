import telebot
import requests
import threading
import time
import sqlite3
import os
from telebot import types

# --- CONFIGURATIONS ---
BOT_TOKEN = '8600054596:AAFkDYPWhxlf9B5i8_-KrFksF0Fal09yUMA'
OWNER_ID = 8442352135
API_URL_TEMPLATE = "https://num-info-rajput.vercel.app/search?num={mobile}"
DELETE_TIMER = 60 

CHANNELS = {
    "1 🚀": {"id": "@snxhub", "url": "https://t.me/snxhub"},
    "2 🚀": {"id": "@snnetwork7", "url": "https://t.me/snnetwork7"},
    "3 🚀": {"id": "@snxhub1", "url": "https://t.me/snxhub1"}
}

bot = telebot.TeleBot(BOT_TOKEN)

# --- DATABASE ---
def db_query(query, params=(), fetch=False):
    try:
        conn = sqlite3.connect('bot_data.db', timeout=30)
        cursor = conn.cursor()
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return res
    except: return None

def init_db():
    db_query('CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY)')
    db_query('CREATE TABLE IF NOT EXISTS personal_users (id INTEGER PRIMARY KEY)')
    db_query('CREATE TABLE IF NOT EXISTS unlimited_users (id INTEGER PRIMARY KEY)')
    db_query('CREATE TABLE IF NOT EXISTS user_searches (user_id INTEGER PRIMARY KEY, count INTEGER, date TEXT)')

init_db()

# --- HELPERS ---
def check_force_join(user_id):
    for key, data in CHANNELS.items():
        try:
            status = bot.get_chat_member(data['id'], user_id).status
            if status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def get_search_info(user_id):
    today = time.strftime("%Y-%m-%d")
    res = db_query('SELECT count, date FROM user_searches WHERE user_id = ?', (user_id,), fetch=True)
    if not res or res[0][1] != today:
        db_query('INSERT OR REPLACE INTO user_searches (user_id, count, date) VALUES (?, ?, ?)', (user_id, 0, today))
        return 0
    return res[0][0]

def delete_msg(chat_id, message_id, delay):
    time.sleep(delay)
    try: bot.delete_message(chat_id, message_id)
    except: pass

# --- SEARCH COMMAND WITH NEW UI ---
@bot.message_handler(commands=['num'])
def search_num(message):
    user_id = message.from_user.id
    if not check_force_join(user_id):
        markup = types.InlineKeyboardMarkup()
        for key, data in CHANNELS.items():
            markup.add(types.InlineKeyboardButton(f"Join {key}", url=data['url']))
        markup.add(types.InlineKeyboardButton("Verify ✅", callback_data="verify_join"))
        return bot.reply_to(message, "❌ **Please join all channels first!**", reply_markup=markup)

    is_owner = (user_id == OWNER_ID)
    is_group_approved = db_query('SELECT id FROM groups WHERE id = ?', (message.chat.id,), fetch=True)
    is_user_approved = db_query('SELECT id FROM personal_users WHERE id = ?', (user_id,), fetch=True)
    is_unlimited = db_query('SELECT id FROM unlimited_users WHERE id = ?', (user_id,), fetch=True) or is_owner

    if message.chat.type != 'private' and not is_group_approved:
        return bot.reply_to(message, "❌ Group not approved.")
    if message.chat.type == 'private' and not is_owner and not is_user_approved:
        return bot.reply_to(message, "❌ No DM access.")

    count = get_search_info(user_id)
    if not is_unlimited and count >= 15:
        return bot.reply_to(message, "⚠️ Daily limit reached.")

    try:
        args = message.text.split()
        if len(args) < 2: return bot.reply_to(message, "⚠️ Usage: `/num [Number]`")
        mobile = args[1]
        status_msg = bot.reply_to(message, "🔍 **Searching Database...**")
        
        resp = requests.get(API_URL_TEMPLATE.format(mobile=mobile), timeout=15).json()
        records = resp if isinstance(resp, list) else (resp.get("data") or resp.get("records") or [resp])
        valid = [r for r in records if isinstance(r, dict) and len(r) > 1]

        if not valid:
            bot.edit_message_text(f"⚠️ No data found for `{mobile}`.", message.chat.id, status_msg.message_id)
            return

        db_query('UPDATE user_searches SET count = count + 1 WHERE user_id = ?', (user_id,))
        
        # --- UI START ---
        out = f"**━━━━━━━━━━━━━━━━━━━━**\n"
        out += f"  **RAJPUT X INFO BOT**\n"
        out += f"**━━━━━━━━━━━━━━━━━━━━**\n\n"
        out += f"**TOTAL RECORDS 📝 : {len(valid)}**\n"
        out += f"**NUMBER ✍🏻 : `{mobile}`**\n"
        out += f"**━━━━━━━━━━━━━━━━━━━━**\n\n"

        for i, r in enumerate(valid[:5], 1):
            def f(keys):
                for k, v in r.items():
                    if any(x in k.lower() for x in keys) and v and str(v).lower() not in ["n/a", "none", "null", ""]: 
                        return str(v).strip()
                return ""

            name = f(['name', 'full'])
            father = f(['father', 'f_name'])
            addr = f(['address', 'addr', 'location'])
            alt = f(['alt', 'mobile2', 'phone', 'contact'])
            circle = f(['circle', 'operator', 'network'])

            out += f"**RECORDS: {i}**\n"
            out += f"📱 **MOBILE:** `{mobile}`\n"
            if name: out += f"👤 **NAME:** `{name}`\n"
            if father: out += f"🤠 **FATHER'S NAME:** `{father}`\n"
            if addr: out += f"🏠 **ADDRESS:** `{addr}`\n"
            if alt: out += f"📞 **ALT:** `{alt}`\n"
            if circle: out += f"🌐 **CIRCLE:** `{circle}`\n"
            out += f"────────────────────\n"

        out += f"\n📉 **LEFT: {('Unlimited' if is_unlimited else 15-(count+1))}**\n"
        out += f"⏳ *Auto-delete in {DELETE_TIMER}s*"

        sent = bot.edit_message_text(out[:4000], message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        # Auto-delete threads
        threading.Thread(target=delete_msg, args=(message.chat.id, sent.message_id, DELETE_TIMER)).start()
        try: threading.Thread(target=delete_msg, args=(message.chat.id, message.message_id, DELETE_TIMER)).start()
        except: pass

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Error:** API issue or invalid response.", message.chat.id, status_msg.message_id)

# --- ALL 13 ADMIN COMMANDS (KEPT ORIGINAL) ---

@bot.message_handler(commands=['approvenumgc', 'disapprovenumgc', 'disaapprovenumgcall', 'listapprovenumgc'])
def group_mgt(message):
    if message.from_user.id != OWNER_ID: return
    cmd = message.text.split()[0].lower()
    if 'approvenumgc' == cmd[1:]:
        db_query('INSERT OR IGNORE INTO groups (id) VALUES (?)', (message.chat.id,))
        bot.reply_to(message, "✅ Group Approved.")
    elif 'disapprovenumgc' == cmd[1:]:
        db_query('DELETE FROM groups WHERE id = ?', (message.chat.id,))
        bot.reply_to(message, "❌ Group Removed.")
    elif 'disaapprovenumgcall' in cmd:
        db_query('DELETE FROM groups')
        bot.reply_to(message, "🗑 All Groups Cleared.")
    elif 'listapprovenumgc' in cmd:
        rows = db_query('SELECT id FROM groups', fetch=True)
        bot.reply_to(message, "👥 Groups:\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "Empty.")

@bot.message_handler(commands=['approvenum', 'disapprovenum', 'disapprovenumall', 'listapprovenum'])
def user_mgt(message):
    if message.from_user.id != OWNER_ID: return
    cmd = message.text.split()[0].lower()
    try:
        if 'list' in cmd:
            rows = db_query('SELECT id FROM personal_users', fetch=True)
            return bot.reply_to(message, "📋 Users:\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "Empty.")
        if 'all' in cmd:
            db_query('DELETE FROM personal_users'); return bot.reply_to(message, "🗑 Cleared.")
        uid = int(message.text.split()[1])
        if 'approvenum' == cmd[1:]:
            db_query('INSERT OR IGNORE INTO personal_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"✅ User {uid} Approved.")
        else:
            db_query('DELETE FROM personal_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ User {uid} Removed.")
    except: bot.reply_to(message, "⚠️ Usage: `/[cmd] [User_ID]`")

@bot.message_handler(commands=['unlimitednum', 'disunlimitednum', 'disunlimitednumall', 'listunlimitednum'])
def unl_mgt(message):
    if message.from_user.id != OWNER_ID: return
    cmd = message.text.split()[0].lower()
    try:
        if 'list' in cmd:
            rows = db_query('SELECT id FROM unlimited_users', fetch=True)
            return bot.reply_to(message, "⭐ Unlimited:\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "Empty.")
        if 'all' in cmd:
            db_query('DELETE FROM unlimited_users'); return bot.reply_to(message, "🗑 Cleared.")
        uid = int(message.text.split()[1])
        if 'unlimitednum' in cmd:
            db_query('INSERT OR IGNORE INTO unlimited_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"⭐ {uid} is now Unlimited.")
        else:
            db_query('DELETE FROM unlimited_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ {uid} Limit Restored.")
    except: bot.reply_to(message, "⚠️ Error.")

@bot.message_handler(commands=['broadcastnum'])
def broadcast(message):
    if message.from_user.id != OWNER_ID: return
    txt = message.text.replace('/broadcastnum', '').strip()
    if not txt: return
    for g in db_query('SELECT id FROM groups', fetch=True):
        try: bot.send_message(g[0], f"📢 **ANN:**\n\n{txt}")
        except: pass
    bot.reply_to(message, "✅ Done.")

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify(call):
    if check_force_join(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

while True:
    try: bot.infinity_polling(timeout=90)
    except: time.sleep(5)
    
