import os
import json
import random
import asyncio
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_CREDS"))
SHEET_NAME = os.getenv("SHEET_NAME")

MAX_OPTION_LENGTH = 100


def clean_option(text):
    text = str(text)
    if len(text) > MAX_OPTION_LENGTH:
        return text[:97] + "..."
    return text


def get_all_worksheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open(SHEET_NAME)
    return sheet.worksheets()


def generate_book_style_questions(df):
    questions = []
    df = df.sample(frac=1)

    # First 5 → Ask author
    for _, row in df.head(5).iterrows():
        correct = row["Book"]
        wrong = df[df["Author"] != row["Author"]]["Book"].sample(3).tolist()
        opts = random.sample([correct] + wrong, 4)

        questions.append({
            "question": f"Who wrote this book?",
            "options": [clean_option(o) for o in opts],
            "answer": opts.index(correct)
        })

    # Next 5 → Ask book
    for _, row in df.tail(5).iterrows():
        correct = row["Author"]
        wrong = (
            df[df["Author"] != correct]["Author"]
            .drop_duplicates()
            .sample(3)
            .tolist()
        )
        opts = random.sample([correct] + wrong, 4)

        questions.append({
            "question": f"Who is the author of '{clean_option(row['Book'])}'?",
            "options": [clean_option(o) for o in opts],
            "answer": opts.index(correct)
        })

    return questions


def generate_quote_style_questions(df):
    questions = []
    df = df.sample(frac=1)

    # First 5 → Ask author
    for _, row in df.head(5).iterrows():
        correct = row["Author"]
        wrong = (
            df[df["Author"] != correct]["Author"]
            .drop_duplicates()
            .sample(3)
            .tolist()
        )
        opts = random.sample([correct] + wrong, 4)

        questions.append({
            "question": f"Who said:\n\"{clean_option(row['Quote'])}\"?",
            "options": [clean_option(o) for o in opts],
            "answer": opts.index(correct)
        })

    # Next 5 → Ask quote
    for _, row in df.tail(5).iterrows():
        correct = row["Quote"]
        wrong = df[df["Author"] != row["Author"]]["Quote"].sample(3).tolist()
        opts = random.sample([correct] + wrong, 4)

        questions.append({
            "question": f"Which quote belongs to {row['Author']}?",
            "options": [clean_option(o) for o in opts],
            "answer": opts.index(clean_option(correct))
        })

    return questions


async def main():
    bot = Bot(token=BOT_TOKEN)
    worksheets = get_all_worksheets()

    for ws in worksheets:
        df = pd.DataFrame(ws.get_all_records())

        if "Book" in df.columns and "Author" in df.columns:
            questions = generate_book_style_questions(df)

        elif "Quote" in df.columns and "Author" in df.columns:
            questions = generate_quote_style_questions(df)

        else:
            continue  # Skip unknown format sheets

        # Optional: Send sheet name as header
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


if __name__ == "__main__":
    asyncio.run(main())
