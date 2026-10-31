import os
import re
import subprocess
import logging
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

def turkish_upper(text: str) -> str:
    """
    Türkçe karakterleri (i -> İ, ı -> I, ğ -> Ğ, ü -> Ü, ş -> Ş, ö -> Ö, ç -> Ç)
    doğru şekilde büyük harfe dönüştürür.
    """
    tr_map = {
        'i': 'İ',
        'ı': 'I',
        'ğ': 'Ğ',
        'ü': 'Ü',
        'ş': 'Ş',
        'ö': 'Ö',
        'ç': 'Ç',
    }
    return "".join(tr_map.get(ch, ch.upper()) for ch in text)

def clean_subtitle_word(word: str) -> str:
    w = word.strip()
    # ASS formatındaki { } etiket karakterlerini temizle
    w = w.replace("{", "").replace("}", "")
    # Görünmez unicode karakterlerini ve variation selectorları temizle
    w = re.sub(r'[\u200B-\u200D\uFE0E\uFE0F\u202A-\u202E]', '', w)
    # Kelime ve noktalama arasına sıkışan yapay sayısal karakterleri temizle (örn. değil7, -> değil,)
    w = re.sub(r'([a-zA-ZçÇğĞıİöÖşŞüÜ])\d+([.,!?:;]*)', r'\1\2', w)
    return turkish_upper(w)

EMOJI_KEYWORDS = {
    # Teknoloji & Yapay Zeka
    "yapay": "🤖", "zeka": "🧠", "robot": "🤖", "ai": "🤖",
    "kod": "💻", "yazilim": "💻", "yazılım": "💻", "yazilimci": "💻", "yazılımcı": "💻",
    "bilgisayar": "🖥️", "program": "⚙️", "veri": "📊", "internet": "🌐", "sistem": "⚙️",
    # Başarı, Para & İş
    "para": "💰", "zengin": "💵", "dolar": "💵", "kazanc": "📈", "kazanç": "📈", "gelir": "💰",
    "milyon": "💎", "milyarder": "💎", "is": "💼", "iş": "💼", "sirket": "🏢", "şirket": "🏢",
    "ofis": "🏢", "patron": "💼", "basari": "🏆", "başarı": "🏆", "sampiyon": "🏆", "şampiyon": "🏆",
    "zafer": "🏆", "hedef": "🎯", "odak": "🎯", "kariyer": "🚀", "buyume": "🚀", "büyüme": "🚀",
    # Aksiyon, Enerji & Duygu
    "ates": "🔥", "ateş": "🔥", "bomba": "💣", "efsane": "🔥", "hizli": "⚡", "hızlı": "⚡",
    "roket": "🚀", "inanilmaz": "😱", "inanılmaz": "😱", "harika": "✨", "mukemmel": "✨", "mükemmel": "✨",
    "dikkat": "⚠️", "tehlike": "⚠️", "risk": "⚠️", "uyari": "🚨", "uyarı": "🚨", "acil": "🚨",
    "sir": "🤫", "sır": "🤫", "gizli": "🤫", "taktik": "🤫", "onemli": "❗", "önemli": "❗",
    "hata": "❌", "yanlis": "❌", "yanlış": "❌", "asla": "❌", "hayir": "❌", "hayır": "❌",
    "dogru": "✅", "doğru": "✅", "kesinlikle": "✅", "evet": "✅",
    "zaman": "⏳", "dakika": "⏱️", "saat": "⏰", "gun": "📅", "gün": "📅", "yil": "🗓️", "yıl": "🗓️",
    "fikir": "💡", "akil": "💡", "akıl": "💡", "dusunce": "💡", "düşünce": "💡",
    "dunya": "🌍", "dünya": "🌍", "kuresel": "🌍", "küresel": "🌍", "turkiye": "🇹🇷", "türkiye": "🇹🇷", "turk": "🇹🇷", "türk": "🇹🇷",
    "mulakat": "👔", "mülakat": "👔", "soru": "❓", "neden": "❓", "nasil": "❓", "nasıl": "❓", "cevap": "💡",
    "ogren": "📚", "öğren": "📚", "egitim": "📚", "eğitim": "📚", "kitap": "📖", "kurs": "📚",
    "kalp": "❤️", "sevgi": "❤️", "tutku": "❤️", "lider": "👑", "kral": "👑"
}

