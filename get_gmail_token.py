"""
One-time script to get a Gmail OAuth2 refresh token.

Run:
    pip install google-auth-oauthlib
    python get_gmail_token.py

A browser window will open — log in and grant access.
The script will print the three values you need for Render env vars.
"""

import json

import os

CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Build the credentials dict in the format google-auth-oauthlib expects
client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

if __name__ == "__main__":
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing dependency. Run:  pip install google-auth-oauthlib")
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("SUCCESS — add these to your Render env vars:")
    print("=" * 60)
    print(f"GMAIL_CLIENT_ID      = {creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET  = {creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN  = {creds.refresh_token}")
    print("=" * 60)
    print("\nAlso set:")
    print("GMAIL_SENDER_EMAIL    = <the Gmail account you just logged in with>")
    print("GMAIL_RECIPIENT_EMAIL = <where you want emails delivered>")
    print()
