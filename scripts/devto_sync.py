#!/usr/bin/env python3
"""
Dev.to Article Syndication Utility for Kirk Keel
Syncs Markdown articles from src/content/blog/ to Dev.to with canonical URLs pointing to eng.kcklayton.com.
"""

import os
import sys
import glob
import json
import re
import urllib.request
import urllib.error

CREDENTIALS_FILE = os.path.expanduser("~/.config/devto/credentials.json")
BLOG_DIR = os.path.expanduser("/home/kirk/projects/eng.kcklayton.com/src/content/blog")

def load_api_key():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f).get("api_key")
    return None

def parse_markdown(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    frontmatter = {}
    body = content

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        fm_text, body = match.group(1), match.group(2)
        for line in fm_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "tags":
                    # Parse tags array: ["tag1", "tag2"]
                    tags = re.findall(r'["\']([^"\']+)["\']', v)
                    if not tags:
                        tags = [t.strip() for t in v.strip("[]").split(",") if t.strip()]
                    frontmatter[k] = tags
                else:
                    frontmatter[k] = v

    slug = os.path.splitext(os.path.basename(filepath))[0]
    return frontmatter, body, slug

def sanitize_tags(tags):
    cleaned = []
    for t in tags:
        # Dev.to tags: alphanumeric only, max 4 tags
        clean_tag = re.sub(r"[^a-zA-Z0-9]", "", t).lower()
        if clean_tag and clean_tag not in cleaned:
            cleaned.append(clean_tag)
    # Default fallbacks if tags are missing
    if not cleaned:
        cleaned = ["engineering", "python", "ai"]
    return cleaned[:4]

def publish_article(filepath, published=True):
    api_key = load_api_key()
    if not api_key:
        print("Error: Missing Dev.to API key in ~/.config/devto/credentials.json")
        sys.exit(1)

    frontmatter, body, slug = parse_markdown(filepath)
    title = frontmatter.get("title", slug.replace("-", " ").title())
    description = frontmatter.get("description", "")
    tags = sanitize_tags(frontmatter.get("tags", []))
    canonical_url = f"https://eng.kcklayton.com/blog/{slug}/"

    # Prepend a polite notice about original publication
    full_body = (
        f"> *Originally published with interactive math formulas and diagrams at [eng.kcklayton.com]({canonical_url})*\n\n"
        + body
    )

    payload = {
        "article": {
            "title": title,
            "body_markdown": full_body,
            "published": published,
            "canonical_url": canonical_url,
            "description": description,
            "tags": tags
        }
    }

    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
            "User-Agent": "Astro-DevTo-Syncer/1.0"
        }
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"✓ Published: '{title}'")
            print(f"  Dev.to URL: {data.get('url')}")
            print(f"  Canonical URL: {canonical_url}")
            return data
    except urllib.error.HTTPError as e:
        print(f"Error publishing {slug} ({e.code}): {e.read().decode('utf-8')}")
        return None

def sync_all(published=True):
    files = glob.glob(os.path.join(BLOG_DIR, "*.md"))
    print(f"Found {len(files)} articles to syndicate to Dev.to...\n")
    for f in sorted(files):
        publish_article(f, published=published)
        print("-" * 50)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        sync_all(published=True)
    elif len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        publish_article(sys.argv[1], published=True)
    else:
        # Default: publish the first flagship article to test
        files = glob.glob(os.path.join(BLOG_DIR, "*.md"))
        if files:
            print("Publishing flagship article to Dev.to...")
            publish_article(files[0], published=True)
        else:
            print("No articles found in", BLOG_DIR)
