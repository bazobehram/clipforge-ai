import os
import logging
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class AudioTranscriber:
    def __init__(self):
        self.whisper_type = settings.WHISPER_TYPE
        self.model_size = settings.WHISPER_MODEL_SIZE
        self.device = settings.WHISPER_DEVICE
        self.compute_type = settings.WHISPER_COMPUTE_TYPE
        self._local_model = None

    def _get_local_model(self):
        if self._local_model is None or getattr(self, "_loaded_model_size", None) != self.model_size:
            try:
                from faster_whisper import WhisperModel
                cpu_threads = min(8, os.cpu_count() or 4)
                logger.info(f"Loading faster-whisper model: {self.model_size} on {self.device} (cpu_threads={cpu_threads})")
                self._local_model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    cpu_threads=cpu_threads
                )
                self._loaded_model_size = self.model_size
            except Exception as e:
                logger.error(f"Error loading faster-whisper: {e}")
                raise e
        return self._local_model

    def _build_initial_prompt(self, video_title: str = "") -> str:
        """
        Whisper'ın Türkçe kelime dağarcığını, teknik jargonları ve noktalama
        kurallarını doğru tahmin etmesi için bağlamsal ön koşullama (contextual prompt) üretir.
        """
        import re
        prompt_parts = [
            "Merhaba. Bu video Türkçe konuşma içermektedir.",
            "Yazılım, teknoloji, yapay zeka, kodlama, kariyer, algoritma, sistem, mülakat ve güncel konular ele alınmaktadır.",
            "Düzgün Türkçe imla, büyük-küçük harf, noktalama işaretleri ve doğru hecelemeye dikkat edilmelidir."
        ]
        if video_title:
            clean_title = re.sub(r'[^\w\s\-,.]', '', video_title).strip()
            if clean_title:
                prompt_parts.append(f"Konu başlığı: {clean_title}.")
        return " ".join(prompt_parts)

    def transcribe(self, audio_path: str, video_title: str = "", progress_callback: Any = None) -> Dict[str, Any]:
        """
        Ses dosyasını kelime bazlı zaman damgalarıyla deşifre eder.
        Eğer bulut servisi (Groq/OpenAI) seçildiyse ve kota aşımı (429), sunucu hatası (500),
        bağlantı kopması veya limit sorunu yaşanırsa; iş akışı ASLA durmaz, anında ve
        sessizce yerel faster-whisper (large-v3-turbo) modeline fallback yapar.
        """
        use_cloud = (self.whisper_type in ("groq", "openai")) or (self.whisper_type == "auto" and bool(settings.GROQ_API_KEY))

        if use_cloud and (settings.GROQ_API_KEY or settings.LLM_API_KEY):
            try:
                logger.info(f"Attempting fast cloud transcription via {self.whisper_type}...")
                return self._transcribe_api(audio_path, video_title=video_title)
            except Exception as e:
                logger.warning(
                    f"Cloud transcription ({self.whisper_type}) encountered an issue ({e}). "
                    f"Failsafe triggered: smoothly falling back to local faster-whisper ({self.model_size})..."
                )
                return self._transcribe_local(audio_path, video_title=video_title, progress_callback=progress_callback)

        return self._transcribe_local(audio_path, video_title=video_title, progress_callback=progress_callback)

    def _transcribe_local(self, audio_path: str, video_title: str = "", progress_callback: Any = None) -> Dict[str, Any]:
        model = self._get_local_model()
        prompt = self._build_initial_prompt(video_title)
        logger.info(f"Starting Whisper ({self.model_size}) transcription with Turkish prompt context: {prompt[:70]}...")

        # large-v3-turbo, small ve base için beam_size=1 (greedy decoding) CPU'da 2.5-3x daha hızlı çalışır
        beam_size = 1 if self.model_size in ("large-v3-turbo", "turbo", "small", "base") else 2
        best_of = 1 if beam_size == 1 else 2

        segments_generator, info = model.transcribe(
            audio_path,
            language="tr",
            initial_prompt=prompt,
            beam_size=beam_size,
            best_of=best_of,
            word_timestamps=True,
            condition_on_previous_text=False,
            temperature=[0.0, 0.2, 0.4],
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=400,
                speech_pad_ms=250
            ),
            repetition_penalty=1.1,
            no_speech_threshold=0.6
        )

        segments = []
        full_transcript = []
        words_list = []

        total_audio_duration = getattr(info, "duration", None) or 0.0

        for seg in segments_generator:
            if progress_callback and total_audio_duration > 0:
                try:
                    progress_callback(seg.end, total_audio_duration, seg.text.strip())
                except Exception as cb_err:
                    logger.debug(f"Progress callback error: {cb_err}")

            seg_words = []
            if seg.words:
                for w in seg.words:
                    word_obj = {
                        "word": w.word.strip(),
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 2)
                    }
                    seg_words.append(word_obj)
                    words_list.append(word_obj)

            segment_data = {
                "id": seg.id,
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
                "words": seg_words
            }
            segments.append(segment_data)
            full_transcript.append(f"[{seg.start:.1f}s - {seg.end:.1f}s]: {seg.text.strip()}")

        from app.services.speech_corrector import SpeechSlipCorrector
        words_list = SpeechSlipCorrector.correct_words(words_list)

        # Segment kelimelerini ve metinlerini de dil sürçmesi motorundan geçir
        for seg in segments:
            if seg.get("words"):
                seg["words"] = SpeechSlipCorrector.correct_words(seg["words"])
                seg["text"] = " ".join(w["word"] for w in seg["words"])

        formatted_text = "\n".join(f"[{s['start']:.1f}s - {s['end']:.1f}s]: {s['text']}" for s in segments)

        return {
            "language": info.language,
            "duration": info.duration,
            "segments": segments,
            "words": words_list,
            "formatted_text": formatted_text
        }

    def _transcribe_api(self, audio_path: str, video_title: str = "") -> Dict[str, Any]:
        import httpx
        import subprocess

        api_key = settings.GROQ_API_KEY if (self.whisper_type in ("groq", "auto") and settings.GROQ_API_KEY) else settings.LLM_API_KEY
        if not api_key:
            raise ValueError("Cloud Whisper API key is missing (set GROQ_API_KEY or LLM_API_KEY).")

        base_url = "https://api.openai.com/v1" if self.whisper_type == "openai" else "https://api.groq.com/openai/v1"
        url = f"{base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}
        model_name = "whisper-1" if self.whisper_type == "openai" else "whisper-large-v3"
        prompt = self._build_initial_prompt(video_title)

        actual_file_to_send = audio_path
        temp_compressed_audio = None

        try:
            # Groq & OpenAI 25MB limit koruması: Eğer ses dosyası 24MB üzerindeyse ffmpeg ile hafifçe sıkıştır
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 24 * 1024 * 1024:
                temp_compressed_audio = audio_path.replace(".wav", "_api_comp.mp3")
                logger.info(f"Audio file is large ({os.path.getsize(audio_path)/(1024*1024):.1f}MB). Compressing for cloud API...")
                subprocess.run([
                    "ffmpeg", "-y", "-i", audio_path,
                    "-b:a", "64k", "-ar", "16000", "-ac", "1",
                    temp_compressed_audio
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(temp_compressed_audio) and os.path.getsize(temp_compressed_audio) < 24 * 1024 * 1024:
                    actual_file_to_send = temp_compressed_audio

            with open(actual_file_to_send, "rb") as f:
                filename = os.path.basename(actual_file_to_send)
                content_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
                files = {"file": (filename, f, content_type)}
                data = {
                    "model": model_name,
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": ["word", "segment"],
                    "language": "tr",
                    "prompt": prompt,
                    "temperature": "0.0"
                }
                with httpx.Client(timeout=180.0) as client:
                    res = client.post(url, headers=headers, files=files, data=data)
                    res.raise_for_status()
                    result = res.json()
        finally:
            if temp_compressed_audio and os.path.exists(temp_compressed_audio):
                try:
                    os.remove(temp_compressed_audio)
                except Exception:
                    pass

        words_list = []
        # 1. Doğrudan kelime düzeyinde zaman damgaları
        for w in result.get("words", []):
            words_list.append({
                "word": w.get("word", "").strip(),
                "start": round(float(w.get("start", 0)), 2),
                "end": round(float(w.get("end", 0)), 2),
                "probability": round(float(w.get("probability", 1.0)), 2)
            })

        segments = []
        full_transcript = []
        for s in result.get("segments", []):
            seg_words = []
            for sw in s.get("words", []):
                w_obj = {
                    "word": sw.get("word", "").strip(),
                    "start": round(float(sw.get("start", 0)), 2),
                    "end": round(float(sw.get("end", 0)), 2),
                    "probability": round(float(sw.get("probability", 1.0)), 2)
                }
                seg_words.append(w_obj)
                if not result.get("words"):
                    words_list.append(w_obj)

            segments.append({
                "id": s.get("id", 0),
                "start": round(float(s.get("start", 0)), 2),
                "end": round(float(s.get("end", 0)), 2),
                "text": s.get("text", "").strip(),
                "words": seg_words
            })
            full_transcript.append(f"[{s.get('start',0):.1f}s - {s.get('end',0):.1f}s]: {s.get('text','').strip()}")

        from app.services.speech_corrector import SpeechSlipCorrector
        words_list = SpeechSlipCorrector.correct_words(words_list)

        # Segment kelimelerini ve metinlerini de dil sürçmesi motorundan geçir
        for seg in segments:
            if seg.get("words"):
                seg["words"] = SpeechSlipCorrector.correct_words(seg["words"])
                seg["text"] = " ".join(w["word"] for w in seg["words"])

        formatted_text = "\n".join(f"[{s['start']:.1f}s - {s['end']:.1f}s]: {s['text']}" for s in segments)

        return {
            "language": result.get("language", "tr"),
            "duration": result.get("duration", 0),
            "segments": segments,
            "words": words_list,
            "formatted_text": formatted_text
        }
