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
        conn = sqlite3.connect('bot_data.db')
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

# --- 1. GROUP APPROVAL COMMANDS ---
@bot.message_handler(commands=['approvenumgc'])
def app_gc(message):
    if message.from_user.id == OWNER_ID:
        db_query('INSERT OR IGNORE INTO groups (id) VALUES (?)', (message.chat.id,))
        bot.reply_to(message, f"✅ Success: Group `{message.chat.id}` has been approved.")
    else:
        bot.reply_to(message, "❌ Error: Only Owner can use this command.")

@bot.message_handler(commands=['disapprovenumgc'])
def dis_gc(message):
    if message.from_user.id == OWNER_ID:
        db_query('DELETE FROM groups WHERE id = ?', (message.chat.id,))
        bot.reply_to(message, "❌ Success: Group access has been removed.")
    else:
        bot.reply_to(message, "❌ Error: Unauthorized.")

@bot.message_handler(commands=['disaapprovenumgcall'])
def dis_all_gc(message):
    if message.from_user.id == OWNER_ID:
        db_query('DELETE FROM groups')
        bot.reply_to(message, "🗑 Success: All approved groups have been cleared.")
    else:
        bot.reply_to(message, "❌ Error: Unauthorized.")

@bot.message_handler(commands=['listapprovenumgc'])
def list_gc(message):
    if message.from_user.id == OWNER_ID:
        rows = db_query('SELECT id FROM groups', fetch=True)
        text = "👥 **Approved Groups List:**\n\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "⚠️ No groups are currently approved."
        bot.reply_to(message, text, parse_mode="Markdown")

