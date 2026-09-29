import os
import time
import threading
from datetime import datetime
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8819406038:AAEn5j4IVQI3v6neCQ89rC7tx8nNjzkjvZw"      # BotFather မှ ရသော Token ထည့်ပါ
AGENT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vYWcuYnVmZmFsbzY4OC5jb20vYXBpL2F1dGgvcmVmcmVzaCIsImlhdCI6MTc5MDY2ODQxNiwiZXhwIjoxNzkwNjc1OTkyLCJuYmYiOjE3OTA2Njg3OTIsImp0aSI6InJ3VGJSSWtOWVFxRmlVMVUiLCJzdWIiOiIyNTAyNzczIiwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyJ9.3FTjXYj_9vuIllfYeuSweeRKCIO9bpZ8C2zWf--I5bs"  # Buffalo Agent Token (eyJ...) ထည့်ပါ
NOTIFICATION_CHAT_ID = "8736201630"              # Reminder / Buttons သတိပေးစာ ပို့လိုသော Group/Chat ID

BASE_URL = "https://ag.buffalo688.com/api"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Render Health Check & Web Server
@app.route('/')
def home():
    return "Bot is alive and running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Token နှင့် Header များ ပြင်ဆင်ပေးသည့် Function
def get_headers():
    token = str(AGENT_TOKEN).strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def fmt_money(val):
    try:
        return f"{float(val):,.0f}"
    except:
        return "0"

def call_api(endpoint, method="GET", json_data=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        headers = get_headers()
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=15)
        else:
            res = requests.post(url, headers=headers, json=json_data, timeout=15)
        
        if res.status_code == 200:
            try:
                return res.json(), None
            except:
                return None, "Invalid Response Format"
        elif res.status_code == 401:
            return None, "Expired"
        else:
            return None, f"HTTP Error {res.status_code}"
    except Exception as e:
        return None, str(e)

# ==================== INLINE BUTTON KEYBOARDS ====================

def make_deposit_buttons(req_id):
    markup = InlineKeyboardMarkup()
    btn_app = InlineKeyboardButton("Approved", callback_data=f"dep_approve_{req_id}")
    btn_rej = InlineKeyboardButton("Decline", callback_data=f"dep_reject_{req_id}")
    markup.row(btn_app, btn_rej)
    return markup

def make_withdraw_buttons(req_id, username, amount):
    markup = InlineKeyboardMarkup()
    btn_app = InlineKeyboardButton("Approved", callback_data=f"wit_approve_{req_id}")
    btn_rej = InlineKeyboardButton("Decline", callback_data=f"wit_reject_{req_id}")
    btn_to = InlineKeyboardButton("Decline 1", callback_data=f"wit_turnover_{req_id}_{username}")
    markup.row(btn_app, btn_rej)
    markup.row(btn_to)
    return markup

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['status'])
def handle_status(message):
    dep_res, err1 = call_api("check/deposits")
    wit_res, err2 = call_api("check/withdraws")

    if err1 == "Expired" or err2 == "Expired":
        bot.reply_to(message, "🔎 Token: ❌ Expired\n⏰ Expires: 0.0h\n📝 Pending deposit : 0\n📝 Pending withdrawal: 0")
        return

    pending_dep = len(dep_res) if isinstance(dep_res, list) else 0
    pending_wit = len(wit_res) if isinstance(wit_res, list) else 0

    msg = (
        f"🔎 Token: ✅ Valid\n"
        f"⏰ Expires: 12.0h\n"
        f"📝 Pending deposit : {pending_dep}\n"
        f"📝 Pending withdrawal: {pending_wit}"
    )
    bot.reply_to(message, msg)

@bot.message_handler(commands=['daily'])
def handle_daily(message):
    today = datetime.now().strftime("%Y-%m-%d")
    data, err = call_api("dashboard/data")
    if err or not data:
        bot.reply_to(message, "❌ အချက်အလက်များ ယူ၍ မရရှိပါ သို့မဟုတ် Token သက်တမ်း ကုန်နေပါသည်။")
        return

    msg = (
        f"🗓️ Daily Report ( {today})\n\n"
        f"🔺 Deposit : {data.get('today_deposit_count', 0)}/ {fmt_money(data.get('today_deposit_amount', 0))} MMK\n\n"
        f"🔻 Withdrawal: {data.get('today_withdraw_count', 0)}/ {fmt_money(data.get('today_withdraw_amount', 0))} MMK\n\n"
        f"↔️ Profit: {fmt_money(data.get('today_profit', 0))} MMK"
    )
    bot.reply_to(message, msg)