def get_word_emoji(word: str) -> str:
    clean = re.sub(r"[^a-zA-ZçÇğĞıİöÖşŞüÜ]", "", word).lower()
    return EMOJI_KEYWORDS.get(clean, "")

class VideoEditor:
    def __init__(self):
        self.output_dir = settings.OUTPUT_DIR
        self.temp_dir = settings.TEMP_DIR

    def generate_ass_subtitles(
        self,
        words: List[Dict[str, Any]],
        clip_start: float,
        clip_end: float,
        ass_path: str
    ) -> bool:
        """
        TikTok, Reels ve Shorts arayüz güvenli alanına (Safe-Zone) uygun,
        kelime düzeyinde animasyonlu vurgulu (karaoke) ve akıllı emojili ASS altyazı üretir.
        """
        clip_words = [
            w for w in words
            if w.get("start", 0) >= clip_start - 0.25 and w.get("end", 0) <= clip_end + 0.25
        ]

        if not clip_words:
            return False

        # Dil sürçmelerini, eksik telaffuzları ve kekelemeleri bağlamsal olarak düzelt (zaman damgaları korunur)
        from app.services.speech_corrector import SpeechSlipCorrector
        clip_words = SpeechSlipCorrector.correct_words(clip_words)

        # 1080x1920 çözünürlük için modern viral Shorts/Reels altyazı stili
        # MarginV: 560 (Alttaki başlık, profil ve butonların üstünde, güvenli alanda)
        # PrimaryColour: Beyaz, Highlight: Canlı Elektrik Sarısı (&H002BF7FF), Siyah Kontur: 5.0px, Gölge: 2.0px
        header = """[Script Info]
Title: ClipForge TikTok/Reels Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,62,&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,5.0,2.0,2,60,60,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def format_time(seconds: float) -> str:
            rel_sec = max(0.0, seconds - clip_start)
            hrs = int(rel_sec // 3600)
            mins = int((rel_sec % 3600) // 60)
            secs = int(rel_sec % 60)
            centisecs = int((rel_sec - int(rel_sec)) * 100)
            return f"{hrs:01d}:{mins:02d}:{secs:02d}.{centisecs:02d}"

        events = []
        chunks = []
        cur_chunk = []
        cur_len = 0
        for w in clip_words:
            w_len = len(w.get("word", ""))
            if cur_chunk and (len(cur_chunk) >= 3 or (cur_len + w_len) > 24):
                chunks.append(cur_chunk)
                cur_chunk = [w]
                cur_len = w_len
            else:
                cur_chunk.append(w)
                cur_len += w_len + 1
        if cur_chunk:
            chunks.append(cur_chunk)

        for chunk in chunks:
            if not chunk:
                continue

            # Parça içinde en fazla 1 adet anlamlı emoji bul
            emoji_idx = -1
            chunk_emoji = ""
            for idx, w in enumerate(chunk):
                em = get_word_emoji(w.get("word", ""))
                if em:
                    emoji_idx = idx
                    chunk_emoji = em
                    break

            for j, active_w in enumerate(chunk):
                start_t = format_time(active_w["start"])
                if j < len(chunk) - 1:
                    end_t = format_time(chunk[j + 1]["start"])
                else:
                    end_t = format_time(active_w["end"])

                line_parts = []
                for k, w in enumerate(chunk):
                    txt = clean_subtitle_word(w.get("word", ""))
                    if k == emoji_idx:
                        txt = f"{txt} {chunk_emoji}"
                    if k == j:
                        # Aktif okunan kelime: Canlı sarı/altın vurgu ve %8 pop efekti
                        line_parts.append(f"{{\\c&H002BF7FF&\\fscx108\\fscy108}}{txt}{{\\r}}")
                    else:
                        line_parts.append(txt)

                full_line = " ".join(line_parts)
                events.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{full_line}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events) + "\n")

        return True

    def cut_and_convert_vertical(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        clip_id: str,
        mode: str = "blur_background",
        words: List[Dict[str, Any]] = None
    ) -> str:
        """
        Videoyu tam kare olarak keser, 9:16 (1080x1920) dikey formata çevirir ve altyazı giydirir.
        Arka plan bulanıklığında 270x480 alt-ölçekleme optimizasyonu ile 5 kat daha hızlı render üretir.
        """
        import time
        ts = int(time.time())
        output_filename = f"clip_{clip_id}_{ts}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)

        # Kelime verisi varsa viral klip sınırlarını da tam cümle ve konuşma bitişine kenetle
        if words:
            try:
                from app.services.trailer_generator import TrailerGenerator
                snapped = TrailerGenerator.snap_scene_boundaries_to_sentences(
                    scenes=[{"start_time": start_time, "end_time": end_time}],
                    words=words,
                    total_duration=999999.0
                )
                if snapped:
                    start_time = snapped[0]["start_time"]
                    end_time = snapped[0]["end_time"]
            except Exception as se:
                logger.warning(f"Could not snap clip boundaries: {se}")

        if end_time <= start_time:
            end_time = start_time + 5.0
        duration = max(1.0, round(end_time - start_time, 2))

        # Altyazı hazırla
        ass_path = os.path.join(self.temp_dir, f"sub_{clip_id}_{ts}.ass")
        has_subtitles = False
        if words:
            try:
                has_subtitles = self.generate_ass_subtitles(words, start_time, end_time, ass_path)
            except Exception as e:
                logger.warning(f"Failed to generate ASS subtitles: {e}")
                has_subtitles = False

        # Ses patlamasını ve ani kesilmeyi önleyen yumuşak ses filtresi ve kusursuz dudak senkronizasyonu (Lip-Sync)
        fade_in_dur = min(0.08, duration / 4)
        fade_out_dur = min(0.18, duration / 4)
        fade_out_start = max(0.0, round(duration - fade_out_dur, 2))
        af_filter = f"aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS,afade=t=in:ss=0:d={fade_in_dur:.2f},afade=t=out:st={fade_out_start:.2f}:d={fade_out_dur:.2f}"

        # 9:16 Dikey Filtre Tasarımı (PTS sıfırlama ile ses-görüntü kayması önlenir)
        if mode == "crop_center":
            base_filter = "setpts=PTS-STARTPTS,scale=-1:1920,crop=1080:1920,setsar=1"
        else:
            # 16:9 yatay videoyu bulanık arka plan üzerine ortala (5x hızlı alt-ölçeklemeli blur)
            base_filter = (
                "[0:v]setpts=PTS-STARTPTS,scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=7:1,scale=1080:1920[bg];"
                "[0:v]setpts=PTS-STARTPTS,scale=1080:-2[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
            )

        filter_complex_str = base_filter
        if has_subtitles and os.path.exists(ass_path):
            escaped_ass = ass_path.replace(":", "\\:").replace("\\", "/").replace("'", "\\'")
            if mode == "crop_center":
                filter_complex_str = f"{base_filter},ass='{escaped_ass}'"
            else:
                filter_complex_str = f"{base_filter}[v];[v]ass='{escaped_ass}'"

        cmd = [
            "ffmpeg", "-y",
            "-threads", "0",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-avoid_negative_ts", "make_zero",
            "-filter_complex" if "[bg]" in filter_complex_str else "-vf", filter_complex_str,
            "-af", af_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-r", "30",
            "-c:a", "aac",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path
        ]

        logger.info(f"FFmpeg render starting for clip {clip_id} ({duration:.1f}s)")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if os.path.exists(ass_path):
            try:
                os.remove(ass_path)
            except Exception:
                pass

        if proc.returncode != 0:
            logger.warning(f"Complex render failed: {proc.stderr[:300]}. Attempting simple crop fallback...")
            fallback_cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-avoid_negative_ts", "make_zero",
                "-vf", "setpts=PTS-STARTPTS,scale=-1:1920,crop=1080:1920,setsar=1",
                "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-r", "30",
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                "-pix_fmt", "yuv420p",
                output_path
            ]
            subprocess.run(fallback_cmd, check=True)

        return {
            "video_filename": output_filename,
            "start_time": round(start_time, 2),
            "end_time": round(end_time, 2),
            "duration": round(duration, 2)
        }

    def extract_thumbnail(self, video_path: str, timestamp: float, output_path: str, width: int = 480) -> bool:
        """
        Extract a single frame from video at timestamp using FFmpeg fast seeking.
        Runs in ~20-30 milliseconds per frame.
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{max(0.0, timestamp):.2f}",
                "-i", video_path,
                "-vframes", "1",
                "-vf", f"scale={width}:-2",
                "-q:v", "3",
                output_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return res.returncode == 0 and os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error extracting thumbnail at {timestamp}s: {e}")
            return False
