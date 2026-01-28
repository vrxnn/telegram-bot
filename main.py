#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telebot
from telebot import types
import sqlite3
import os
from datetime import datetime, timedelta
import time
import pytz

# Bot sozlamalari
API_TOKEN = "7914845243:AAFZiJTvrNmKxwA4zBi7lxT1oGebuTV2eX4"  # O'z tokeningizni kiriting
ADMIN_ID = 5668810530  # O'z admin ID'ingizni kiriting

bot = telebot.TeleBot(API_TOKEN)
bot_username = bot.get_me().username

# Timezone
tz = pytz.timezone('Asia/Tashkent')

# Ma'lumotlar bazasi
def init_db():
    conn = sqlite3.connect('kinobot.db', check_same_thread=False)
    c = conn.cursor()
    
    # Foydalanuvchilar
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  first_name TEXT,
                  username TEXT,
                  join_date TEXT)''')
    
    # Kinolar
    c.execute('''CREATE TABLE IF NOT EXISTS movies
                 (code INTEGER PRIMARY KEY,
                  photo_id TEXT,
                  video_id TEXT,
                  caption TEXT,
                  channel_msg_id INTEGER,
                  download_count INTEGER DEFAULT 0)''')
    
    # Adminlar
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (admin_id INTEGER PRIMARY KEY)''')
    
    # Ommaviy kanallar
    c.execute('''CREATE TABLE IF NOT EXISTS public_channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE)''')
    
    # Maxfiy kanallar
    c.execute('''CREATE TABLE IF NOT EXISTS private_channels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  chat_id INTEGER,
                  invite_link TEXT,
                  UNIQUE(chat_id))''')
    
    # Maxfiy kanal a'zolari
    c.execute('''CREATE TABLE IF NOT EXISTS private_channel_members
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  chat_id INTEGER,
                  user_id INTEGER,
                  UNIQUE(chat_id, user_id))''')
    
    # Bloklangan userlar
    c.execute('''CREATE TABLE IF NOT EXISTS blocked_users
                 (user_id INTEGER PRIMARY KEY)''')
    
    # User qadamlari
    c.execute('''CREATE TABLE IF NOT EXISTS user_steps
                 (user_id INTEGER PRIMARY KEY,
                  step TEXT,
                  data TEXT)''')
    
    # Sozlamalar
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY,
                  value TEXT)''')
    
    # Dastlabki sozlamalar
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_status', 'Yoqilgan')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('movie_code', '0')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel', '')")
    c.execute("INSERT OR IGNORE INTO admins (admin_id) VALUES (?)", (ADMIN_ID,))
    
    conn.commit()
    conn.close()

init_db()

# Database funksiyalar
def get_db():
    return sqlite3.connect('kinobot.db', check_same_thread=False)

def get_setting(key):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def is_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT admin_id FROM admins WHERE admin_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_all_admins():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT admin_id FROM admins")
    admins = [row[0] for row in c.fetchall()]
    conn.close()
    return admins

def add_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO admins (admin_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def remove_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE admin_id=? AND admin_id!=?", (user_id, ADMIN_ID))
    conn.commit()
    conn.close()

def add_user(user_id, first_name, username):
    conn = get_db()
    c = conn.cursor()
    
    # Avval userning mavjudligini tekshiramiz
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = c.fetchone()
    
    if not exists:
        join_date = datetime.now(tz).strftime("%d.%m.%Y")
        c.execute("INSERT INTO users (user_id, first_name, username, join_date) VALUES (?, ?, ?, ?)",
                  (user_id, first_name, username, join_date))
        conn.commit()
        
        # Asosiy adminga xabar yuborish
        try:
            user_link = f'<a href="tg://user?id={user_id}">{first_name}</a>'
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("👀 Ko'rish", url=f"tg://user?id={user_id}"))
            
            username_text = username if username else "Yoq"
            bot.send_message(
                ADMIN_ID,
                f"<b>👤 Yangi obunachi qo'shildi!\n\n"
                f"👤 Ism: {first_name}\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"🔗 Telegram: @{username_text}\n"
                f"🕒 Vaqt: {datetime.now(tz).strftime('%d.%m.%Y | %H:%M')}</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
        except:
            pass
    
    conn.close()

def get_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def is_blocked(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM blocked_users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def block_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def unblock_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM blocked_users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def set_step(user_id, step, data=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_steps (user_id, step, data) VALUES (?, ?, ?)",
              (user_id, step, data))
    conn.commit()
    conn.close()

def get_step(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT step, data FROM user_steps WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None)

def clear_step(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM user_steps WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# Kanallar bilan ishlash
def get_public_channels():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM public_channels")
    channels = [row[0] for row in c.fetchall()]
    conn.close()
    return channels

def add_public_channel(username):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO public_channels (username) VALUES (?)", (username,))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def remove_public_channel(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM public_channels WHERE username=?", (username,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_private_channels():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT chat_id, invite_link FROM private_channels")
    channels = c.fetchall()
    conn.close()
    return channels

def add_private_channel(chat_id, invite_link):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO private_channels (chat_id, invite_link) VALUES (?, ?)",
                  (chat_id, invite_link))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def remove_private_channel(chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM private_channels WHERE chat_id=?", (chat_id,))
    c.execute("DELETE FROM private_channel_members WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def add_private_member(chat_id, user_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO private_channel_members (chat_id, user_id) VALUES (?, ?)",
                  (chat_id, user_id))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def is_private_member(chat_id, user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM private_channel_members WHERE chat_id=? AND user_id=?",
              (chat_id, user_id))
    result = c.fetchone()
    conn.close()
    return result is not None

# Kanal obunasini tekshirish
def check_subscription(user_id):
    buttons = []
    
    # Ommaviy kanallar
    public_channels = get_public_channels()
    for channel_username in public_channels:
        try:
            member = bot.get_chat_member(f"@{channel_username}", user_id)
            if member.status not in ["creator", "administrator", "member"]:
                chat_info = bot.get_chat(f"@{channel_username}")
                buttons.append([types.InlineKeyboardButton(
                    text=f"❌ {chat_info.title}",
                    url=f"https://t.me/{channel_username}"
                )])
        except:
            continue
    
    # Maxfiy kanallar
    private_channels = get_private_channels()
    for chat_id, invite_link in private_channels:
        if not is_private_member(chat_id, user_id):
            buttons.append([types.InlineKeyboardButton(
                text="❌ Maxfiy kanal",
                url=invite_link
            )])
    
    if buttons:
        buttons.append([types.InlineKeyboardButton(
            text="🔄 Tekshirish",
            callback_data="checksuv"
        )])
        return False, buttons
    
    return True, []

# Klaviaturalar
def get_admin_panel():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📢 Kanallar", "📥 Kino Yuklash")
    markup.row("✉ Xabarnoma", "📊 Statistika")
    markup.row("🤖 Bot holati", "👥 Adminlar")
    markup.row("◀️ Orqaga")
    return markup

def get_back_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("◀️ Orqaga")
    return markup

def get_panel_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🗄 Boshqaruv paneli")
    return markup

# Statistika funksiyalari
def get_daily_stats():
    conn = get_db()
    c = conn.cursor()
    
    today = datetime.now(tz).strftime("%d.%m.%Y")
    yesterday = (datetime.now(tz) - timedelta(days=1)).strftime("%d.%m.%Y")
    day2 = (datetime.now(tz) - timedelta(days=2)).strftime("%d.%m.%Y")
    day3 = (datetime.now(tz) - timedelta(days=3)).strftime("%d.%m.%Y")
    day4 = (datetime.now(tz) - timedelta(days=4)).strftime("%d.%m.%Y")
    day5 = (datetime.now(tz) - timedelta(days=5)).strftime("%d.%m.%Y")
    
    stats = {}
    for day, name in [(today, 'bugun'), (yesterday, 'kecha'), (day2, '2kun'), 
                      (day3, '3kun'), (day4, '4kun'), (day5, '5kun')]:
        c.execute("SELECT COUNT(*) FROM users WHERE join_date=?", (day,))
        stats[name] = c.fetchone()[0]
    
    conn.close()
    return stats

def get_weekly_stats():
    conn = get_db()
    c = conn.cursor()
    
    now = datetime.now(tz)
    current_week = now.isocalendar()[1]
    last_week = (now - timedelta(weeks=1)).isocalendar()[1]
    two_weeks_ago = (now - timedelta(weeks=2)).isocalendar()[1]
    
    c.execute("SELECT join_date FROM users")
    all_dates = c.fetchall()
    
    stats = {'shu_hafta': 0, 'oldin_hafta': 0, 'oldin_2hafta': 0}
    
    for (date_str,) in all_dates:
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            week = date_obj.isocalendar()[1]
            
            if week == current_week:
                stats['shu_hafta'] += 1
            elif week == last_week:
                stats['oldin_hafta'] += 1
            elif week == two_weeks_ago:
                stats['oldin_2hafta'] += 1
        except:
            continue
    
    conn.close()
    return stats

def get_monthly_stats():
    conn = get_db()
    c = conn.cursor()
    
    now = datetime.now(tz)
    current_month = now.strftime("%m.%Y")
    last_month = (now - timedelta(days=30)).strftime("%m.%Y")
    two_months_ago = (now - timedelta(days=60)).strftime("%m.%Y")
    
    c.execute("SELECT join_date FROM users")
    all_dates = c.fetchall()
    
    stats = {'shu_oy': 0, 'oldin_oy': 0, 'oldin_2oy': 0}
    
    for (date_str,) in all_dates:
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            month = date_obj.strftime("%m.%Y")
            
            if month == current_month:
                stats['shu_oy'] += 1
            elif month == last_month:
                stats['oldin_oy'] += 1
            elif month == two_months_ago:
                stats['oldin_2oy'] += 1
        except:
            continue
    
    conn.close()
    return stats

# /start komandasi
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    # Bloklangan user
    if is_blocked(user_id):
        bot.send_message(user_id, "❌ Siz botdan foydalanish huquqidan mahrum qilindingiz!")
        return
    
    # Bot holati
    bot_status = get_setting('bot_status')
    if bot_status == "O'chirilgan" and not is_admin(user_id):
        bot.send_message(
            user_id,
            "⛔️ <b>Bot vaqtinchalik o'chirilgan!</b>\n\n<i>Botda ta'mirlash ishlari olib borilayotgan bo'lishi mumkin!</i>",
            parse_mode='HTML'
        )
        return
    
    # Foydalanuvchini qo'shish
    add_user(user_id, first_name, username)
    
    # /start kodi bilan
    if len(message.text.split()) > 1:
        movie_code = message.text.split()[1]
        
        is_subscribed, buttons = check_subscription(user_id)
        
        if not is_subscribed:
            markup = types.InlineKeyboardMarkup(buttons)
            bot.send_message(
                user_id,
                "<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
            set_step(user_id, "waiting_movie", movie_code)
            return
        
        send_movie(user_id, movie_code)
        return
    
    # Oddiy /start
    is_subscribed, buttons = check_subscription(user_id)
    
    if not is_subscribed:
        markup = types.InlineKeyboardMarkup(buttons)
        bot.send_message(
            user_id,
            "<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>",
            parse_mode='HTML',
            reply_markup=markup
        )
        return
    
    user_link = f'<a href="tg://user?id={user_id}">{first_name}</a>'
    channel = get_setting('channel')
    
    markup = types.InlineKeyboardMarkup()
    if channel:
        markup.row(types.InlineKeyboardButton(
            "🔎 Kino kodlari",
            url=f"https://t.me/{channel.replace('@', '')}"
        ))
    
    if is_admin(user_id):
        markup.row(types.InlineKeyboardButton(
            "🗄 Boshqaruv paneli",
            callback_data="boshqar"
        ))
    
    bot.send_message(
        user_id,
        f"🖐 <b>Assalomu alaykum, {user_link}\n\n"
        f"<blockquote>📊 Bot buyruqlari:\n"
        f"/start - ♻️ Botni qayta ishga tushirish\n"
        f"/help - ☎️ Qo'llab-quvvatlash</blockquote>\n\n"
        f"🔎 Film kodini yuboring:</b>",
        parse_mode='HTML',
        reply_markup=markup
    )

# /help komandasi
@bot.message_handler(commands=['help'])
def help_handler(message):
    user_id = message.from_user.id
    
    is_subscribed, buttons = check_subscription(user_id)
    if not is_subscribed:
        markup = types.InlineKeyboardMarkup(buttons)
        bot.send_message(
            user_id,
            "<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>",
            parse_mode='HTML',
            reply_markup=markup
        )
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "☎️ Qo'llab-quvvatlash",
        url=f"tg://user?id={ADMIN_ID}"
    ))
    
    bot.send_message(
        user_id,
        "💻 <b>Savol va Takliflaringiz bolsa pastdagi manzilimizga murojaat qiling!</b>",
        parse_mode='HTML',
        reply_markup=markup
    )

# Kinoni yuborish
def send_movie(user_id, movie_code):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT video_id, caption, download_count FROM movies WHERE code=?", (movie_code,))
        result = c.fetchone()
        
        if result:
            video_id, caption, download_count = result
            
            download_count += 1
            c.execute("UPDATE movies SET download_count=? WHERE code=?", (download_count, movie_code))
            conn.commit()
            
            channel = get_setting('channel') or ""
            
            markup = types.InlineKeyboardMarkup()
            if channel:
                markup.row(types.InlineKeyboardButton(
                    "🔎 Kino kodlari",
                    url=f"https://t.me/{channel.replace('@', '')}"
                ))
            markup.row(types.InlineKeyboardButton(
                "📋 Ulashish",
                url=f"https://t.me/share/url?url=https://t.me/{bot_username}?start={movie_code}"
            ))
            
            caption_text = caption or "Malumot yoq"
            bot.send_video(
                user_id,
                video_id,
                caption=f"<b>🍿 Kino haqida:\n<blockquote>{caption_text}</blockquote>\n\n"
                       f"🔰 Kanal: {channel}\n"
                       f"🗂 Yuklashlar soni: {download_count}\n\n"
                       f"🤖 Bizning bot: @{bot_username}</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
        else:
            bot.send_message(user_id, "❌ Bunday kodli kino topilmadi!")
        
        conn.close()
    except Exception as e:
        bot.send_message(user_id, "❌ Xatolik yuz berdi!")

# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    # Bot holati tekshiruvi
    bot_status = get_setting('bot_status')
    if bot_status == "O'chirilgan" and not is_admin(user_id):
        bot.answer_callback_query(
            call.id,
            "⛔️ Bot vaqtinchalik o'chirilgan!\n\nBotda ta'mirlash ishlari olib borilayotgan bo'lishi mumkin!",
            show_alert=True
        )
        return
    
    # Obunani tekshirish
    if data == "checksuv":
        is_subscribed, buttons = check_subscription(user_id)
        
        if is_subscribed:
            bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
            bot.delete_message(chat_id, message_id)
            
            step, movie_code = get_step(user_id)
            if step == "waiting_movie" and movie_code:
                send_movie(user_id, movie_code)
                clear_step(user_id)
            else:
                channel = get_setting('channel')
                user_link = f'<a href="tg://user?id={user_id}">{call.from_user.first_name}</a>'
                
                markup = types.InlineKeyboardMarkup()
                if channel:
                    markup.row(types.InlineKeyboardButton(
                        "🔎 Kino kodlari",
                        url=f"https://t.me/{channel.replace('@', '')}"
                    ))
                
                if is_admin(user_id):
                    markup.row(types.InlineKeyboardButton(
                        "🗄 Boshqaruv paneli",
                        callback_data="boshqar"
                    ))
                
                bot.send_message(
                    user_id,
                    f"🖐 <b>Assalomu alaykum, {user_link}\n\n"
                    f"<blockquote>📊 Bot buyruqlari:\n"
                    f"/start - ♻️ Botni qayta ishga tushirish\n"
                    f"/help - ☎️ Qo'llab-quvvatlash</blockquote>\n\n"
                    f"🔎 Film kodini yuboring:</b>",
                    parse_mode='HTML',
                    reply_markup=markup
                )
        else:
            bot.answer_callback_query(call.id, "❌ Barcha kanallarga obuna bo'ling!", show_alert=True)
    
    # Boshqaruv paneli
    elif data == "boshqar":
        if not is_admin(user_id):
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<b>🖥️ Boshqaruv panelidasiz!</b>",
            parse_mode='HTML',
            reply_markup=get_admin_panel()
        )
    
    elif data == "bosh":
        if not is_admin(user_id):
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<b>Admin paneliga xush kelibsiz!</b>",
            parse_mode='HTML',
            reply_markup=get_admin_panel()
        )
    
    elif data == "yopish":
        bot.delete_message(chat_id, message_id)
    
    # Adminlar bo'limi
    elif data == "admins":
        if not is_admin(user_id):
            return
        
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("➕ Yangi admin qo'shish", callback_data="add"))
        markup.row(
            types.InlineKeyboardButton("📑 Ro'yxat", callback_data="list"),
            types.InlineKeyboardButton("🗑 O'chirish", callback_data="remove")
        )
        
        bot.edit_message_text(
            "🔰 <b>Quyidagilardan birini tanlang:</b>",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data == "list":
        if not is_admin(user_id):
            return
        
        admins = get_all_admins()
        admins_text = "\n".join([str(admin) for admin in admins if admin != ADMIN_ID])
        
        if admins_text:
            text = f"👮‍♂️ <b>Adminlar ro'yxati:</b>\n{admins_text}"
        else:
            text = "🚫 <b>Yordamchi adminlar topilmadi!</b>"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="admins"))
        
        bot.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
    
    elif data == "add":
        if user_id != ADMIN_ID:
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "🔢 <b>Kerakli foydalanuvchi ID raqamini yuboring:</b>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "add-admin")
    
    elif data == "remove":
        if user_id != ADMIN_ID:
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "🔢 <b>Kerakli foydalanuvchi ID raqamini yuboring:</b>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "remove-admin")
    
    # Kanallar bo'limi
    elif data == "kanallar":
        if not is_admin(user_id):
            return
        
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("💎 Majburiy obunalar", callback_data="majburiy"))
        markup.row(
            types.InlineKeyboardButton("🎥 Kino kanal", callback_data="qoshimcha"),
            types.InlineKeyboardButton("❌ Yopish", callback_data="bosh")
        )
        
        bot.edit_message_text(
            "<b>⬇️ Quyidagilardan birini tanlang:</b>",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data == "majburiy":
        if not is_admin(user_id):
            return
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("👥 Ommaviy", callback_data="ommav"),
            types.InlineKeyboardButton("🔐 Maxfiy", callback_data="maxfiy")
        )
        markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="kanallar"))
        
        bot.edit_message_text(
            "<b>⁉️ Qaysi turda kanal qo'shmoqchisiz!</b>",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data == "ommav":
        if not is_admin(user_id):
            return
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Qo'shish", callback_data="qoshish"))
        markup.row(
            types.InlineKeyboardButton("📑 Ro'yxat", callback_data="royxati"),
            types.InlineKeyboardButton("🗑 O'chirish", callback_data="ochirish")
        )
        markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="majburiy"))
        
        bot.edit_message_text(
            "<b>✅ Ommaviy kanallarni sozlash bo'limidasiz:</b>",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data == "maxfiy":
        if not is_admin(user_id):
            return
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Qo'shish", callback_data="qosh"))
        markup.row(
            types.InlineKeyboardButton("📑 Ro'yxat", callback_data="roy"),
            types.InlineKeyboardButton("🗑 O'chirish", callback_data="ochir")
        )
        markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="majburiy"))
        
        bot.edit_message_text(
            "<b>✅ Maxfiy kanallarni sozlash bo'limidasiz:</b>",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    # Ommaviy kanallar
    elif data == "qoshish":
        if not is_admin(user_id):
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<i>⚠️ Kanalingiz manzilini yuborishdan avval botni kanalingizga admin qilib olishingiz kerak!</i>\n\n"
            "📢 <b>Kerakli kanalni manzilini yuboring:\n\n"
            "📄 Namuna:</b> <code>@FireObuna</code>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "add-channel")
    
    elif data == "ochirish":
        if not is_admin(user_id):
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<b>📝 O'chirilishi kerak bo'lgan kanalning manzilini yuboring:\n\n"
            "📄 Namuna:</b> <code>@FireObuna</code>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "remove-channel")
    
    elif data == "royxati":
        if not is_admin(user_id):
            return
        
        channels = get_public_channels()
        
        if channels:
            text = "<b>📢 Kanallar ro'yxati:</b>\n\n"
            text += "\n".join([f"@{ch}" for ch in channels])
            text += f"\n\n<b>Ulangan kanallar soni:</b> {len(channels)} ta"
        else:
            text = "<b>Hech qanday kanallar ulanmagan!</b>"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="ommav"))
        
        bot.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
    
    # Maxfiy kanallar
    elif data == "qosh":
        if not is_admin(user_id):
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<i>⚠️ Kanalingiz manzilini yuborishdan avval botni kanalingizga admin qilib olishingiz kerak! Aks holda xatoliklar yuzaga keladi!</i>\n\n"
            "📢 <b>Maxfiy kanalni quyidagicha yuboring:</b>\n\n"
            "📄 <b>Namuna:</b> <code>https://t.me/+ZEcQiRY_pRphZTdi\n-100326189432</code>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "add-chanel")
    
    elif data == "ochir":
        if not is_admin(user_id):
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<b>📝 O'chirilishi kerak bo'lgan maxfiy kanalning manzilini va ID sini yuboring:</b>\n\n"
            "📄 <b>Namuna:</b>\n<code>https://t.me/+ZEcQiRY_pRphZTdiHs\n-1001234567890</code>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "remove-secret-channel")
    
    elif data == "roy":
        if not is_admin(user_id):
            return
        
        public_channels = get_public_channels()
        private_channels = get_private_channels()
        
        # Ommaviy kanallar
        if public_channels:
            public_text = "<b>📢 Ommaviy kanallar:</b>\n\n"
            public_text += "\n".join([f"@{ch}" for ch in public_channels])
            public_text += f"\n\n<b>Ulangan ommaviy kanallar soni:</b> {len(public_channels)} ta"
        else:
            public_text = "<b>Ommaviy kanallar ulanmagan!</b>"
        
        # Maxfiy kanallar
        if private_channels:
            private_text = "\n\n<b>🔒 Maxfiy kanallar:</b>\n\n"
            for chat_id, link in private_channels:
                private_text += f"🔹 <code>{link}</code>\n"
            private_text += f"\n<b>Ulangan maxfiy kanallar soni:</b> {len(private_channels)} ta"
        else:
            private_text = "\n\n<b>Maxfiy kanallar ulanmagan!</b>"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Orqaga", callback_data="maxfiy"))
        
        bot.edit_message_text(
            public_text + private_text,
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    # Kino kanali
    elif data == "qoshimcha":
        if not is_admin(user_id):
            return
        
        channel = get_setting('channel') or "Kiritilmagan"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Kino kanalni o'zgartirish", callback_data="kinokanal"))
        markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="kanallar"))
        
        bot.edit_message_text(
            f"<b>📄 Hozirgi kino kanal:</b> {channel}",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data == "kinokanal":
        if not is_admin(user_id):
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<blockquote>⚠️ Kanalingiz manzilini yuborishdan avval botni kanalingizga admin qilib olishingiz kerak!</blockquote>\n\n"
            "📢 <b>Kerakli kanalni manzilini yuboring:\n\n"
            "📄 Namuna:</b> <code>@FireObuna</code>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "add-channl")
    
    # Statistika
    elif data == "stat":
        if not is_admin(user_id):
            return
        
        all_users = get_all_users()
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("📅 Kunlik", callback_data="kunlik"),
            types.InlineKeyboardButton("📆 Haftalik", callback_data="haftalik"),
            types.InlineKeyboardButton("📊 Oylik", callback_data="oylik")
        )
        
        bot.edit_message_text(
            f"<b>📊 Qaysi statistikani ko'rmoqchisiz?\n\n✅ Jami Foydalanuvchilar: {len(all_users)} ta</b>",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data == "kunlik":
        if not is_admin(user_id):
            return
        
        stats = get_daily_stats()
        
        text = (f"<b>📅 Kunlik statistika:</b>\n"
                f"<blockquote>🔹 Bugun: {stats['bugun']} ta\n"
                f"🔹 Kecha: {stats['kecha']} ta\n"
                f"🔹 2 kun oldin: {stats['2kun']} ta\n"
                f"🔹 3 kun oldin: {stats['3kun']} ta\n"
                f"🔹 4 kun oldin: {stats['4kun']} ta\n"
                f"🔹 5 kun oldin: {stats['5kun']} ta</blockquote>")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Ortga qaytish", callback_data="stat"))
        
        bot.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
    
    elif data == "haftalik":
        if not is_admin(user_id):
            return
        
        stats = get_weekly_stats()
        
        text = (f"<b>📆 Haftalik statistika:</b>\n"
                f"<blockquote>🔹 Shu hafta: {stats['shu_hafta']} ta\n"
                f"🔹 O'tgan hafta: {stats['oldin_hafta']} ta\n"
                f"🔹 2 hafta oldin: {stats['oldin_2hafta']} ta</blockquote>")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Ortga qaytish", callback_data="stat"))
        
        bot.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
    
    elif data == "oylik":
        if not is_admin(user_id):
            return
        
        stats = get_monthly_stats()
        
        text = (f"<b>📊 Oylik statistika:</b>\n"
                f"<blockquote>🔹 Shu oy: {stats['shu_oy']} ta\n"
                f"🔹 O'tgan oy: {stats['oldin_oy']} ta\n"
                f"🔹 2 oy oldin: {stats['oldin_2oy']} ta</blockquote>")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Ortga qaytish", callback_data="stat"))
        
        bot.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
    
    # Xabarnoma
    elif data == "send":
        if not is_admin(user_id):
            return
        
        all_users = get_all_users()
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            f"<b><u>📝 {len(all_users)} ta foydalanuvchiga yuboriladigan xabarni botga yuboring.</u>\n\n"
            f"⚠️<i>Oddiy ko'rinishda yuboring!</i></b>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "sendpost")
    
    elif data == "send2":
        if not is_admin(user_id):
            return
        
        all_users = get_all_users()
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            f"<b><u>📝 {len(all_users)} ta foydalanuvchiga yuboriladigan xabarni botga yuboring.</u>\n\n"
            f"⚠️<i>Forward ko'rinishda yuboring!</i></b>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "sendfwrd")
    
    elif data == "user":
        if not is_admin(user_id):
            return
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<b>📝 Foydalanuvchi ID raqamini kiriting:</b>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "user")
    
    # Kino yuklash
    elif data == "oddiyk":
        if not is_admin(user_id):
            return
        
        channel = get_setting('channel')
        
        if not channel:
            bot.answer_callback_query(call.id, "⚠️ Kinolar yuboriladigan kanal qo'shilmagan!", show_alert=True)
            return
        
        movie_code = int(get_setting('movie_code')) + 1
        set_setting('movie_code', str(movie_code))
        
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            user_id,
            "<i>📄 Siz bu usulda kino yuklash uchun avval kinoni matnli qismi (captioni)ni tayyor qilib olishingiz kerak! O'sha matn bilan tashlasangiz bot buni avtomatik saqlab kerakli joyda qo'llaydi!</i>\n\n"
            "<b>✅ Boshlash uchun avvalo kino uchun rasm yuboring!</b>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        set_step(user_id, "rasm", str(movie_code))
    
    # Bot holati
    elif data == "bot":
        if not is_admin(user_id):
            return
        
        bot_status = get_setting('bot_status')
        
        if bot_status == "Yoqilgan":
            set_setting('bot_status', "O'chirilgan")
        else:
            set_setting('bot_status', "Yoqilgan")
        
        bot.answer_callback_query(call.id, "✅ Bot holati o'zgartirildi!")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="xolat"))
        
        bot.edit_message_text(
            "<b>✅ Bot holati muvaffaqiyatli o'zgartirildi!</b>",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data == "xolat":
        if not is_admin(user_id):
            return
        
        bot_status = get_setting('bot_status')
        
        if bot_status == "Yoqilgan":
            btn_text = "❌ O'chirish"
            status_emoji = "✅"
        else:
            btn_text = "✅ Yoqish"
            status_emoji = "❌"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(btn_text, callback_data="bot"))
        
        bot.edit_message_text(
            f"<b>📄 Hozirgi holat:</b> {status_emoji} {bot_status}",
            chat_id,
            message_id,
            parse_mode='HTML',
            reply_markup=markup
        )

# Matn xabarlar
@bot.message_handler(content_types=['text'])
def text_handler(message):
    user_id = message.from_user.id
    text = message.text
    first_name = message.from_user.first_name or ""
    
    # Bloklangan user
    if is_blocked(user_id):
        return
    
    # Bot holati
    bot_status = get_setting('bot_status')
    if bot_status == "O'chirilgan" and not is_admin(user_id):
        bot.send_message(
            user_id,
            "⛔️ <b>Bot vaqtinchalik o'chirilgan!</b>\n\n<i>Botda ta'mirlash ishlari olib borilayotgan bo'lishi mumkin!</i>",
            parse_mode='HTML'
        )
        return
    
    step, step_data = get_step(user_id)
    
    # Orqaga
    if text == "◀️ Orqaga":
        clear_step(user_id)
        
        is_subscribed, buttons = check_subscription(user_id)
        if not is_subscribed:
            markup = types.InlineKeyboardMarkup(buttons)
            bot.send_message(
                user_id,
                "<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
            return
        
        user_link = f'<a href="tg://user?id={user_id}">{first_name}</a>'
        channel = get_setting('channel')
        
        markup = types.InlineKeyboardMarkup()
        if channel:
            markup.row(types.InlineKeyboardButton(
                "🔎 Kino kodlari",
                url=f"https://t.me/{channel.replace('@', '')}"
            ))
        
        if is_admin(user_id):
            markup.row(types.InlineKeyboardButton(
                "🗄 Boshqaruv paneli",
                callback_data="boshqar"
            ))
        
        bot.send_message(
            user_id,
            f"🖐 <b>Assalomu alaykum, {user_link}\n\n"
            f"<blockquote>📊 Bot buyruqlari:\n"
            f"/start - ♻️ Botni qayta ishga tushirish\n"
            f"/help - ☎️ Qo'llab-quvvatlash</blockquote>\n\n"
            f"🔎 Film kodini yuboring:</b>",
            parse_mode='HTML',
            reply_markup=markup
        )
        return
    
    # Boshqaruv paneli
    if text == "🗄 Boshqaruv paneli" or text == "/panel":
        if not is_admin(user_id):
            return
        
        clear_step(user_id)
        bot.send_message(
            user_id,
            "<b>Admin paneliga xush kelibsiz!</b>",
            parse_mode='HTML',
            reply_markup=get_admin_panel()
        )
        return
    
    # Admin funksiyalari
    if is_admin(user_id):
        
        # Statistika
        if text == "📊 Statistika":
            all_users = get_all_users()
            
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("📅 Kunlik", callback_data="kunlik"),
                types.InlineKeyboardButton("📆 Haftalik", callback_data="haftalik"),
                types.InlineKeyboardButton("📊 Oylik", callback_data="oylik")
            )
            
            bot.send_message(
                user_id,
                f"<b>📊 Qaysi statistikani ko'rmoqchisiz?\n\n✅ Jami Foydalanuvchilar: {len(all_users)} ta</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
        
        # Xabarnoma
        elif text == "✉ Xabarnoma":
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("💠 Oddiy xabar", callback_data="send"),
                types.InlineKeyboardButton("💠 Userga xabar", callback_data="user")
            )
            markup.row(
                types.InlineKeyboardButton("❌ Yopish", callback_data="bosh"),
                types.InlineKeyboardButton("💠 Forward xabar", callback_data="send2")
            )
            
            bot.send_message(
                user_id,
                "<b>❗ Yuboriladigan xabar turini tanlang:</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
        
        # Kino yuklash
        elif text == "📥 Kino Yuklash":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "✅ Faqat kino rasmi va kinoni tashlash",
                callback_data="oddiyk"
            ))
            
            bot.send_message(
                user_id,
                "<b>⁉️ Qaysi usulda kino yuklaysiz?</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
        
        # Kanallar
        elif text == "📢 Kanallar":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💎 Majburiy obunalar", callback_data="majburiy"))
            markup.row(
                types.InlineKeyboardButton("🎥 Kino kanal", callback_data="qoshimcha"),
                types.InlineKeyboardButton("❌ Yopish", callback_data="bosh")
            )
            
            bot.send_message(
                user_id,
                "<b>Majburiy obunalarni sozlash bo'limidasiz:</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
        
        # Bot holati
        elif text == "🤖 Bot holati":
            bot_status = get_setting('bot_status')
            
            if bot_status == "Yoqilgan":
                btn_text = "❌ O'chirish"
                status_emoji = "✅"
            else:
                btn_text = "✅ Yoqish"
                status_emoji = "❌"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(btn_text, callback_data="bot"))
            
            bot.send_message(
                user_id,
                f"<b>📄 Hozirgi holat:</b> {status_emoji} {bot_status}",
                parse_mode='HTML',
                reply_markup=markup
            )
        
        # Adminlar
        elif text == "👥 Adminlar":
            if user_id == ADMIN_ID:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("➕ Yangi admin qo'shish", callback_data="add"))
                markup.row(
                    types.InlineKeyboardButton("📑 Ro'yxat", callback_data="list"),
                    types.InlineKeyboardButton("🗑 O'chirish", callback_data="remove")
                )
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("📑 Ro'yxat", callback_data="list"))
            
            bot.send_message(
                user_id,
                "🔰 <b>Quyidagilardan birini tanlang:</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
        
        # Step jarayonlari
        elif step == "add-admin":
            if user_id != ADMIN_ID:
                return
            
            if text.isdigit():
                new_admin = int(text)
                
                # Userning borligini tekshirish
                all_users = get_all_users()
                if new_admin not in all_users:
                    bot.send_message(
                        user_id,
                        "🚫 <b>Ushbu foydalanuvchi botdan foydalanmaydi!</b>\n\n🔢 Boshqa ID raqamni kiriting:",
                        parse_mode='HTML'
                    )
                    return
                
                if add_admin(new_admin):
                    bot.send_message(
                        user_id,
                        f"✅ <code>{new_admin}</code> <b>adminlar ro'yxatiga qo'shildi!</b>",
                        parse_mode='HTML',
                        reply_markup=get_admin_panel()
                    )
                else:
                    bot.send_message(
                        user_id,
                        "🚫 <b>Ushbu foydalanuvchi allaqachon admin!</b>\n\n🔢 Boshqa ID raqamni kiriting:",
                        parse_mode='HTML'
                    )
                    return
                
                clear_step(user_id)
            else:
                bot.send_message(user_id, "<b>Faqat raqamlardan foydalaning!</b>", parse_mode='HTML')
        
        elif step == "remove-admin":
            if user_id != ADMIN_ID:
                return
            
            if text.isdigit():
                admin_id = int(text)
                
                if admin_id == ADMIN_ID:
                    bot.send_message(user_id, "❌ Asosiy adminni o'chirish mumkin emas!", parse_mode='HTML')
                    return
                
                remove_admin(admin_id)
                bot.send_message(
                    user_id,
                    f"✅ <code>{admin_id}</code> <b>adminlar ro'yxatidan olib tashlandi!</b>",
                    parse_mode='HTML',
                    reply_markup=get_admin_panel()
                )
                clear_step(user_id)
            else:
                bot.send_message(user_id, "<b>Faqat raqamlardan foydalaning!</b>", parse_mode='HTML')
        
        elif step == "add-channel":
            if text.startswith('@'):
                channel_username = text[1:]
            else:
                channel_username = text
            
            try:
                chat = bot.get_chat(f"@{channel_username}")
                admins = bot.get_chat_administrators(f"@{channel_username}")
                
                is_bot_admin = any(admin.user.id == bot.get_me().id for admin in admins)
                
                if is_bot_admin:
                    if add_public_channel(channel_username):
                        bot.send_message(
                            user_id,
                            f"<b>✅ @{channel_username} nomli kanal muvaffaqiyatli qo'shildi.</b>",
                            parse_mode='HTML',
                            reply_markup=get_admin_panel()
                        )
                        clear_step(user_id)
                    else:
                        bot.send_message(user_id, "❌ Bu kanal allaqachon qo'shilgan!", parse_mode='HTML')
                else:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton(
                        "🛡 Kanalga admin qilish",
                        url=f"https://t.me/{bot_username}?startchannel=on"
                    ))
                    
                    bot.send_message(
                        user_id,
                        "<b>⚠️ Bot ushbu kanalda admin emas!</b>\n\n<i>🆙️ Qayta urinib ko'ring:</i>",
                        parse_mode='HTML',
                        reply_markup=markup
                    )
            except:
                bot.send_message(
                    user_id,
                    "<b>Kanal manzilini to'g'ri yuboring:</b>\n\n<b>📄 Namuna:</b> <code>@FireObuna</code>",
                    parse_mode='HTML'
                )
        
        elif step == "remove-channel":
            if text.startswith('@'):
                channel_username = text[1:]
            else:
                channel_username = text
            
            if remove_public_channel(channel_username):
                bot.send_message(
                    user_id,
                    f"<b>✅ @{channel_username} nomli kanal muvaffaqiyatli o'chirildi.</b>",
                    parse_mode='HTML',
                    reply_markup=get_admin_panel()
                )
                clear_step(user_id)
            else:
                bot.send_message(
                    user_id,
                    f"<b>❗ @{channel_username} ro'yxatdan topilmadi!</b>\n\n<i>🆙 Qayta urinib ko'ring!</i>",
                    parse_mode='HTML'
                )
        
        elif step == "add-chanel":
            if "https://t.me/+" in text and "-100" in text:
                lines = text.strip().split('\n')
                if len(lines) == 2:
                    invite_link = lines[0].strip()
                    chat_id = int(lines[1].strip())
                    
                    if add_private_channel(chat_id, invite_link):
                        bot.send_message(
                            user_id,
                            f"<b>✅ {invite_link} - kanal muvaffaqiyatli qo'shildi.</b>",
                            parse_mode='HTML',
                            reply_markup=get_admin_panel()
                        )
                        clear_step(user_id)
                    else:
                        bot.send_message(user_id, "❌ Bu kanal allaqachon qo'shilgan!", parse_mode='HTML')
                else:
                    bot.send_message(
                        user_id,
                        "<b>Kanal manzilini to'g'ri yuboring:</b>\n\n📄 <b>Namuna:</b> <code>https://t.me/+ZEcQiRY_pRphZTdi\n-100326189432</code>",
                        parse_mode='HTML'
                    )
            else:
                bot.send_message(
                    user_id,
                    "<b>Kanal manzilini to'g'ri yuboring:</b>\n\n📄 <b>Namuna:</b> <code>https://t.me/+ZEcQiRY_pRphZTdi\n-100326189432</code>",
                    parse_mode='HTML'
                )
        
        elif step == "remove-secret-channel":
            if "https://t.me/+" in text and "-100" in text:
                lines = text.strip().split('\n')
                if len(lines) == 2:
                    invite_link = lines[0].strip()
                    chat_id = int(lines[1].strip())
                    
                    remove_private_channel(chat_id)
                    bot.send_message(
                        user_id,
                        f"<b>✅ {invite_link} nomli maxfiy kanal muvaffaqiyatli o'chirildi.</b>",
                        parse_mode='HTML',
                        reply_markup=get_admin_panel()
                    )
                    clear_step(user_id)
                else:
                    bot.send_message(
                        user_id,
                        "<b>Kanal manzilini va ID sini to'g'ri yuboring:</b>\n\n📄 <b>Namuna:</b>\n<code>https://t.me/+ZEcQiRY_pRphZTdiHs\n-1001234567890</code>",
                        parse_mode='HTML'
                    )
            else:
                bot.send_message(
                    user_id,
                    "<b>Kanal manzilini va ID sini to'g'ri yuboring:</b>\n\n📄 <b>Namuna:</b>\n<code>https://t.me/+ZEcQiRY_pRphZTdiHs\n-1001234567890</code>",
                    parse_mode='HTML'
                )
        
        elif step == "add-channl":
            if text.startswith('@'):
                channel_username = text[1:]
            else:
                channel_username = text
            
            try:
                chat = bot.get_chat(f"@{channel_username}")
                admins = bot.get_chat_administrators(f"@{channel_username}")
                
                is_bot_admin = any(admin.user.id == bot.get_me().id for admin in admins)
                
                if is_bot_admin:
                    set_setting('channel', text)
                    bot.send_message(
                        user_id,
                        f"<b>✅ {text} nomli kanal muvaffaqiyatli qo'shildi.</b>",
                        parse_mode='HTML',
                        reply_markup=get_admin_panel()
                    )
                    clear_step(user_id)
                else:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton(
                        "🛡 Kanalga admin qilish",
                        url=f"https://t.me/{bot_username}?startchannel=on"
                    ))
                    
                    bot.send_message(
                        user_id,
                        "<b>⚠️ Bot ushbu kanalda admin emas!</b>\n\n<i>🆙️ Qayta urinib ko'ring:</i>",
                        parse_mode='HTML',
                        reply_markup=markup
                    )
            except:
                bot.send_message(
                    user_id,
                    "<b>⛔ Kanal manzilini to'g'ri yuboring:</b>\n\n<b>📄 Namuna:</b> <code>@FireObuna</code>",
                    parse_mode='HTML'
                )
        
        elif step == "user":
            if text.isdigit():
                set_step(user_id, "xabar", text)
                bot.send_message(
                    user_id,
                    "<b>📝 Yubormoqchi bo'lgan xabaringizni kiriting:</b>",
                    parse_mode='HTML',
                    reply_markup=get_panel_markup()
                )
            else:
                bot.send_message(user_id, "<b>Faqat raqamlardan foydalaning!</b>", parse_mode='HTML')
        
        elif step == "xabar":
            target_user = int(step_data)
            
            try:
                bot.send_message(
                    target_user,
                    f"<b>📩 Sizga yangi xabar keldi:</b>\n\n{text}",
                    parse_mode='HTML'
                )
                
                bot.send_message(
                    user_id,
                    "<b>✅ Xabaringiz foydalanuvchiga yetkazildi!</b>",
                    parse_mode='HTML',
                    reply_markup=get_admin_panel()
                )
            except:
                bot.send_message(user_id, "❌ Xabar yuborishda xatolik!", parse_mode='HTML')
            
            clear_step(user_id)
        
        elif step == "sendpost":
            clear_step(user_id)
            
            bot.send_message(user_id, "🔄 <b>Xabar yuborish boshlandi!</b>", parse_mode='HTML')
            
            all_users = get_all_users()
            sent = 0
            failed = 0
            
            for uid in all_users:
                try:
                    bot.copy_message(uid, user_id, message.message_id)
                    sent += 1
                except:
                    failed += 1
            
            bot.send_message(
                user_id,
                f"<b>✅ Xabar yuborildi!</b>\n\n"
                f"📨 Jami foydalanuvchilar: <b>{len(all_users)}</b>\n"
                f"✅ Yuborildi: <b>{sent}</b>\n"
                f"❌ Yuborilmadi: <b>{failed}</b>",
                parse_mode='HTML',
                reply_markup=get_admin_panel()
            )
        
        elif step == "sendfwrd":
            clear_step(user_id)
            
            bot.send_message(user_id, "🔄 <b>Xabar yuborish boshlandi!</b>", parse_mode='HTML')
            
            all_users = get_all_users()
            sent = 0
            failed = 0
            
            for uid in all_users:
                try:
                    bot.forward_message(uid, user_id, message.message_id)
                    sent += 1
                except:
                    failed += 1
            
            bot.send_message(
                user_id,
                f"<b>✅ Xabar yuborildi!</b>\n\n"
                f"📨 Jami foydalanuvchilar: <b>{len(all_users)}</b>\n"
                f"✅ Yuborildi: <b>{sent}</b>\n"
                f"❌ Yuborilmadi: <b>{failed}</b>",
                parse_mode='HTML',
                reply_markup=get_admin_panel()
            )
    
    # Oddiy foydalanuvchilar uchun
    else:
        # Obunani tekshirish
        is_subscribed, buttons = check_subscription(user_id)
        
        if not is_subscribed:
            markup = types.InlineKeyboardMarkup(buttons)
            bot.send_message(
                user_id,
                "<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling!</b>",
                parse_mode='HTML',
                reply_markup=markup
            )
            return
        
        # Kino kodini tekshirish
        if text.isdigit():
            send_movie(user_id, text)

# Rasm handler (kino yuklash)
@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    step, movie_code = get_step(user_id)
    
    if step == "rasm":
        photo_id = message.photo[-1].file_id
        
        bot.send_message(
            user_id,
            "<i>📄 Siz yuborgan rasm muvaffaqiyatli saqlandi! Bu qadamda kinoni matn qismi tayyor bo'lishi kerak!</i>\n\n"
            "<b>🎬 Endi esa filmni botga yuboring!</b>",
            parse_mode='HTML',
            reply_markup=get_panel_markup()
        )
        
        set_step(user_id, "kinoo", f"{movie_code}|{photo_id}")

# Video handler (kino yuklash)
@bot.message_handler(content_types=['video'])
def video_handler(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    step, step_data = get_step(user_id)
    
    if step == "kinoo":
        parts = step_data.split('|')
        movie_code = parts[0]
        photo_id = parts[1]
        
        video_id = message.video.file_id
        caption = message.caption or ""
        
        channel = get_setting('channel')
        
        # Ma'lumotlar bazasiga saqlash
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO movies (code, photo_id, video_id, caption, download_count) VALUES (?, ?, ?, ?, ?)",
                  (movie_code, photo_id, video_id, caption, 0))
        conn.commit()
        conn.close()
        
        # Kanalga yuborish
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "📥 Kinoni yuklab olish",
            url=f"https://t.me/{bot_username}?start={movie_code}"
        ))
        
        msg = bot.send_photo(
            channel,
            photo_id,
            caption=f"<b>🍿 Botga yangi film joylandi!\n\n"
                   f"🎞 Film haqida:\n<blockquote>{caption}</blockquote>\n\n"
                   f"🔢 Yuklash kodi: <code>{movie_code}</code>\n\n"
                   f"‼️ Bot manzili: @{bot_username}\n\n"
                   f"<i>❗ Diqqat quyidagi tugmani bosish orqali filmni olasiz.</i></b>",
            parse_mode='HTML',
            reply_markup=markup
        )
        
        # Adminga xabar
        markup2 = types.InlineKeyboardMarkup()
        markup2.add(types.InlineKeyboardButton(
            "📢 Filmni Ko'rish",
            url=f"https://t.me/{channel.replace('@', '')}/{msg.message_id}"
        ))
        
        bot.send_message(
            user_id,
            f"<blockquote>✅ Film bazaga muvaffaqiyatli joylandi!</blockquote>\n\n🔄 Kino kodi: <code>{movie_code}</code>",
            parse_mode='HTML',
            reply_to_message_id=message.message_id,
            reply_markup=markup2
        )
        
        clear_step(user_id)
        
        bot.send_message(
            user_id,
            "<b>✅ Admin paneliga qaytdingiz!</b>",
            parse_mode='HTML',
            reply_markup=get_admin_panel()
        )

# Chat join request handler
@bot.chat_join_request_handler()
def chat_join_request_handler(chat_join_request):
    chat_id = chat_join_request.chat.id
    user_id = chat_join_request.from_user.id
    
    # Maxfiy kanal a'zolariga qo'shish
    add_private_member(chat_id, user_id)
    
    # Foydalanuvchiga xabar
    try:
        bot.send_message(
            user_id,
            "<b>/start - bosing va kino kodini yuboring!</b>",
            parse_mode='HTML'
        )
    except:
        pass

# My chat member handler
@bot.my_chat_member_handler()
def my_chat_member_handler(update):
    if update.new_chat_member.status == "kicked":
        block_user(update.from_user.id)
    elif update.new_chat_member.status in ["member", "administrator"]:
        unblock_user(update.from_user.id)

# Bot ishga tushirish
if __name__ == '__main__':
    print("🤖 Bot ishga tushdi...")
    print(f"📌 Bot username: @{bot_username}")
    print(f"👨‍💼 Admin ID: {ADMIN_ID}")
    bot.infinity_polling(skip_pending=True)