@bot.message_handler(commands=['weekly', 'Weekly'])
def handle_weekly(message):
    data, err = call_api("dashboard/data")
    if err or not data:
        bot.reply_to(message, "❌ အချက်အလက်များ ယူ၍ မရရှိပါ သို့မဟုတ် Token သက်တမ်း ကုန်နေပါသည်။")
        return

    start_date = data.get("weekly_start", datetime.now().strftime("%Y-%m-%d"))
    end_date = datetime.now().strftime("%Y-%m-%d")

    msg = (
        f"📊 Weekly Report ( {start_date}➖ to➖{end_date} )\n\n"
        f"🔺 Deposit: {data.get('weekly_deposit_count', 0)}/ {fmt_money(data.get('weekly_deposit_amount', 0))} MMK\n\n"
        f"🔻 Withdrawal: {data.get('weekly_withdraw_count', 0)}/ {fmt_money(data.get('weekly_withdraw_amount', 0))} MMK\n\n"
        f"↔️ Profit: {fmt_money(data.get('weekly_profit', 0))} MMK"
    )
    bot.reply_to(message, msg)

@bot.message_handler(commands=['monthly'])
def handle_monthly(message):
    month_str = datetime.now().strftime("%Y-%m")
    data, err = call_api("dashboard/data")
    if err or not data:
        bot.reply_to(message, "❌ အချက်အလက်များ ယူ၍ မရရှိပါ သို့မဟုတ် Token သက်တမ်း ကုန်နေပါသည်။")
        return

    msg = (
        f"📈 Monthly Report ({month_str} )\n\n"
        f"🔺 Deposit: {data.get('monthly_deposit_count', 0)}/ {fmt_money(data.get('monthly_deposit_amount', 0))} MMK\n\n"
        f"🔻 Withdrawal: {data.get('monthly_withdraw_count', 0)}/ {fmt_money(data.get('monthly_withdraw_amount', 0))} MMK\n\n"
        f"↔️ Profit: {fmt_money(data.get('monthly_profit', 0))} MMK"
    )
    bot.reply_to(message, msg)

@bot.message_handler(commands=['yearly'])
def handle_yearly(message):
    year_str = datetime.now().strftime("%Y")
    data, err = call_api("dashboard/data")
    if err or not data:
        bot.reply_to(message, "❌ အချက်အလက်များ ယူ၍ မရရှိပါ သို့မဟုတ် Token သက်တမ်း ကုန်နေပါသည်။")
        return

    msg = (
        f"📈 Yearly Report ( {year_str} )\n\n"
        f"🔺 Deposit: {data.get('yearly_deposit_count', 0)}/ {fmt_money(data.get('yearly_deposit_amount', 0))} MMK\n\n"
        f"🔻 Withdrawal: {data.get('yearly_withdraw_count', 0)}/ {fmt_money(data.get('yearly_withdraw_amount', 0))} MMK\n\n"
        f"↔️ Profit: {fmt_money(data.get('yearly_profit', 0))} MMK"
    )
    bot.reply_to(message, msg)

@bot.message_handler(commands=['balance'])
def handle_balance(message):
    wait_msg = bot.reply_to(message, "🔎 Checking balances....")
    data, err = call_api("dashboard/data")
    if err or not data:
        bot.edit_message_text("❌ အချက်အလက်များ ယူ၍ မရရှိပါ သို့မဟုတ် Token သက်တမ်း ကုန်နေပါသည်။", chat_id=message.chat.id, message_id=wait_msg.message_id)
        return

    res_msg = (
        f"💳 Agent Credit: {fmt_money(data.get('agent_balance', 0))} MMK\n\n"
        f"✨ All Deposit: {data.get('all_deposit_count', 0)}/ {fmt_money(data.get('all_deposit_amount', 0))} MMK\n\n"
        f"✨All Withdrawal: {data.get('all_withdraw_count', 0)}/ {fmt_money(data.get('all_withdraw_amount', 0))} mmk\n\n"
        f"💰Profit : {fmt_money(data.get('total_profit', 0))} mmk"
    )
    bot.edit_message_text(res_msg, chat_id=message.chat.id, message_id=wait_msg.message_id)

