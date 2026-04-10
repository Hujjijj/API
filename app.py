from flask import Flask, request, jsonify
import sqlite3
import secrets
import os
import time
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")

app = Flask(__name__)

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("keys.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT, api_key TEXT, created_at INTEGER)")
    conn.commit()
    conn.close()

init_db()

# ---------------- TELEGRAM SEND ----------------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

# ---------------- WEBHOOK ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "Send:\n1 → API KEY\n2 → API URL")

        elif text == "1":
            key = generate_key(chat_id)
            send_message(chat_id, f"🔑 API KEY:\n{key}")

        elif text == "2":
            key = generate_key(chat_id)
            send_message(chat_id, f"🌐 API URL:\n{BASE_URL}/api/{key}")

    return "ok"

# ---------------- KEY GENERATOR ----------------
def generate_key(user_id):
    conn = sqlite3.connect("keys.db")
    c = conn.cursor()

    c.execute("SELECT api_key, created_at FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()

    now = int(time.time())

    if row:
        key, created = row
        if now - created < 43200:
            conn.close()
            return key
        else:
            c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
            conn.commit()

    key = secrets.token_hex(16)

    c.execute("INSERT INTO users VALUES (?, ?, ?)", (user_id, key, now))
    conn.commit()
    conn.close()

    return key

# ---------------- API ----------------
@app.route("/")
def home():
    return "Working 🚀"

@app.route("/api/<key>")
def api(key):
    conn = sqlite3.connect("keys.db")
    c = conn.cursor()
    c.execute("SELECT created_at FROM users WHERE api_key=?", (key,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"status": "invalid"})

    if int(time.time()) - row[0] > 43200:
        return jsonify({"status": "expired"})

    return jsonify({"status": "success"})

# ---------------- SET WEBHOOK ----------------
@app.route("/setwebhook")
def setwebhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    requests.get(url, params={"url": BASE_URL + "/webhook"})
    return "Webhook set"

# ---------------- MAIN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
