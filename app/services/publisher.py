import urllib.parse
from typing import Dict, Any, List, Optional

class SocialPublisher:
    """
    Mobil ve masaüstü cihazlarda tek tıkla paylaşım, pano kopyalama ve
    yerel mobil uygulama derin bağlantılarını (deep-links) yönetir.
    """

    @staticmethod
    def generate_share_urls(title: str, description: str, hashtags: List[str], youtube_url: Optional[str] = None) -> Dict[str, str]:
        tags_str = " ".join(hashtags) if hashtags else "#shorts #viral #reels #fyp"
        
        desc = description.strip() if description else ""
        if youtube_url and youtube_url not in desc:
            desc = f"{desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()

        full_caption = f"{title}\n\n{desc}\n\n{tags_str}".strip()

        # Twitter (X) ve Bluesky için linki ve hashtagleri her zaman koruyan akıllı metin (maks 270 karakter)
        link_part = f"🎬 {youtube_url}" if youtube_url else ""
        tags_part = tags_str.strip()
        
        # Öncelik: 1. YouTube Linki, 2. Hashtagler, 3. Başlık
        fixed_parts = [p for p in [link_part, tags_part] if p]
        fixed_len = sum(len(p) for p in fixed_parts) + (len(fixed_parts) * 2)
        max_title_len = max(35, 265 - fixed_len)
        
        post_title = title.strip()
        if len(post_title) > max_title_len:
            post_title = post_title[:max_title_len].rstrip() + "..."
            
        tweet_parts = [p for p in [post_title, link_part, tags_part] if p]
        tweet_text = "\n\n".join(tweet_parts).strip()

        encoded_full = urllib.parse.quote(full_caption)
        encoded_tweet = urllib.parse.quote(tweet_text)

        return {
            # Web Yükleme / Creator Center Bağlantıları
            "youtube_web": "https://studio.youtube.com/channel/UC/videos/upload?d=ud",
            "tiktok_web": "https://www.tiktok.com/creator-center/upload?from=webapp",
            "instagram_web": "https://www.instagram.com/create/style/",
            "twitter_web": f"https://twitter.com/intent/tweet?text={encoded_tweet}",
            "x_web": f"https://x.com/intent/post?text={encoded_tweet}",
            "bluesky_web": f"https://bsky.app/intent/compose?text={encoded_tweet}",

            # Mobil Uygulama Derin Bağlantıları (Deep-Links)
            "instagram_app": "instagram://camera",
            "tiktok_app": "snssdk1233://",
            "youtube_app": "vnd.youtube://",
            "twitter_app": f"twitter://post?message={encoded_tweet}",
            "x_app": f"twitter://post?message={encoded_tweet}",
            "bluesky_app": f"bluesky://intent/compose?text={encoded_tweet}",

            # Hazır Kopyalanabilir Metin
            "full_caption": full_caption,
            "tweet_text": tweet_text,
            "hashtags_only": tags_str,
            "title_only": title
        }