# ==================== BUTTON CALLBACK HANDLER ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_button_click(call):
    data = call.data
    
    # 1. Deposit Approve / Reject
    if data.startswith("dep_approve_"):
        req_id = data.split("_")[2]
        res, err = call_api(f"deposit/approve/{req_id}", method="POST")
        if not err:
            bot.edit_message_text(f"🔷 Deposit Approved by Bot\n\nID: {req_id}\nSTATUS: ✅ အတည်ပြုပြီးပါပြီ", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ လုပ်ဆောင်မှု မအောင်မြင်ပါ: {err}")

    elif data.startswith("dep_reject_"):
        req_id = data.split("_")[2]
        res, err = call_api(f"deposit/reject/{req_id}", method="POST")
        if not err:
            bot.edit_message_text(f"🔷 Deposit Rejected\n\nID: {req_id}\nSTATUS: ❌ ငြင်းပယ်လိုက်ပါပြီ", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ လုပ်ဆောင်မှု မအောင်မြင်ပါ: {err}")

    # 2. Withdrawal Approve / Reject
    elif data.startswith("wit_approve_"):
        req_id = data.split("_")[2]
        res, err = call_api(f"withdraw/approve/{req_id}", method="POST")
        if not err:
            bot.edit_message_text(f"♦️ Withdrawal Approved\n\nID: {req_id}\nSTATUS: ✅ အတည်ပြုပြီးပါပြီ", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ လုပ်ဆောင်မှု မအောင်မြင်ပါ: {err}")

    elif data.startswith("wit_reject_"):
        req_id = data.split("_")[2]
        res, err = call_api(f"withdraw/reject/{req_id}", method="POST")
        if not err:
            bot.edit_message_text(f"♦️ Withdrawal Rejected\n\nID: {req_id}\nSTATUS: ❌ ရိုးရိုးငြင်းပယ်လိုက်ပါပြီ", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ လုပ်ဆောင်မှု မအောင်မြင်ပါ: {err}")

    # 3. Withdrawal Turnover Reject (Decline 1)
    elif data.startswith("wit_turnover_"):
        parts = data.split("_")
        req_id = parts[2]
        username = parts[3] if len(parts) > 3 else "User"

        # User ၏ လက်ရှိ Balance ကို ရယူခြင်း
        user_info, err = call_api(f"user/details/{username}")
        user_balance = user_info.get("balance", 0) if user_info else 0

        # Turnover ဖြင့် Reject လုပ်ခြင်း
        res, err = call_api(f"withdraw/reject/{req_id}", method="POST", json_data={"reason": "turnover"})
        if not err:
            msg = (
                f"♦️ Withdrawal Request Rejected by Bot\n\n"
                f"ID: {req_id}\n"
                f"User: {username}\n"
                f"STATUS: ⚠️ Turnover ဖြင့် ငြင်းပယ်လိုက်ပါပြီ\n\n"
                f"🔄 ကစားအားသတ်မှတ်ချက်: User ၏ လက်ရှိ Balance {fmt_money(user_balance)} MMK အတိုင်း Turnover ပြည့်အောင် ပြန်လည် ကစားရပါမည်။"
            )
            bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"❌ လုပ်ဆောင်မှု မအောင်မြင်ပါ: {err}")

# ==================== BACKGROUND REMINDER LOOP ====================

pending_tracker = {}

def auto_reminder_loop():
    while True:
        try:
            target_chat = NOTIFICATION_CHAT_ID
            if target_chat:
                # Deposit Reminders
                dep_list, _ = call_api("check/deposits")
                if isinstance(dep_list, list) and len(dep_list) > 0:
                    for item in dep_list:
                        req_id = item.get("id")
                        pending_tracker[req_id] = pending_tracker.get(req_id, 0) + 5
                        mins = pending_tracker[req_id]
                        
                        alert = (
                            f"// {mins} မိနစ်ကြာနေပါပြီ သင်အတည်မပြုရသေးပါ\n\n"
                            f"🔷 Deposit Request\n"
                            f"ID: {req_id}\n"
                            f"User: {item.get('username')}\n"
                            f"Amount: {fmt_money(item.get('amount'))} MMK\n"
                            f"Payment: {item.get('payment_method', 'N/A')}\n"
                            f"Code: {item.get('trans_id', 'N/A')}\n"
                            f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                        )
                        bot.send_message(target_chat, alert, reply_markup=make_deposit_buttons(req_id))

                # Withdrawal Reminders
                wit_list, _ = call_api("check/withdraws")
                if isinstance(wit_list, list) and len(wit_list) > 0:
                    for item in wit_list:
                        req_id = item.get("id")
                        pending_tracker[req_id] = pending_tracker.get(req_id, 0) + 5
                        mins = pending_tracker[req_id]
                        
                        alert = (
                            f"// {mins} မိနစ်ကြာနေပါပြီ သင်အတည်မပြုရသေးပါ\n\n"
                            f"♦️ Withdrawal Request\n"
                            f"ID: {req_id}\n"
                            f"User: {item.get('username')}\n"
                            f"Amount: {fmt_money(item.get('amount'))} MMK\n"
                            f"Payment: {item.get('payment_method', 'N/A')}\n"
                            f"Phone: {item.get('phone', 'N/A')}\n"
                            f"Bank name: {item.get('bank_name', 'N/A')}\n"
                            f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                        )
                        bot.send_message(target_chat, alert, reply_markup=make_withdraw_buttons(req_id, item.get('username'), item.get('amount')))

        except Exception as e:
            print("Reminder Loop Error:", e)
        
        time.sleep(300)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    t_rem = threading.Thread(target=auto_reminder_loop)
    t_rem.daemon = True
    t_rem.start()

    print("Bot started successfully...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
