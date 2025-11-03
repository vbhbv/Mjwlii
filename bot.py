import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes 
from telegram.constants import ParseMode
from telegram import error as TelegramError

# --- إعدادات البوت والثوابت ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# V17.0: معرف القناة
CHANNEL_ID = "@books921383837" 

TEMP_RESULTS_KEY = "current_search_results" 


# ----------------------------------------------------------------------
# --- دالة البحث داخل القناة (V17.3: تثبيت الهيكل) ---
# ----------------------------------------------------------------------
async def search_telegram_channel(context, chat_id, query: str):
    
    if not CHANNEL_ID or CHANNEL_ID == "YOUR_CHANNEL_ID":
        await context.bot.send_message(chat_id=chat_id, text="❌ **خطأ الإعداد:** الرجاء تحديد `CHANNEL_ID` في الكود.")
        return []

    try:
        # 💥 V17.3: نستخدم الدالة search_for_messages مع التأكيد على اسم المعامل (query)
        messages = await context.bot.search_for_messages(
            chat_id=CHANNEL_ID,
            query=query, 
            limit=5  
        )
        
        # تحويل الرسائل إلى قائمة نتائج مبسطة
        results = []
        for msg in messages:
            if msg.document or msg.photo or msg.video:
                message_text = msg.caption if msg.caption else (msg.text if msg.text else "رسالة بدون عنوان")
                results.append({
                    "message_id": msg.message_id, 
                    "title": message_text[:100].replace('\n', ' ')
                })

        return results
        
    except TelegramError.BadRequest as e:
        if "Bad Request: chat not found" in str(e):
             await context.bot.send_message(chat_id=chat_id, text="❌ خطأ: لم يتم العثور على القناة. تأكد من أن البوت مشرف وأن `CHANNEL_ID` صحيح.")
        elif "Bad Request: message is not modified" in str(e):
             pass
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ خطأ تيليجرام: {e}")
        return []
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ خطأ عام أثناء البحث: {e}")
        return []


# ----------------------------------------------------------------------
# --- دالة Callback (إعادة توجيه الرسالة) ---
# ----------------------------------------------------------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    
    if data.startswith("dl|"):
        try:
            index_str = data.split("|", 1)[1]
            index = int(index_str)
            message_id_to_forward = context.user_data[TEMP_RESULTS_KEY][index]["message_id"]

        except Exception:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ حدث خطأ أثناء معالجة زر التحميل (نتيجة غير صالحة).")
            return
            
        await query.edit_message_text("✅ جارٍ إرسال الكتاب...")
        
        try:
            await context.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=CHANNEL_ID, 
                message_id=message_id_to_forward 
            )
            await query.message.delete()
            
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ فشل إعادة توجيه الرسالة. تأكد من أن البوت مشرف في القناة.\nالخطأ: {e}")


# ----------------------------------------------------------------------
# --- دوال تيليجرام الرئيسية (start، search_cmd، main) ---
# ----------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 بوت المكتبة الداخلية جاهز!\n"
        "أرسل /search متبوعًا باسم الكتاب للبحث داخل قناة المكتبة المحددة."
    )

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("استخدم: /search اسم الكتاب أو المؤلف")
        return

    msg = await update.message.reply_text(f"🔍 أبحث عن **{query}** داخل المكتبة المحددة...")
    
    try:
        results = await search_telegram_channel(context, update.message.chat_id, query)

        if not results:
            await msg.edit_text("❌ لم يتم العثور على نتائج في المكتبة الداخلية. حاول بكلمات مختلفة.")
            return

        buttons = []
        text_lines = []
        
        context.user_data[TEMP_RESULTS_KEY] = results
        
        for i, item in enumerate(results, start=0):
            title = item.get("title")
            text_lines.append(f"{i+1}. {title}")
            buttons.append([InlineKeyboardButton(f"📥 تحميل {i+1}", callback_data=f"dl|{i}")])
            
        reply = "✅ تم العثور على الكتب التالية:\n" + "\n".join(text_lines)
        await msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
         await msg.edit_text(f"⚠️ حدث خطأ أثناء البحث: {e}")

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing in environment variables.")

    # هذا هو السطر الذي كان يسبب الخطأ في الصورة 1000024176.jpg.
    # الحل يكمن في ضمان تثبيت إصدار 20.x من المكتبة.
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("البوت بدأ العمل.")
    app.run_polling()

if __name__ == "__main__":
    main()
