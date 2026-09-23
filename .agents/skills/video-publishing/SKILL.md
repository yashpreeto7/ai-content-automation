---
name: video-publishing
description: Social media publishing and distribution engine for YouTube Data API v3, YouTube Shorts, and Instagram Graph API Reels. Handles OAuth2 token refresh, video upload with chunked resume, thumbnail attachment, and metadata dispatch with strict human approval gates.
---

# Video Publishing & Social Distribution Skill

This skill provides comprehensive instructions, API protocols, and Python implementations for securely publishing long-form videos and 9:16 Shorts/Reels to YouTube and Instagram.

---

## 1. Core Publishing Principles

1. **Strict Human Approval Gate**:
   - Never publish automatically upon render completion.
   - The user must explicitly inspect the rendered preview, title, description, and tags before initiating publication.
2. **Credential Isolation**:
   - Credentials (client secrets, refresh tokens, access tokens) are stored in `.env` or secure OS keychain.
   - Never log authorization headers, access tokens, or client secrets in stdout or telemetry.
3. **Resilient Chunked Uploads**:
   - Long-form videos (several hundred megabytes) must use resumable chunked upload protocols to survive network timeouts.
4. **Hinglish Metadata Integrity**:
   - Maintain the authentic creator voice with Roman-Hinglish titles and descriptions.
   - Ensure proper hashtag casing (e.g., `#AIAgents`, `#SystemDesign`, `#HinglishTech`).

---

## 2. YouTube Data API v3 Integration

### Resumable Video Upload
YouTube videos over 5MB should always use the Google API Client Resumable Upload protocol.

```python
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload_youtube_video(
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "28", # Science & Technology
    privacy_status: str = "private", # Default to private for review
    is_short: bool = False
) -> str:
    creds = Credentials(
        token=os.getenv("YOUTUBE_ACCESS_TOKEN"),
        refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("YOUTUBE_CLIENT_ID"),
        client_secret=os.getenv("YOUTUBE_CLIENT_SECRET")
    )
    
    youtube = build("youtube", "v3", credentials=creds)
    
    # YouTube Shorts detection: #Shorts in title or description + vertical aspect ratio
    final_title = title if not is_short else f"{title} #Shorts"
    
    body = {
        "snippet": {
            "title": final_title[:100], # Max 100 chars
            "description": description[:5000],
            "tags": tags[:50],
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(
        file_path,
        mimetype="video/mp4",
        chunksize=1024 * 1024 * 5, # 5MB chunks
        resumable=True
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
            
    return response["id"]
```

---

## 3. Instagram Graph API (Reels)

### Two-Step Container Upload
Instagram Reels require creating a media container, polling for processing completion, and then publishing the container:

```python
import time
import requests

def publish_instagram_reel(
    video_url: str,
    caption: str,
    instagram_account_id: str,
    access_token: str
) -> str:
    base_url = "https://graph.facebook.com/v19.0"
    
    # Step 1: Create Reel Container
    container_payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token
    }
    res = requests.post(f"{base_url}/{instagram_account_id}/media", data=container_payload)
    res.raise_for_status()
    creation_id = res.json()["id"]
    
    # Step 2: Poll container status until FINISHED
    for _ in range(30):
        time.sleep(5)
        status_res = requests.get(
            f"{base_url}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token}
        ).json()
        
        status_code = status_res.get("status_code")
        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            raise RuntimeError(f"Instagram media processing failed: {status_res}")
            
    # Step 3: Publish Media
    pub_res = requests.post(
        f"{base_url}/{instagram_account_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token}
    )
    pub_res.raise_for_status()
    return pub_res.json()["id"]
```

---

## 4. Rate Limiting & Quotas

- **YouTube API**: Default quota is 10,000 units/day. Video upload consumes ~1,600 units. A creator can upload ~6 videos daily within free tier quota.
- **Instagram Graph API**: 200 calls/hour per user.
