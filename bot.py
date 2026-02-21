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
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_CREDS"))
SHEET_NAME = os.getenv("SHEET_NAME")

# Telegram limit
MAX_OPTION_LENGTH = 100

def clean_option(text):
    text = str(text)
    if len(text) > MAX_OPTION_LENGTH:
        return text[:97] + "..."
    return text

def get_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)

    books_df = pd.DataFrame(sheet.worksheet("Books").get_all_records())
    quotes_df = pd.DataFrame(sheet.worksheet("Quotes").get_all_records())

    return books_df, quotes_df

def generate_book_questions(df):
    questions = []

    df = df.sample(frac=1)

    # First 5: Ask author → 4 book options
    for _, row in df.head(5).iterrows():
        correct = row["Book"]
        options = df[df["Author"] == row["Author"]]["Book"].tolist()
        wrong = df[df["Author"] != row["Author"]]["Book"].sample(3).tolist()
        opts = random.sample([correct] + wrong, 4)

        questions.append({
            "question": f"Who wrote this book?",
            "options": [clean_option(o) for o in opts],
            "answer": opts.index(correct)
        })

    # Next 5: Ask book → 4 author options
    for _, row in df.tail(5).iterrows():
        correct = row["Author"]
        wrong = df[df["Author"] != correct]["Author"].drop_duplicates().sample(3).tolist()
        opts = random.sample([correct] + wrong, 4)

        questions.append({
            "question": f"Who is the author of '{row['Book']}'?",
            "options": [clean_option(o) for o in opts],
            "answer": opts.index(correct)
        })

    return questions

def generate_quote_questions(df):
    questions = []

    df = df.sample(frac=1)

    # First 5: Ask author → 4 quote options
    for _, row in df.head(5).iterrows():
        correct = row["Quote"]
        wrong = df[df["Author"] != row["Author"]]["Quote"].sample(3).tolist()
        opts = random.sample([correct] + wrong, 4)

        questions.append({
            "question": f"Who said this?",
            "options": [clean_option(o) for o in opts],
            "answer": opts.index(clean_option(correct))
        })

    # Next 5: Ask quote → 4 author options
    for _, row in df.tail(5).iterrows():
        correct = row["Author"]
        wrong = df[df["Author"] != correct]["Author"].drop_duplicates().sample(3).tolist()
        opts = random.sample([correct] + wrong, 4)

        questions.append({
            "question": f"Who said:\n\"{clean_option(row['Quote'])}\"?",
            "options": [clean_option(o) for o in opts],
            "answer": opts.index(correct)
        })

    return questions

async def main():
    bot = Bot(token=BOT_TOKEN)
    books_df, quotes_df = get_sheets()

    questions = (
        generate_book_questions(books_df) +
        generate_quote_questions(quotes_df)
    )

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