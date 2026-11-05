#!/usr/bin/env python3
"""
Bluesky CLI utility for Kirk Keel (@kirk-keel.bsky.social)
Usage:
    python3 bluesky_cli.py post "Your post text here"
    python3 bluesky_cli.py profile
"""

import sys
import os
import re
import json
import datetime
import urllib.request
import urllib.error

CREDENTIALS_FILE = os.path.expanduser("~/.config/bluesky/credentials.json")

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    return {
        "handle": "kirk-keel.bsky.social",
        "app_password": "7tms-5hpv-enht-uouy"
    }

def save_credentials(creds):
    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f, indent=2)

def authenticate():
    creds = load_credentials()
    req = urllib.request.Request(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        data=json.dumps({"identifier": creds["handle"], "password": creds["app_password"]}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def build_facets(text):
    facets = []
    # Match URLs
    for m in re.finditer(r"https?://[^\s]+", text):
        start = len(text[:m.start()].encode("utf-8"))
        end = len(text[:m.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group(0)}]
        })
    # Match Tags
    for m in re.finditer(r"#([a-zA-Z0-9_]+)", text):
        start = len(text[:m.start()].encode("utf-8"))
        end = len(text[:m.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group(1)}]
        })
    return facets

def post(text):
    session = authenticate()
    jwt = session["accessJwt"]
    did = session["did"]

    facets = build_facets(text)
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    }
    if facets:
        record["facets"] = facets

    req = urllib.request.Request(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        data=json.dumps({
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": record
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {jwt}"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            rkey = res["uri"].split("/")[-1]
            print(f"✓ Post published successfully!")
            print(f"🌐 Link: https://bsky.app/profile/{session['handle']}/post/{rkey}")
            return res
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.read().decode('utf-8')}")
        sys.exit(1)

def show_profile():
    creds = load_credentials()
    url = f"https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor={creds['handle']}"
    with urllib.request.urlopen(url) as resp:
        profile = json.loads(resp.read().decode("utf-8"))
        print(f"\n--- Bluesky Profile: @{profile.get('handle')} ---")
        print(f"Name: {profile.get('displayName')}")
        print(f"Bio:\n{profile.get('description')}")
        print(f"Followers: {profile.get('followersCount')} | Follows: {profile.get('followsCount')} | Posts: {profile.get('postsCount')}")
        print(f"URL: https://bsky.app/profile/{profile.get('handle')}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bluesky_cli.py [post <text> | profile]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "post":
        if len(sys.argv) < 3:
            print("Error: Missing post content.")
            sys.exit(1)
        post(" ".join(sys.argv[2:]))
    elif cmd == "profile":
        show_profile()
    else:
        print(f"Unknown command: {cmd}")
