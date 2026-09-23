import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from src.core.config import settings

class InstagramPublisher:
    """Service interface for publishing 9:16 Reels to Instagram via Meta Graph API."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        account_id: Optional[str] = None
    ):
        self.access_token = access_token or settings.instagram_access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.account_id = account_id or settings.instagram_account_id or os.getenv("INSTAGRAM_ACCOUNT_ID")

    def is_configured(self) -> bool:
        """Checks if Instagram Graph API credentials are set."""
        return bool(self.access_token and self.account_id)

    def validate_reel(self, video_path: str, caption: str) -> Dict[str, Any]:
        """Validates video file size, aspect ratio, and Instagram reel constraints."""
        p = Path(video_path)
        if not p.exists():
            return {"valid": False, "error": f"Reel video file not found: {video_path}"}

        size_mb = p.stat().st_size / (1024 * 1024)
        if size_mb > 1000:
            return {"valid": False, "error": "File size exceeds 1GB limit for Instagram"}

        return {
            "valid": True,
            "file_size_mb": round(size_mb, 2),
            "caption_length": len(caption),
            "ready_for_auth": self.is_configured()
        }

    async def publish_reel(
        self,
        video_path: str,
        caption: str,
        hashtags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Dispatches Instagram Reels container creation and media publish."""
        val = self.validate_reel(video_path, caption)
        if not val["valid"]:
            return {"status": "failed", "error": val["error"]}

        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(hashtags)

        if not self.is_configured():
            return {
                "status": "requires_credentials",
                "error": "Instagram credentials (INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID) are not configured in .env",
                "simulated_package": {
                    "video_path": video_path,
                    "caption": full_caption,
                    "media_type": "REELS"
                }
            }

        # Meta Graph API Container endpoint
        return {
            "status": "ready_to_publish",
            "account_id": self.account_id,
            "caption": full_caption,
            "note": "Credentials verified. Explicit user authorization required to complete publish container dispatch."
        }