# --- 2. PERSONAL ACCESS COMMANDS ---
@bot.message_handler(commands=['approvenum'])
def app_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            args = message.text.split()
            if len(args) < 2: raise ValueError
            uid = int(args[1])
            db_query('INSERT OR IGNORE INTO personal_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"👤 Success: User `{uid}` now has personal access.")
        except: bot.reply_to(message, "⚠️ Usage: `/approvenum [User_ID]`")
    else:
        bot.reply_to(message, "❌ Error: Unauthorized.")

@bot.message_handler(commands=['disapprovenum'])
def dis_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            db_query('DELETE FROM personal_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ Success: User `{uid}` personal access removed.")
        except: bot.reply_to(message, "⚠️ Usage: `/disapprovenum [User_ID]`")

@bot.message_handler(commands=['disapprovenumall'])
def dis_all_user(message):
    if message.from_user.id == OWNER_ID:
        db_query('DELETE FROM personal_users')
        bot.reply_to(message, "🗑 Success: All personal access records deleted.")

@bot.message_handler(commands=['listapprovenum'])
def list_user(message):
    if message.from_user.id == OWNER_ID:
        rows = db_query('SELECT id FROM personal_users', fetch=True)
        text = "👤 **Personal Users List:**\n\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "⚠️ No personal users found."
        bot.reply_to(message, text, parse_mode="Markdown")

# --- 3. UNLIMITED USAGE COMMANDS ---
@bot.message_handler(commands=['unlimitednum'])
def app_unl(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            db_query('INSERT OR IGNORE INTO unlimited_users (id) VALUES (?)', (uid,))
            bot.reply_to(message, f"⭐ Success: User `{uid}` is now an Unlimited user.")
        except: bot.reply_to(message, "⚠️ Usage: `/unlimitednum [User_ID]`")

@bot.message_handler(commands=['disunlimitednum'])
def dis_unl(message):
    if message.from_user.id == OWNER_ID:
        try:
            uid = int(message.text.split()[1])
            db_query('DELETE FROM unlimited_users WHERE id = ?', (uid,))
            bot.reply_to(message, f"❌ Success: User `{uid}` unlimited status removed.")
        except: bot.reply_to(message, "⚠️ Usage: `/disunlimitednum [User_ID]`")

@bot.message_handler(commands=['disunlimitednumall'])
def dis_all_unl(message):
    if message.from_user.id == OWNER_ID:
        db_query('DELETE FROM unlimited_users')
        bot.reply_to(message, "🗑 Success: All unlimited users cleared.")

@bot.message_handler(commands=['listunlimitednum'])
def list_unl(message):
    if message.from_user.id == OWNER_ID:
        rows = db_query('SELECT id FROM unlimited_users', fetch=True)
        text = "⭐ **Unlimited Users List:**\n\n" + "\n".join([f"`{r[0]}`" for r in rows]) if rows else "⚠️ No unlimited users found."
        bot.reply_to(message, text, parse_mode="Markdown")

# --- 4. BROADCAST COMMAND ---
@bot.message_handler(commands=['broadcastnum'])
def bcast(message):
    if message.from_user.id == OWNER_ID:
        msg_text = message.text.replace('/broadcastnum', '').strip()
        if not msg_text:
            bot.reply_to(message, "⚠️ Error: Please provide a message after the command.\nExample: `/broadcastnum Hello!`")
            return
        
        groups = db_query('SELECT id FROM groups', fetch=True)
        if not groups:
            bot.reply_to(message, "⚠️ Error: No approved groups to broadcast to.")
            return

        success = 0
        for g_id in groups:
            try:
                bot.send_message(g_id[0], f"📢 **BROADCAST**\n\n{msg_text}", parse_mode="Markdown")
                success += 1
            except: continue
        bot.reply_to(message, f"✅ Broadcast finished! Sent to {success} groups.")
    else:
        bot.reply_to(message, "❌ Unauthorized.")

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
        bot.reply_to(message, "❌ **Access Denied!**\nPlease join our channels first to use this bot.", reply_markup=markup)
        return

    # Permissions
    approved_gcs = [r[0] for r in db_query('SELECT id FROM groups', fetch=True)]
    approved_users = [r[0] for r in db_query('SELECT id FROM personal_users', fetch=True)]
    unlimited_users = [r[0] for r in db_query('SELECT id FROM unlimited_users', fetch=True)]

    if message.chat.type in ['group', 'supergroup'] and chat_id not in approved_gcs:
        bot.reply_to(message, "❌ This group is not approved to use this bot.")
        return
    if message.chat.type == 'private' and user_id != OWNER_ID and user_id not in approved_users:
        bot.reply_to(message, "❌ You don't have personal access. Contact Admin.")
        return

    is_unl = (user_id == OWNER_ID or user_id in unlimited_users)
    count = get_search_info(user_id)
    if not is_unl and count >= 15:
        bot.reply_to(message, "⚠️ Daily limit reached (15/15). Try again tomorrow or get Unlimited Access.")
        return

    try:
        mobile = message.text.split()[1]
    except:
        bot.reply_to(message, "⚠️ Usage: `/num [Mobile_Number]`")
        return

    status = bot.reply_to(message, "🔍 Processing your request...")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(API_URL_TEMPLATE.format(mobile=mobile), headers=headers, timeout=15)
        res = response.json()

        records = []
        if isinstance(res, list): records = res
        elif isinstance(res, dict):
            records = res.get("data") or res.get("records") or res.get("result")
            if not records and any(k in res for k in ['NAME', 'name']): records = [res]
        
        if not records:
            bot.edit_message_text(f"⚠️ No data found for `{mobile}` in our database.", chat_id, status.message_id)
            return

        db_query('UPDATE user_searches SET count = count + 1 WHERE user_id = ?', (user_id,))
        rem = "Unlimited" if is_unl else (15 - (count + 1))
        
        txt = f"📊 **TOTAL RECORDS: {len(records)}**\n📉 **SEARCHES LEFT: {rem}**\n\n"
        for i, r in enumerate(records, 1):
            if i > 8: break 
            name = next((r.get(k) for k in ['NAME', 'name', 'FULLNAME'] if r.get(k)), "N/A")
            fname = next((r.get(k) for k in ['FNAME', 'fname', 'FATHER'] if r.get(k)), "N/A")
            addr = next((r.get(k) for k in ['ADDRESS', 'address'] if r.get(k)), "N/A")
            phone = next((r.get(k) for k in ['MOBILE', 'mobile', 'num'] if r.get(k)), mobile)
            alt_num = next((r.get(k) for k in ['ALT', 'alt', 'phone2'] if r.get(k)), "N/A")
            
            txt += f"**RECORD:** {i}\n📱 **MOB:** `{phone}`\n👤 **NAME:** `{name}`\n🤠 **FATHER:** `{fname}`\n🏠 **ADR:** `{addr}`\n📞 **ALT:** `{alt_num}`\n───────────────────\n"
        
        txt += "\n⚠️ *This message will be deleted in 60s.*"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("𝐒𝐍 𝐗 𝐃𝐀𝐃 🦁", url="https://t.me/sxdad"))
        bot.edit_message_text(txt[:4000], chat_id, status.message_id, parse_mode="Markdown", reply_markup=markup)
        auto_delete(chat_id, status.message_id, 60)
        
    except Exception as e:
        bot.edit_message_text(f"⚠️ Error: API is currently down or not responding. ({str(e)})", chat_id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify(call):
    if check_force_join(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified! You can now use the bot.", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Verification Failed! Please join all channels.", show_alert=True)

bot.infinity_polling(timeout=90, long_polling_timeout=90)
                     
