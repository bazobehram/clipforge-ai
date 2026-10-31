import os
import re
import uuid
import logging
import subprocess
from typing import Dict, Any, Tuple
from app.config import settings

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        self.download_dir = settings.DOWNLOADS_DIR

    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        YouTube linklerini temizler, oynatma listesi ve takip parametrelerini ayıklar.
        Desteklenenler: watch?v=, youtu.be/, shorts/, m.youtube.com
        """
        url = url.strip()
        # Shorts linkini standart formata dönüştürme
        shorts_match = re.search(r'youtube\.com/shorts/([a-zA-Z0-9_-]+)', url)
        if shorts_match:
            video_id = shorts_match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"

        # youtu.be linki
        short_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
        if short_match:
            video_id = short_match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"

        # Parametreleri sadeleştirme (list= vb. kaldırılır)
        watch_match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', url)
        if watch_match:
            video_id = watch_match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
        return url

    def download_video(self, raw_url: str, job_id: str = "") -> Dict[str, Any]:
        """download() için geriye dönük uyumluluk takma adı (alias)"""
        if not job_id:
            job_id = str(uuid.uuid4())[:8]
        return self.download(raw_url, job_id)

    def download(self, raw_url: str, job_id: str) -> Dict[str, Any]:
        """
        YouTube videosunu indirir ve Whisper için 16kHz WAV formatında ses ayrıştırır.
        """
        clean_url = self.sanitize_url(raw_url)
        job_dir = os.path.join(self.download_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)

        video_template = os.path.join(job_dir, "original_video.%(ext)s")

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': video_template,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'nocheckcertificate': True,
            'geo_bypass': True,
        }

        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                video_title = info.get('title', 'YouTube Video')
                duration = info.get('duration', 0)
                thumbnail = info.get('thumbnail', '')
                video_path = os.path.join(job_dir, "original_video.mp4")

        except Exception as e:
            logger.error(f"yt-dlp download failed: {e}")
            raise RuntimeError(f"Video indirilemedi: {str(e)}")

        # 16kHz mono WAV çıkar (Whisper için ideal standart)
        audio_path = os.path.join(job_dir, "audio.wav")
        extract_audio_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            audio_path
        ]
        
        proc = subprocess.run(extract_audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            logger.warning(f"Audio extraction warning: {proc.stderr.decode('utf-8', errors='ignore')}")

        return {
            "title": video_title,
            "duration": float(duration),
            "thumbnail": thumbnail,
            "video_path": video_path,
            "audio_path": audio_path,
            "job_dir": job_dir
        }

    def cleanup_job_raw(self, job_dir: str):
        """Klipler oluşturulduktan sonra ham büyük video dosyasını silip disk tasarrufu sağlar."""
        try:
            raw_video = os.path.join(job_dir, "original_video.mp4")
            raw_audio = os.path.join(job_dir, "audio.wav")
            if os.path.exists(raw_video):
                os.remove(raw_video)
            if os.path.exists(raw_audio):
                os.remove(raw_audio)
        except Exception as e:
            logger.warning(f"Cleanup error in {job_dir}: {e}")
