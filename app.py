from flask import Flask, request, jsonify
import requests
import sqlite3
import hashlib
import uuid
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# X Config (replace with yours)
X_CLIENT_ID = os.getenv('X_CLIENT_ID', 'cnQ0MUd1U3ROcWxyNDJ3c3VHR1c6MTpjaQ')  # Use env vars in Vercel
X_SECRET = os.getenv('X_SECRET', 'Hw0A4H4RVUp31sJ0Azjn4PJG8CQq8yqociNrd09mSd27IBA8c_')  # Needed for token exchange
DB_FILE = 'engagements_bot.db'  # If sharing DB with bot; for Vercel, use SQLite or switch to PostgreSQL
BOT_TOKEN = os.getenv('BOT_TOKEN', '8174658087:AAGcGiEnMiJPkjFXTxMAIrVTXhFLjo9RJdo')  # To notify via Telegram
TELEGRAM_BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# PKCE Helper (simplified; match your bot's logic)
def generate_pkce_verifier(state):
    # For demo: Hardcode or fetch from shared storage (e.g., Redis). In prod, use a shared DB/session.
    # Placeholder: Assume stored in DB or env; expand as needed.
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT code_verifier FROM pkce_temp WHERE state = ? AND expires_at > ?', 
                   (state, datetime.now()))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def create_user(telegram_id, x_user_id, x_username, referral_code):
    # Same as your bot's create_user; adapt if DB is shared
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (telegram_id, x_user_id, username, x_username, referral_code)
            VALUES (?, ?, ?, ?, ?)
        ''', (telegram_id, x_user_id, "VercelUser", x_username, referral_code))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

@app.route('/callback')
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error or not code or not state:
        return f"Error: {error or 'Missing params'}. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 400

    # Get verifier (adapt to your storage)
    code_verifier = generate_pkce_verifier(state)
    if not code_verifier:
        return "Expired verification. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 400

    # Exchange code for tokens
    token_data = {
        'client_id': X_CLIENT_ID,
        'client_secret': X_SECRET,  # Required for confidential clients
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': request.url_root.rstrip('/') + '/callback',  # Dynamic for Vercel
        'code_verifier': code_verifier
    }
    token_response = requests.post('https://api.x.com/2/oauth2/token', data=token_data)
    if token_response.status_code != 200:
        return f"Token failed: {token_response.text}. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 500

    tokens = token_response.json()
    access_token = tokens.get('access_token')

    # Fetch X user
    headers = {'Authorization': f'Bearer {access_token}'}
    user_response = requests.get('https://api.x.com/2/users/me', headers=headers)
    if user_response.status_code != 200:
        return f"User fetch failed. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 500

    x_user = user_response.json()['data']
    x_user_id = x_user['id']
    x_username = x_user['username']

    # Create user and notify
    telegram_id = int(state)
    referral_code = str(uuid.uuid4())[:8]
    if create_user(telegram_id, x_user_id, x_username, referral_code):
        # Notify via Telegram Bot API
        requests.post(TELEGRAM_BOT_URL, data={
            'chat_id': telegram_id,
            'text': f"Login successful! Connected as @{x_username}. Referral code: {referral_code}"
        })
        return f"Success! Connected @{x_username}. <a href='https://t.me/yapcgbot'>Back to Bot</a>"
    else:
        return "Account creation failed. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 500

if __name__ == '__main__':
    app.run()