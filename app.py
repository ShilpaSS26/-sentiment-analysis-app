"""
Sentiment Analysis Web Application
------------------------------------
A Flask app that takes text typed in by a user, runs it through TextBlob,
and shows whether the sentiment is Positive, Negative, or Neutral, along
with the raw Polarity and Subjectivity scores.

Every analysis is also saved to a small SQLite database, so there's a
History page showing everything you've analyzed before.

Author: (you!)
"""

import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from textblob import TextBlob

# 1. Create the Flask application object.
#    __name__ tells Flask where to look for templates/static files.
app = Flask(__name__)

DATABASE = "history.db"


def get_db_connection():
    """
    Opens a connection to the SQLite database file.
    sqlite3.Row lets us access columns by name (row["text"]) instead of
    only by numeric index (row[0]), which makes the template code cleaner.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Creates the 'entries' table if it doesn't already exist.
    This runs once, automatically, whenever the app starts up.
    """
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            polarity REAL NOT NULL,
            subjectivity REAL NOT NULL,
            sentiment TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_entry(result):
    """Inserts one analysis result into the database."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO entries (text, polarity, subjectivity, sentiment, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            result["text"],
            result["polarity"],
            result["subjectivity"],
            result["sentiment"],
            datetime.now().strftime("%d %b %Y, %I:%M %p"),
        ),
    )
    conn.commit()
    conn.close()


def analyze_sentiment(text):
    """
    Runs TextBlob sentiment analysis on a piece of text and returns
    a dictionary with everything the template needs to display.

    TextBlob gives us two numbers for any text:
      - polarity: how positive/negative the text is, from -1.0 (very
        negative) to +1.0 (very positive). 0 means neutral.
      - subjectivity: how much of the text is opinion vs. fact, from
        0.0 (very objective/factual) to 1.0 (very subjective/opinionated).
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    # Turn the raw polarity number into a human-friendly label.
    # We use a small buffer (0.05) around zero so that text with a tiny,
    # almost meaningless polarity still counts as "Neutral" rather than
    # flipping to Positive/Negative for a near-zero score like 0.01.
    if polarity > 0.05:
        sentiment_label = "Positive"
    elif polarity < -0.05:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Neutral"

    return {
        "text": text,
        "polarity": round(polarity, 3),
        "subjectivity": round(subjectivity, 3),
        "sentiment": sentiment_label,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Handles both showing the empty form (GET, when the page first loads)
    and processing a submitted form (POST, when the user clicks Analyze).
    """
    result = None
    error = None

    if request.method == "POST":
        user_text = request.form.get("user_text", "").strip()

        if not user_text:
            error = "Please enter some text before analyzing."
        else:
            result = analyze_sentiment(user_text)
            save_entry(result)  # store this analysis in the database

    # render_template looks inside the 'templates' folder automatically.
    return render_template("index.html", result=result, error=error)


@app.route("/history")
def history():
    """
    Shows every past analysis, most recent first.
    This reads straight from the database rather than from memory,
    so the history survives even if you restart the app.
    """
    conn = get_db_connection()
    entries = conn.execute(
        "SELECT * FROM entries ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("history.html", entries=entries)


@app.route("/history/delete/<int:entry_id>", methods=["POST"])
def delete_entry(entry_id):
    """Deletes a single history entry by its id, then returns to History."""
    conn = get_db_connection()
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("history"))


if __name__ == "__main__":
    init_db()  # make sure the table exists before the app starts serving
    # debug=True gives helpful error pages and auto-reloads the server
    # whenever you save a code change. Turn this off in production.
    app.run(debug=True)
