import os
import uuid
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

# Env vars from Vercel (set in dashboard)
X_CLIENT_ID = os.getenv('X_CLIENT_ID')
X_CLIENT_SECRET = os.getenv('X_CLIENT_SECRET')
BOT_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Stateless PKCE: For demo, we'll assume verifier passed via state or log; in prod, use Redis/Upstash
# For now, simulate success if code present (add real storage later)

@app.route('/callback', methods=['GET'])
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error or not code or not state:
        return f"Error: {error or 'Missing params'}. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 400

    # Simulate PKCE verifier (replace with real fetch from shared store)
    code_verifier = "demo_verifier_" + state  # Placeholder: In prod, get from Redis/DB

    # Exchange code for tokens (fast op)
    token_data = {
        'client_id': X_CLIENT_ID,
        'client_secret': X_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': request.url_root.rstrip('/') + 'callback',
        'code_verifier': code_verifier
    }
    try:
        token_response = requests.post('https://api.x.com/2/oauth2/token', data=token_data, timeout=5)
        if token_response.status_code != 200:
            print(f"Token error: {token_response.text}")  # Vercel logs
            return f"Token failed: {token_response.text[:100]}. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 500

        tokens = token_response.json()
        access_token = tokens.get('access_token')

        # Fetch X user (fast)
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get('https://api.x.com/2/users/me', headers=headers, timeout=5)
        if user_response.status_code != 200:
            print(f"User error: {user_response.text}")
            return f"User fetch failed. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 500

        x_user = user_response.json()['data']
        x_user_id = x_user['id']
        x_username = x_user['username']

        # Create user (simulate DB—no SQLite; in prod, use Vercel Postgres)
        telegram_id = int(state)
        referral_code = str(uuid.uuid4())[:8]
        # TODO: Insert to shared DB (e.g., Supabase/Postgres)
        print(f"Created user: TG {telegram_id}, X @{x_username}, Code {referral_code}")  # Log

        # Notify Telegram
        requests.post(TELEGRAM_BOT_URL, data={
            'chat_id': telegram_id,
            'text': f"Login successful! Connected as @{x_username}. Referral code: {referral_code}"
        }, timeout=5)

        return f"Success! Connected @{x_username}. <a href='https://t.me/yapcgbot'>Back to Bot</a>"

    except Exception as e:
        print(f"Callback error: {str(e)}")
        return f"Unexpected error. <a href='https://t.me/yapcgbot'>Back to Bot</a>", 500

# Vercel requires this for serverless
if __name__ == '__main__':
    app.run()