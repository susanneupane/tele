import os
import json
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# States for conversation handler
DEPARTURE, ARRIVAL, DATE, AIRLINE, CONFIRM = range(5)

# Calendar helper functions
def create_calendar(start_year=None, start_month=None):
    """
    Returns an InlineKeyboardMarkup showing 3 months (current and next two) stacked vertically, dates in YYYY-MM-DD format.
    """
    now = datetime.now()
    if start_year is None:
        start_year = now.year
    if start_month is None:
        start_month = now.month
    week_days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    all_months = []
    for i in range(3):
        # Calculate year/month for each of the 3 months
        month = (start_month + i - 1) % 12 + 1
        year = start_year + ((start_month + i - 1) // 12)
        first_day = datetime(year, month, 1)
        next_month = first_day.replace(day=28) + timedelta(days=4)
        last_day = (next_month - timedelta(days=next_month.day)).day
        keyboard = []
        # Month header
        keyboard.append([InlineKeyboardButton(f"{first_day.strftime('%B %Y')}", callback_data="IGNORE")])
        # Weekday header
        keyboard.append([InlineKeyboardButton(day, callback_data="IGNORE") for day in week_days])
        # Calendar days
        row = []
        for blank in range((first_day.weekday() + 1) % 7):
            row.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
        for day in range(1, last_day + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            row.append(InlineKeyboardButton(str(day), callback_data=f"DAY_{date_str}"))
            if len(row) == 7:
                keyboard.append(row)
                row = []
        if row:
            while len(row) < 7:
                row.append(InlineKeyboardButton(" ", callback_data="IGNORE"))
            keyboard.append(row)
        all_months.extend(keyboard)
    return InlineKeyboardMarkup(all_months)


# Sample airlines list
AIRLINES = ["All Airlines", "Qatar Airways", "Emirates", "Turkish Airlines", "Air India"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for departure city."""
    await update.message.reply_text(
        "Welcome to the Ticket Booking Bot! 🎫\n"
        "Please enter your departure city:"
    )
    return DEPARTURE

async def departure(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store departure city and ask for arrival city."""
    context.user_data['departure'] = update.message.text
    await update.message.reply_text("Please enter your arrival city:")
    return ARRIVAL

async def arrival(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store arrival city and show calendar for date selection."""
    context.user_data['arrival'] = update.message.text
    # Send a loading message first
    loading_msg = await update.message.reply_text("Loading calendar...")
    # Edit the message to show the calendar
    await loading_msg.edit_text(
        "Please select your travel date:",
        reply_markup=create_calendar()
    )
    return DATE

# Handler for calendar callback queries
def parse_calendar_callback(data):
    if data.startswith("DAY_"):
        # Expect YYYY-MM-DD
        return "DAY", data[4:]
    elif data.startswith("PREV_"):
        _, y, m = data.split('_')
        return "PREV", (int(y), int(m))
    elif data.startswith("NEXT_"):
        _, y, m = data.split('_')
        return "NEXT", (int(y), int(m))
    else:
        return data, None

async def calendar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action, value = parse_calendar_callback(query.data)
    if action == "IGNORE":
        return DATE
    elif action == "DAY":
        # value is DD/MM/YYYY
        context.user_data['date'] = value
        await query.edit_message_text(f"Selected date: {value}\nPlease select your airline:", reply_markup=airline_keyboard())
        return AIRLINE
    elif action == "PREV":
        y, m = value
        await query.edit_message_reply_markup(reply_markup=create_calendar(y, m))
        return DATE
    elif action == "NEXT":
        y, m = value
        await query.edit_message_reply_markup(reply_markup=create_calendar(y, m))
        return DATE
    else:
        return DATE


async def calendar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action, value = parse_calendar_callback(query.data)
    if action == "IGNORE":
        return DATE
    elif action == "PREV":
        y, m = value
        await query.edit_message_reply_markup(reply_markup=create_calendar(y, m))
        return DATE
    elif action == "NEXT":
        y, m = value
        await query.edit_message_reply_markup(reply_markup=create_calendar(y, m))
        return DATE
    elif action == "DAY":
        # Save selected date and show airline options
        context.user_data['date'] = value
        keyboard = [[airline] for airline in AIRLINES]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await query.edit_message_text(f"Selected date: {value}\nPlease select your airline:")
        await query.message.reply_text("Please select your airline:", reply_markup=reply_markup)
        return AIRLINE
    return DATE

async def airline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store airline preference and show booking summary."""
    context.user_data['airline'] = update.message.text
    
    # Create booking summary
    booking_info = (
        "📋 Booking Summary:\n"
        f"From: {context.user_data['departure']}\n"
        f"To: {context.user_data['arrival']}\n"
        f"Date: {context.user_data['date']}\n"
        f"Airline: {context.user_data['airline']}\n\n"
        "Would you like to confirm this booking? (Yes/No)"
    )
    
    keyboard = [['Yes', 'No']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(booking_info, reply_markup=reply_markup)
    return CONFIRM

BOOKINGS_FILE = "bookings.json"

def load_bookings():
    print(f"[DEBUG] Loading bookings from: {os.path.abspath(BOOKINGS_FILE)}")
    if not os.path.exists(BOOKINGS_FILE):
        print("[DEBUG] bookings.json does not exist.")
        return {}
    with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            print(f"[DEBUG] Loaded bookings: {data}")
            return data
        except Exception as e:
            print(f"[DEBUG] Failed to load bookings: {e}")
            return {}

def save_bookings(bookings):
    print(f"[DEBUG] Saving bookings to: {os.path.abspath(BOOKINGS_FILE)}")
    print(f"[DEBUG] Bookings to save: {bookings}")
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, indent=2)

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle booking confirmation."""
    if update.message.text.lower() == 'yes':
        user_id = str(update.message.from_user.id)
        print(f"[DEBUG] Confirming booking for user_id: {user_id}")
        bookings = load_bookings()
        ref = datetime.now().strftime("%Y%m%d%H%M%S")
        booking_obj = {
            "ref": ref,
            "departure": context.user_data.get('departure'),
            "arrival": context.user_data.get('arrival'),
            "date": context.user_data.get('date'),
            "airline": context.user_data.get('airline')
        }
        print(f"[DEBUG] Booking object: {booking_obj}")
        if user_id not in bookings:
            bookings[user_id] = []
        bookings[user_id].append(booking_obj)
        save_bookings(bookings)
        await update.message.reply_text(
            f"✅ Booking confirmed!\nYour booking reference number: #{ref}",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Booking cancelled. Type /start to begin a new booking.",
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "Booking cancelled. Type /start to begin a new booking.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def bookings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    print(f"[DEBUG] /booking command for user_id: {user_id}")
    bookings_all = load_bookings()
    print(f"[DEBUG] All bookings loaded: {bookings_all}")
    bookings = bookings_all.get(user_id, [])
    if not bookings:
        await update.message.reply_text("You have no bookings.")
        return
    for idx, booking in enumerate(bookings):
        text = (f"📋 Booking #{idx+1} (Ref: {booking['ref']})\n"
                f"From: {booking['departure']}\n"
                f"To: {booking['arrival']}\n"
                f"Date: {booking['date']}\n"
                f"Airline: {booking['airline']}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Remove", callback_data=f"REMOVE_{booking['ref']}")]
        ])
        await update.message.reply_text(text, reply_markup=keyboard)

async def remove_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    ref = query.data.split('_', 1)[1]
    bookings = load_bookings()
    user_bookings = bookings.get(user_id, [])
    new_bookings = [b for b in user_bookings if b['ref'] != ref]
    bookings[user_id] = new_bookings
    save_bookings(bookings)
    await query.edit_message_text(f"Booking with reference #{ref} has been removed.")


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN').replace("'", "").replace(' ', '')) .build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            DEPARTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, departure)],
            ARRIVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, arrival)],
            DATE: [CallbackQueryHandler(calendar_handler)],
            AIRLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, airline)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('booking', bookings_command))
    application.add_handler(CallbackQueryHandler(remove_booking_callback, pattern=r'^REMOVE_.*'))
    application.run_polling()


if __name__ == '__main__':
    main()
