# Telegram Ticket Booking Bot

A Telegram bot that helps users book tickets by collecting:
- Departure city
- Arrival city
- Travel date
- Preferred airline (optional)

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root and add your Telegram bot token:
```
TELEGRAM_TOKEN=your_bot_token_here
```

3. Run the bot:
```bash
python bot.py
```

## Usage

1. Start a conversation with the bot using the `/start` command
2. Follow the prompts to enter:
   - Departure city
   - Arrival city
   - Travel date (DD/MM/YYYY format)
   - Preferred airline (optional)
3. Review and confirm your booking
4. Use `/cancel` at any time to cancel the booking process

## Features

- Step-by-step booking process
- Date validation
- Airline selection from predefined list
- Booking summary before confirmation
- Booking reference number generation
- Cancel booking at any time
