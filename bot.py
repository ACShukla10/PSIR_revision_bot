import os
import json
import random
import asyncio
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from telegram import Bot

# ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_CREDS"))

MAX_OPTION_LENGTH = 100


def clean_option(text):
    text = str(text)
    return text[:97] + "..." if len(text) > MAX_OPTION_LENGTH else text


def get_all_worksheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=scopes)
    client = gspread.authorize(creds)

    # 🔥 NO DRIVE API — open directly by key
    sheet = client.open_by_key(SPREADSHEET_ID)

    return sheet.worksheets()


def safe_sample(series, n):
    unique_vals = list(series.dropna().unique())
    if len(unique_vals) <= n:
        return unique_vals
    return random.sample(unique_vals, n)


def generate_book_questions(df):
    questions = []
    df = df.sample(frac=1).reset_index(drop=True)

    # Need minimum data
    if df["Author"].nunique() < 4:
        return []

    # First 5 → Ask author (book options)
    for _, row in df.head(5).iterrows():
        correct = row["Book"]
        wrong = safe_sample(df[df["Author"] != row["Author"]]["Book"], 3)
        options = random.sample([correct] + wrong, len(wrong) + 1)

        questions.append({
            "question": "Who wrote this book?",
            "options": [clean_option(o) for o in options],
            "answer": options.index(correct)
        })

    # Next 5 → Ask book (author options)
    for _, row in df.tail(5).iterrows():
        correct = row["Author"]
        wrong = safe_sample(df[df["Author"] != correct]["Author"], 3)
        options = random.sample([correct] + wrong, len(wrong) + 1)

        questions.append({
            "question": f"Who is the author of '{clean_option(row['Book'])}'?",
            "options": [clean_option(o) for o in options],
            "answer": options.index(correct)
        })

    return questions


def generate_quote_questions(df):
    questions = []
    df = df.sample(frac=1).reset_index(drop=True)

    if df["Author"].nunique() < 4:
        return []

    # First 5 → Ask author
    for _, row in df.head(5).iterrows():
        correct = row["Author"]
        wrong = safe_sample(df[df["Author"] != correct]["Author"], 3)
        options = random.sample([correct] + wrong, len(wrong) + 1)

        questions.append({
            "question": f'Who said:\n"{clean_option(row["Quote"])}"',
            "options": [clean_option(o) for o in options],
            "answer": options.index(correct)
        })

    # Next 5 → Ask quote
    for _, row in df.tail(5).iterrows():
        correct = row["Quote"]
        wrong = safe_sample(df[df["Author"] != row["Author"]]["Quote"], 3)
        options = random.sample([correct] + wrong, len(wrong) + 1)

        questions.append({
            "question": f"Which quote belongs to {row['Author']}?",
            "options": [clean_option(o) for o in options],
            "answer": options.index(clean_option(correct))
        })

    return questions


async def main():
    bot = Bot(token=BOT_TOKEN)
    worksheets = get_all_worksheets()

    for ws in worksheets:
        df = pd.DataFrame(ws.get_all_records())

        if not {"Author"}.issubset(df.columns):
            continue

        if "Book" in df.columns:
            questions = generate_book_questions(df)
        elif "Quote" in df.columns:
            questions = generate_quote_questions(df)
        else:
            continue

        if not questions:
            continue

        await bot.send_message(chat_id=CHAT_ID, text=f"📘 {ws.title}")

        for q in questions:
            await bot.send_poll(
                chat_id=CHAT_ID,
                question=q["question"],
                options=q["options"],
                type="quiz",
                correct_option_id=q["answer"],
                is_anonymous=False
            )
            await asyncio.sleep(2)  # avoid Telegram flood limit


if __name__ == "__main__":
    asyncio.run(main())
