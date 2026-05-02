import telebot
import requests
import threading
import time
import sqlite3
from telebot import types

# ================= CONFIG =================
API_TOKEN = '8600054596:AAEKxLqeHN7PItqxK-SZ0I371ka8KH3A-MM'
OWNER_ID = 8442352135
# Aapki image ke mutabik API URL structure
API_URL = "https://num-info-rajput.vercel.app/search?num={}"

CHANNELS = {
    "1 🚀": {"id": "@snxhub", "url": "https://t.me/snxhub"},
    "2 🚀": {"id": "@snnetwork7", "url": "https://t.me/snnetwork7"},
    "3 🚀": {"id": "@snxhub1", "url": "https://t.me/snxhub1"}
}

bot = telebot.TeleBot(API_TOKEN)

# ================= DATABASE =================
def db(q, p=(), f=False):
    con = sqlite3.connect("data.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(q, p)
    r = cur.fetchall() if f else None
    con.commit()
    con.close()
    return r

def init():
    db("CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY)")
    db("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
    db("CREATE TABLE IF NOT EXISTS unlimited(id INTEGER PRIMARY KEY)")
    db("CREATE TABLE IF NOT EXISTS usage(uid INTEGER PRIMARY KEY,count INTEGER,date TEXT)")

init()

# ================= HELPERS =================
def auto_del(cid, mid, t=60):
    def d():
        time.sleep(t)
        try: bot.delete_message(cid, mid)
        except: pass
    threading.Thread(target=d).start()

def get_count(uid):
    d = time.strftime("%Y-%m-%d")
    r = db("SELECT count,date FROM usage WHERE uid=?", (uid,), True)
    if not r or r[0]['date'] != d:
        db("INSERT OR REPLACE INTO usage VALUES(?,?,?)", (uid,0,d))
        return 0
    return r[0]['count']

def force_join(uid):
    for c in CHANNELS.values():
        try:
            s = bot.get_chat_member(c['id'], uid).status
            if s in ['left','kicked']:
                return False
        except:
            return False
    return True

def is_owner(uid):
    return uid == OWNER_ID

# ================= SEARCH (UPDATED FOR IMAGE API) =================
@bot.message_handler(commands=['num'])
def num_cmd(m):
    uid = m.from_user.id
    cid = m.chat.id

    if not force_join(uid):
        mk = types.InlineKeyboardMarkup()
        for k, c in CHANNELS.items():
            mk.add(types.InlineKeyboardButton(f"Join {k}", url=c['url']))
        mk.add(types.InlineKeyboardButton("Verify ✅", callback_data="v"))
        bot.reply_to(m, "❌ Join all channels first", reply_markup=mk)
        return

    groups = [i['id'] for i in db("SELECT id FROM groups", f=True)]
    users = [i['id'] for i in db("SELECT id FROM users", f=True)]
    unl = [i['id'] for i in db("SELECT id FROM unlimited", f=True)]

    if m.chat.type in ['group','supergroup'] and cid not in groups:
        return

    if m.chat.type == 'private' and uid != OWNER_ID and uid not in users:
        bot.reply_to(m, "❌ No Personal Access")
        return

    unlimited = uid == OWNER_ID or uid in unl
    count = get_count(uid)

    if not unlimited and count >= 15:
        bot.reply_to(m, "⚠️ Daily Limit Reached")
        return

    try:
        number = m.text.split()[1]
    except:
        bot.reply_to(m, "❌ Use: /num 919XXXXXXXXX")
        return

    msg = bot.reply_to(m, "🔍 Searching...")

    try:
        # API Response image ke mutabik fetch karna
        response = requests.get(API_URL.format(number), timeout=10).json()
        
        # Image ke structure ke hisaab se: res['result']
        res_data = response.get("result", {})
        success = response.get("success", False)
        
    except Exception as e:
        bot.edit_message_text(f"⚠️ API Error: {str(e)}", cid, msg.message_id)
        return

    if not success or not res_data:
        bot.edit_message_text("❌ No Data Found", cid, msg.message_id)
        return

    db("UPDATE usage SET count=count+1 WHERE uid=?", (uid,))
    rem = "Unlimited" if unlimited else (15-(count+1))

    # Image ke keys: country, country_code, rmn, number, etc.
    # Note: Image mein limited keys hain, agar API zyada info deti hai toh wo bhi add ho jayengi
    name = res_data.get("name", "Not Available")
    num_val = res_data.get("number", number)
    country = res_data.get("country", "India")
    c_code = res_data.get("country_code", "+91")
    
    txt = f"📊 STATUS: SUCCESS | LEFT: {rem}\n\n"
    txt += f"📁 RECORD FOUND\n"
    txt += f"📞 Number: {num_val}\n"
    txt += f"👤 Name: {name}\n"
    txt += f"🌍 Country: {country} ({c_code})\n"
    txt += f"⚡ Response: {response.get('response_time', 'N/A')}\n"
    txt += "━━━━━━━━━━━━━━\n"
    txt += "\n⚠️ Auto delete in 60 sec"

    mk = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("SN X DAD 🦁", url="https://t.me/sxdad")
    )

    bot.edit_message_text(txt[:4000], cid, msg.message_id, reply_markup=mk)
    auto_del(cid, msg.message_id, 60)

# ================= VERIFY =================
@bot.callback_query_handler(func=lambda c: c.data=="v")
def verify(c):
    if force_join(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ Verified", show_alert=True)
        bot.delete_message(c.message.chat.id, c.message.message_id)
    else:
        bot.answer_callback_query(c.id, "❌ Join all first", show_alert=True)

# Admin commands (No changes made as per instruction)
@bot.message_handler(commands=['approvenumgc'])
def approve_gc(m):
    if not is_owner(m.from_user.id): return
    db("INSERT OR IGNORE INTO groups VALUES(?)", (m.chat.id,))
    bot.reply_to(m, "✅ Group Approved")

@bot.message_handler(commands=['disapprovenumgc'])
def disapprove_gc(m):
    if not is_owner(m.from_user.id): return
    db("DELETE FROM groups WHERE id=?", (m.chat.id,))
    bot.reply_to(m, "❌ Group Removed")

@bot.message_handler(commands=['disapprovenumgcall'])
def remove_all_gc(m):
    if not is_owner(m.from_user.id): return
    db("DELETE FROM groups")
    bot.reply_to(m, "⚠️ All groups removed")

@bot.message_handler(commands=['listapprovenumgc'])
def list_gc(m):
    if not is_owner(m.from_user.id): return
    data = db("SELECT id FROM groups", f=True)
    if not data:
        bot.reply_to(m, "❌ No groups")
    else:
        bot.reply_to(m, "\n".join([str(i['id']) for i in data]))

@bot.message_handler(commands=['approvenum'])
def approve_user(m):
    if not is_owner(m.from_user.id): return
    try:
        uid = int(m.text.split()[1])
        db("INSERT OR IGNORE INTO users VALUES(?)", (uid,))
        bot.reply_to(m, "✅ Approved")
    except:
        bot.reply_to(m, "❌ Invalid ID")

@bot.message_handler(commands=['disapprovenum'])
def disapprove_user(m):
    if not is_owner(m.from_user.id): return
    try:
        uid = int(m.text.split()[1])
        db("DELETE FROM users WHERE id=?", (uid,))
        bot.reply_to(m, "❌ Removed")
    except:
        bot.reply_to(m, "❌ Invalid ID")

@bot.message_handler(commands=['disapprovenumall'])
def remove_all_users(m):
    if not is_owner(m.from_user.id): return
    db("DELETE FROM users")
    bot.reply_to(m, "⚠️ All users removed")

@bot.message_handler(commands=['listapprovenum'])
def list_users(m):
    if not is_owner(m.from_user.id): return
    data = db("SELECT id FROM users", f=True)
    bot.reply_to(m, "\n".join([str(i['id']) for i in data]) or "No users")

@bot.message_handler(commands=['unlimitednum'])
def add_unl(m):
    if not is_owner(m.from_user.id): return
    try:
        uid = int(m.text.split()[1])
        db("INSERT OR IGNORE INTO unlimited VALUES(?)", (uid,))
        bot.reply_to(m, "♾ Unlimited added")
    except:
        bot.reply_to(m, "❌ Invalid ID")

@bot.message_handler(commands=['disunlimitednum'])
def rem_unl(m):
    if not is_owner(m.from_user.id): return
    try:
        uid = int(m.text.split()[1])
        db("DELETE FROM unlimited WHERE id=?", (uid,))
        bot.reply_to(m, "❌ Removed")
    except:
        bot.reply_to(m, "❌ Invalid ID")

@bot.message_handler(commands=['disunlimitednumall'])
def rem_all_unl(m):
    if not is_owner(m.from_user.id): return
    db("DELETE FROM unlimited")
    bot.reply_to(m, "⚠️ All unlimited removed")

@bot.message_handler(commands=['listunlimitednum'])
def list_unl(m):
    if not is_owner(m.from_user.id): return
    data = db("SELECT id FROM unlimited", f=True)
    bot.reply_to(m, "\n".join([str(i['id']) for i in data]) or "No unlimited")

@bot.message_handler(commands=['broadcastnum'])
def broadcast(m):
    if not is_owner(m.from_user.id): return
    try:
        msg = m.text.split(' ',1)[1]
    except:
        bot.reply_to(m, "Use: /broadcastnum message")
        return
    users = db("SELECT id FROM users", f=True)
    groups = db("SELECT id FROM groups", f=True)
    unlimited = db("SELECT id FROM unlimited", f=True)
    sent = set()
    total = 0
    for u in users + unlimited + groups:
        uid = u['id']
        if uid not in sent:
            try:
                bot.send_message(uid, msg)
                sent.add(uid)
                total += 1
            except: pass
    bot.reply_to(m, f"✅ Sent to {total} chats")

# ================= START =================
print("Bot Running...")
bot.infinity_polling()
