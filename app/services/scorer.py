import json
import re
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class ContentScorer:
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.4, timeout: int = 120) -> str:
        """
        Pollinations / OpenAI uyumlu API çağrısı yapar.
        Cloudflare 403 engeline takılmamak için gerçek tarayıcı User-Agent kullanır.
        """
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": USER_AGENT
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            resp_data = json.loads(response.read().decode("utf-8"))
            content = resp_data["choices"][0]["message"]["content"].strip()

        # Markdown json bloklarını temizle
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    @classmethod
    def clean_title(cls, title: str, video_title: str = "", snippet: str = "") -> str:
        """Başlıktaki yarım kalmış ifadeleri, bağlaçları, tırnakları ve anlamsız kesilmeleri düzeltir."""
        if not title:
            title = ""
        # Tırnak işaretlerini temizle
        title = re.sub(r'^["\'“”„«]+|["\'“”„»]+$', '', title).strip()
        title = re.sub(r'[*_`#]', '', title).strip()
        title = re.sub(r'\.{2,}$', '', title).strip()
        # Sondaki anlamsız bağlaçları temizle
        title = re.sub(r'\s+\b(ve|veya|ile|da|de|ama|fakat|çünkü|ise|ki|bir|bu|için|gibi|ne|ne\s+dersin)\b$', '', title, flags=re.IGNORECASE).strip()
        # Baştaki bağlaçları temizle
        title = re.sub(r'^\b(ve|veya|ile|da|de|ama|fakat|çünkü|bu\s+yüzden|bence|aslında|yani)\b\s*', '', title, flags=re.IGNORECASE).strip()
        # Sondaki tire, pipe ve noktalama işaretlerini temizle
        title = re.sub(r'[-|–—,;:\s]+$', '', title).strip()

        # Eğer çok uzunsa ve YouTube formatında | veya - ile bölünmüşse ana kancayı al
        if len(title) > 65 and ('|' in title or ' - ' in title):
            parts = [p.strip() for p in re.split(r'\||\s+-\s+', title) if len(p.strip()) >= 6]
            if parts and len(parts[0]) <= 65:
                title = parts[0]

        if len(title) < 7 and snippet:
            t, _ = cls.build_nlp_title_and_description(video_title, snippet)
            title = t
        elif len(title) < 7:
            title = video_title or "Öne Çıkan Klip"

        if title:
            title = title[0].upper() + title[1:]
        return title

    @classmethod
    def clean_description(cls, text: str, video_title: str = "", snippet: str = "") -> str:
        """Açıklamadaki yapay kancaları temizler, yarım cümleleri düzeltir ve anlam bütünlüğü sağlar."""
        if not text:
            text = ""
        # Tırnak işaretlerini temizle
        text = re.sub(r'^["\'“”„«]+|["\'“”„»]+$', '', text).strip()
        patterns = [
            r'(?:videoyu\s+)?(?:beğen(?:ip|meyi|in)?|abone\s+ol(?:mayı|un)?|kaydet(?:ip|meyi|in)?|paylaş(?:ıp|mayı|ın)?)(?:[\s,]+(?:ve|ile)?\s*(?:kanala\s+)?(?:abone\s+ol(?:mayı|un)?|beğen(?:ip|meyi|in)?|kaydet(?:ip|meyi|in)?|takip\s+et(?:meyi|in)?|paylaş(?:ıp|mayı|ın)?))*\s*(?:unutmay[ıi]n|lütfen)?[\.!]*',
            r'daha\s+fazlas[ıi]\s+için\s+takip\s+(?:edin|kal[ıi]n|etmeyi\s+unutmay[ıi]n)[\.!]*',
            r'takipte\s+kal[ıi]n[\.!]*',
            r'(?:bizi\s+)?takip\s+et(?:meyi\s+unutmay[ıi]n|in)[\.!]*',
            r'(?:kanala\s+)?abone\s+ol(?:may[ıi]\s+unutmay[ıi]n|un)[\.!]*',
            r'kaydetmeyi\s+(?:ve\s+paylaşmayı\s+)?unutmay[ıi]n[\.!]*',
            r'beğenmeyi\s+(?:ve\s+kaydetmeyi\s+)?unutmay[ıi]n[\.!]*',
            r'düşüncelerinizi\s+(?:yorumlar(?:da)?\s+)?(?:paylaş[ıi]n|bildirin|yaz[ıi]n|belirtin)[\.!]*',
            r'fikirlerinizi\s+(?:yorumlar(?:da)?\s+)?(?:paylaş[ıi]n|bildirin|yaz[ıi]n|belirtin)[\.!]*',
            r'görüşlerinizi\s+(?:yorumlar(?:da)?\s+)?(?:paylaş[ıi]n|bildirin|yaz[ıi]n|belirtin)[\.!]*',
            r'yorum(?:lar(?:da)?)?\s+(?:yaz[ıi]n|belirtin|paylaş[ıi]n|bekliyoruz|buluşal[ıi]m)[\.!]*',
            r'siz\s+(?:bu\s+konuda\s+)?ne\s+düşünüyorsunuz\??',
            r'sizce\s+(?:de\s+)?öyle\s+mi\??',
            r'sen\s+ne\s+düşünüyorsun\??',
            r'peki\s+sizce\??',
            r'kat[ıi]l[ıi]yor\s+musunuz\??',
            r'videosundan\s+kesit[\.!]*',
            r'yapay\s+zeka\s+(?:ile|tarafından)\s+oluşturulan\s+akıllı\s+video\s+özeti[\.!]*',
            r'yapay\s+zeka\s+özeti[\.!]*',
            r'akıllı\s+video\s+özeti[\.!]*'
        ]
        cleaned = text
        for p in patterns:
            cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[,;:]\s*([,\.!?;])', r'\1', cleaned)
        cleaned = re.sub(r'\s+([,\.!?;])', r'\1', cleaned)
        cleaned = re.sub(r'\b(ve|veya|ile|da|de)\b[\.\s!]*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^\s*\b(ve|veya|ile|da|de)\b[\s,]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[,;:\s]+$', '', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        cleaned = re.sub(r'[\.!]{2,}', '.', cleaned).strip()

        # Eğer çok kısa kalmışsa veya anlamsızsa snippet'ten anlamlı cümle türet
        if len(cleaned) < 18 and snippet:
            _, d = cls.build_nlp_title_and_description(video_title, snippet)
            cleaned = d
        elif len(cleaned) < 18:
            cleaned = f"{video_title} konusundaki önemli ayrıntılar."

        # Cümle sonu noktalama kontrolü
        if cleaned and cleaned[-1] not in ('.', '!', '?'):
            cleaned += "."

        return cleaned

    @classmethod
    def build_nlp_title_and_description(cls, video_title: str, snippet: str):
        """Konuşma metninden gramer bütünlüğü tam, anlam kaybı olmayan başlık ve açıklama üretir."""
        clean_snippet = re.sub(r'\s+', ' ', snippet or '').strip()
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_snippet) if len(s.strip()) > 5]
        if not sentences and clean_snippet:
            sentences = [clean_snippet]

        title = ""
        # 1. Soru cümlesi var mı? (En yüksek tıklama getiren kanca)
        for s in sentences:
            if s.endswith('?') or re.search(r'\b(mı|mi|mu|mü|midir|mıdır|nasıl|neden|niçin|kim|nerede)\b', s, re.IGNORECASE):
                q = re.sub(r'^(ama|fakat|ve|veya|oysa|çünkü|peki|yani|yoksa|aslında|şimdi|bence|bu\s+yüzden)\s+', '', s, flags=re.IGNORECASE).strip()
                words = q.split()
                if len(words) <= 13 and len(q) <= 85:
                    title = q if q.endswith('?') else (q + '?' if re.search(r'\b(mı|mi|mu|mü|midir|mıdır)\b', q, re.IGNORECASE) else q)
                elif len(words) > 13:
                    parts = [p.strip() for p in re.split(r'[,;]', q) if len(p.strip()) > 10]
                    for p in parts:
                        if re.search(r'\b(mı|mi|mu|mü|nasıl|neden)\b', p, re.IGNORECASE) and len(p.split()) <= 12:
                            title = p if p.endswith('?') else f"{p}?"
                            break
                if title:
                    break

        if not title:
            first = sentences[0] if sentences else video_title
            first = re.sub(r'^(ama|fakat|ve|veya|oysa|çünkü|bence|aslında|yani|örneğin|mesela|bu\s+hatta)\s+', '', first, flags=re.IGNORECASE).strip()
            first_clean = re.sub(r'[.!?]+$', '', first).strip()
            words = first_clean.split()
            if len(words) <= 10 and len(first_clean) >= 12:
                title = first_clean
            elif len(words) > 10:
                selected = []
                for w in words[:10]:
                    if w.lower() in ('ve', 'veya', 'ile', 'ama', 'fakat', 'de', 'da', 'ki', 'ise') and len(selected) >= 4:
                        break
                    selected.append(w)
                title = " ".join(selected)

        if len(title.strip()) < 8:
            title = f"{video_title}: Önemli Noktalar"

        title = title.strip()
        if title:
            title = title[0].upper() + title[1:]
        title = re.sub(r'[,;:\s]+$', '', title).strip()
        title = re.sub(r'\.{2,}$', '', title).strip()

        # 2. AÇIKLAMA TÜRETME (Yüklemi tam, edebi ve profesyonel Türkçe cümle)
        if sentences:
            first_s = sentences[0].strip()
            if not first_s.endswith(('.', '!', '?')):
                first_s += '.'
            
            if len(sentences) > 1 and len(first_s) < 85:
                second_s = sentences[1].strip()
                if not second_s.endswith(('.', '!', '?')):
                    second_s += '.'
                desc = f"{first_s} {second_s}"
            else:
                desc = first_s
        else:
            desc = f"{video_title} konusunun en dikkat çeken detayları."

        return title, desc

    @staticmethod
    def is_overlapping_or_duplicate(
        cand: Dict[str, Any],
        candidates_list: List[Dict[str, Any]],
        max_overlap_ratio: float = 0.35
    ) -> bool:
        """
        Aday klibin listedeki herhangi bir adayla belirgin şekilde çakışıp
        çakışmadığını veya mükerrer olup olmadığını kontrol eder.
        """
        if not candidates_list:
            return False

        try:
            c_st = float(cand.get("start_time", 0.0))
            c_et = float(cand.get("end_time", 0.0))
        except (ValueError, TypeError):
            return False

        c_dur = max(1.0, c_et - c_st)

        for ex in candidates_list:
            try:
                e_st = float(ex.get("start_time", 0.0))
                e_et = float(ex.get("end_time", 0.0))
            except (ValueError, TypeError):
                continue

            e_dur = max(1.0, e_et - e_st)

            # Başlangıç ve bitiş zamanları çok yakınsa doğrudan mükerrer
            if abs(c_st - e_st) < 10.0 and abs(c_et - e_et) < 10.0:
                return True

            # Zaman aralığı kesişim oranı kontrolü
            overlap = max(0.0, min(c_et, e_et) - max(c_st, e_st))
            if (overlap / min(c_dur, e_dur)) > max_overlap_ratio:
                return True

        return False

    @staticmethod
    def get_transcript_window(
        formatted_transcript: str,
        offset: int = 0,
        existing_candidates: Optional[List[Dict[str, Any]]] = None,
        max_chars: int = 14000
    ) -> str:
        """
        Transkriptten analiz için uygun pencereyi seçer.
        Offset veya mevcut adaylar varsa, videonun daha önce taranmamış
        veya devamındaki bölümlerine odaklanarak yeni kesitlerin keşfedilmesini sağlar.
        """
        if not formatted_transcript or len(formatted_transcript) <= max_chars:
            return formatted_transcript

        # Mevcut adayların en büyük bitiş zamanını bul
        max_end_time = 0.0
        if existing_candidates:
            for c in existing_candidates:
                try:
                    et = float(c.get("end_time", 0.0))
                    if et > max_end_time:
                        max_end_time = et
                except (ValueError, TypeError):
                    continue

        lines = formatted_transcript.splitlines()

        # Eğer mevcut adayların kapsadığı bir süre varsa, o sürenin hemen öncesinden başlat
        start_line_idx = 0
        if max_end_time > 30.0:
            target_start = max(0.0, max_end_time - 10.0)
            for idx, line in enumerate(lines):
                m = re.search(r'\[(\d+\.?\d*)s\s*-', line)
                if m and float(m.group(1)) >= target_start:
                    start_line_idx = max(0, idx - 1)
                    break

        # Eğer start_line_idx sona çok yakınsa (kalan metin 2500 karakterden azsa),
        # offsete göre transkript içinde dengeli bir pencere belirle
        candidate_window_lines = lines[start_line_idx:]
        candidate_text = "\n".join(candidate_window_lines)
        if len(candidate_text) < 2500 and start_line_idx > 0:
            step_stride = max(1, len(lines) // max(offset + 1, 2))
            start_line_idx = (offset * step_stride) % max(1, len(lines) - 20)
            candidate_window_lines = lines[start_line_idx:]

        # max_chars sınırına kadar satırları ekle
        collected_lines = []
        char_count = 0
        for l in candidate_window_lines:
            if char_count + len(l) + 1 > max_chars and collected_lines:
                break
            collected_lines.append(l)
            char_count += len(l) + 1

        return "\n".join(collected_lines)

    def analyze_and_score(
        self,
        formatted_transcript: str,
        video_title: str,
        video_duration: float,
        max_clips: int = 10,
        offset: int = 0,
        youtube_url: str = "",
        existing_candidates: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Transkripti inceleyerek en yüksek kanca (hook), akış ve etkileşim puanına
        sahip 30-90 saniyelik en iyi aday parçaları seçer ve metadata üretir.
        Mevcut adayları dikkate alarak mükerrer veya çakışan kesit üretilmesini engeller.
        """
        existing_candidates = existing_candidates or []
        llm_request_count = min(max(max_clips, 5), 10)

        # Transkript penceresini mevcut adaylara / offsete göre dinamik seç
        transcript_window = self.get_transcript_window(
            formatted_transcript=formatted_transcript,
            offset=offset,
            existing_candidates=existing_candidates,
            max_chars=14000
        )

        existing_prompt_section = ""
        if existing_candidates:
            lines_summary = []
            for ec in existing_candidates[-15:]:
                st = round(float(ec.get("start_time", 0.0)), 1)
                et = round(float(ec.get("end_time", 0.0)), 1)
                t = ec.get("title", "")
                lines_summary.append(f"- [{st}s - {et}s]: {t}")
            existing_summary_text = "\n".join(lines_summary)
            existing_prompt_section = f"""\n\nÖNEMLİ KURAL - DAHA ÖNCE ÇIKARILAN KESİTLER:
Bu videodan daha önce aşağıdaki zaman aralıkları ve konular ZATEN klip olarak çıkarılmıştır:
{existing_summary_text}

ZORUNLU DİREKTİF:
1. Yukarıdaki zaman aralıklarıyla ÇAKIŞAN (aynı veya benzer dakikalardaki) kesitler KESİNLİKLE ÜRETME! En az 15 saniye fark olmalıdır.
2. Aşağıdaki transkript penceresinde yer alan, videonun henüz kullanılmamış YEPYENİ bölümlerinden ve farklı konularından tam {llm_request_count} adet yeni bağımsız klip çıkar.
3. Konular ve başlıklar önceki kesitlerden tamamen farklı olmalıdır.\n"""

        system_prompt = f"""Sen dünyanın en iyi kısa formatlı video (TikTok, Instagram Reels, YouTube Shorts) yapımcısı ve viral içerik uzmanısın.
Görevin: Sana zaman damgalarıyla verilen video deşifresini incelemek, videonun farklı noktalarından izleyicinin dikkatini ilk 3 saniyede yakalayan (hook), bağımsız olarak anlam ifade eden ve en çok viral olma potansiyeline sahip tam {llm_request_count} adet bağımsız kesit bulmaktır.

Kurallar:
1. Kesinlikle tam {llm_request_count} adet birbirinden ve daha önce çıkarılan kesitlerden tamamen farklı yeni klip önerisi oluştur.
2. Her klip için video içeriğine özel, birbirinden FARKLI ve ilgi çekici başlıklar üret. Asla jenerik veya birbirinin kopyası başlık yazma!
3. SÜRE & DOĞAL BAĞLAM KURALI: Her klip 30 ile 90 saniye arasında olmalıdır. Klipleri yapay olarak 25-30 saniyeye sıkıştırma! Konuşmacının anlattığı konunun, argümanın, örneğin veya eleştirinin izleyici tarafından tam olarak anlaşılabilmesi için ne kadar süre gerekiyorsa o kadar süre ver. Eğer bir düşünce 65-85 saniyede tamamlanıyorsa, asla yarıda kesme; tam hikaye yayını (story arc) kapsayacak şekilde süreyi 30-90s aralığında belirle.
4. Başlangıç zamanı güçlü bir soru, çarpıcı bir iddia, hikaye başlangıcı veya şaşırtıcı bir bilgi ile başlamalıdır.
5. Bitiş zamanı cümlenin ortasında veya havada kalmamalı, konuşmacının ana fikrini tamamladığı anlamlı bir noktada bitmelidir.
6. ELEŞTİRİ & DIŞ KAYNAK VİDEO KURALI: Eğer kesit başka bir videodan/röportajdan bir kesit içeriyorsa, sadece o dış kesiti tek başına alıp bırakma; ana anlatıcının o kesiti sunduğu giriş ile arkasından yaptığı eleştiri, yorum veya cevabı da mutlaka klibe dahil et.
7. Puanlama:
   - "score": 75-98 arasında tam sayı.
   - "hook_score", "flow_score", "value_score": 7.0 ile 9.9 arasında tek ondalıklı sayı (örn: 9.3).
8. Her klip için:
   - "title": O kesite ÖZGÜ, kesinlikle 4 ila 9 kelimeden oluşan, merak uyandırıcı, tam bir anlam ifade eden Türkçe başlık. Asla yarım kalmış ifadeler ("ve...", "ise...", "için...") veya konuşma metninin rastgele kesilmiş halini YAZMA!
   - "description": O kesitte anlatılan konunun özünü net, edebi ve akıcı 1-2 cümleyle özetle. Cümlelerin yüklemi ve anlamı tam olmalı, asla cümle ortasında kesilmemelidir. KESİNLİKLE "yorum yazın", "düşüncelerinizi belirtin", "beğenin", "takip edin", "kaydetmeyi unutmayın" gibi yapay kancalar YAZMA!
   - "hashtags": KESİNLİKLE videoda konuşulan SPESİFİK KONUYA ÖZEL, en iddialı ve izleyici çeken 6-8 etiket dizisi. En az 4-5 tanesi doğrudan konuşulan konu/kavramla ilgili olmalıdır.
   - "summary": Klibin neden viral olacağını anlatan 1 cümlelik gerekçe.
   - "transcript_snippet": Bu kesitte konuşulan ilk 1-2 cümle.

Çıktıyı KESİNLİKLE sadece aşağıdaki JSON formatında ver, hiçbir ek açıklama veya markdown metni yazma:
{{
  "clips": [
    {{
      "start_time": 45.0,
      "end_time": 95.0,
      "score": 94,
      "hook_score": 9.5,
      "flow_score": 9.0,
      "value_score": 9.7,
      "title": "...",
      "description": "...",
      "hashtags": ["#konuEtiketi1", "#konuEtiketi2", "#konuEtiketi3", "#kesfet", "#reels"],
      "summary": "...",
      "transcript_snippet": "..."
    }}
  ]
}}
"""

        user_prompt = f"""Video Başlığı: {video_title}
Toplam Süre: {video_duration} saniye
İstenen En İyi Aday Klip Sayısı: {llm_request_count}{existing_prompt_section}

Zaman Damgalı Transkript:
{transcript_window}
"""

        valid_clips = []
        try:
            content = self._call_llm(system_prompt, user_prompt, temperature=0.55, timeout=70)
            data = json.loads(content)
            clips = data.get("clips", [])
            for c in clips:
                c["score"] = round(float(c.get("score", 85)), 1)
                c["hook_score"] = round(float(c.get("hook_score", 8.5)), 1)
                c["flow_score"] = round(float(c.get("flow_score", 8.0)), 1)
                c["value_score"] = round(float(c.get("value_score", 8.0)), 1)
                c["start_time"] = round(float(c.get("start_time", 0.0)), 1)
                c["end_time"] = round(float(c.get("end_time", 30.0)), 1)
                c["duration"] = round(c["end_time"] - c["start_time"], 1)

                snippet = c.get("transcript_snippet", "")
                c["title"] = self.clean_title(c.get("title", ""), video_title=video_title, snippet=snippet)

                desc = self.clean_description(c.get("description", ""), video_title=video_title, snippet=snippet)
                if youtube_url and youtube_url not in desc:
                    desc = f"{desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()
                c["description"] = desc

                if not c.get("hashtags"):
                    c["hashtags"] = self.generate_smart_hashtags(video_title, snippet)

                # Çakışma ve mükerrerlik filtresi (hem mevcut adaylara hem bu partideki diğerlerine karşı)
                if existing_candidates and self.is_overlapping_or_duplicate(c, existing_candidates):
                    logger.info(f"Duplicate candidate filtered against existing: [{c.get('start_time')}s - {c.get('end_time')}s] '{c.get('title')}'")
                    continue
                if self.is_overlapping_or_duplicate(c, valid_clips):
                    continue

                valid_clips.append(c)

            valid_clips.sort(key=lambda x: x.get("score", 0), reverse=True)
            if len(valid_clips) >= max_clips:
                return valid_clips[:max_clips]
            elif valid_clips:
                needed = max_clips - len(valid_clips)
                extra = self._fallback_clips(
                    video_duration=video_duration,
                    count=needed,
                    video_title=video_title,
                    formatted_transcript=formatted_transcript,
                    offset=offset + len(valid_clips),
                    youtube_url=youtube_url,
                    existing_candidates=existing_candidates + valid_clips
                )
                return valid_clips + extra

        except Exception as e:
            logger.warning(f"LLM API call error in analyze_and_score: {e}. Generating fallback clips...")

        needed_total = max_clips - len(valid_clips)
        extra = self._fallback_clips(
            video_duration=video_duration,
            count=needed_total,
            video_title=video_title,
            formatted_transcript=formatted_transcript,
            offset=offset + len(valid_clips),
            youtube_url=youtube_url,
            existing_candidates=existing_candidates + valid_clips
        )
        return valid_clips + extra

    def search_topic_clips(
        self,
        query: str,
        formatted_transcript: str,
        video_title: str,
        video_duration: float,
        youtube_url: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcının videoda arattığı kelime, cümle veya konuya göre
        en uygun 1-4 kesiti bulur ve viral klip adayı üretir.
        """
        system_prompt = """Sen uzman bir video araştırmacısı ve viral kurgu editörüsün.
Kullanıcı sana bir video transkripti ve aradığı bir konuyu/cümleyi/anahtar kelimeyi verecek.
Görevin:
1. Transkriptte kullanıcının aradığı konunun veya cümlenin en etkili ve net şekilde konuşulduğu 1 ile 3 adet bağımsız kesit bulmak.
2. Her kesit 30 ile 90 saniye arasında olmalıdır. Konuşmacının aranan konuyu baştan sona tam olarak anlattığı doğal süreyi kapsasın, yapay olarak kısa kesme.
3. Konunun başlangıcı ve bitişi mantıklı bir anlam bütünlüğü oluşturmalıdır.
4. Bu kesit için yüksek tıklama getirecek özel bir başlık (title), açıklama (description), etiketler (hashtags) ve transcript_snippet üret.
5. Açıklama (description) kısmında KESİNLİKLE "yorum yapın", "beğenin", "düşüncelerinizi paylaşın", "takip edin", "kaydetmeyi unutmayın" gibi yapay kancalar KULLANMA! Sadece aranan konunun kesitte nasıl ele alındığını net ve kaliteli 1-2 cümleyle özetle.

Çıktıyı KESİNLİKLE sadece aşağıdaki JSON formatında ver:
{
  "clips": [
    {
      "start_time": 45.0,
      "end_time": 90.0,
      "score": 93,
      "hook_score": 9.4,
      "flow_score": 9.0,
      "value_score": 9.5,
      "title": "...",
      "description": "...",
      "hashtags": ["#shorts", "#viral", "#konu"],
      "summary": "Aranan konu bu kesitte detaylı ve çarpıcı olarak işleniyor.",
      "transcript_snippet": "..."
    }
  ]
}
"""
        user_prompt = f"""Video Başlığı: {video_title}
Kullanıcının Aradığı Konu / Cümle: {query}

Zaman Damgalı Transkript:
{formatted_transcript[:14000]}
"""
        try:
            content = self._call_llm(system_prompt, user_prompt, temperature=0.3, timeout=60)
            data = json.loads(content)
            clips = data.get("clips", [])
            for c in clips:
                c["score"] = round(float(c.get("score", 90)), 1)
                c["hook_score"] = round(float(c.get("hook_score", 9.0)), 1)
                c["flow_score"] = round(float(c.get("flow_score", 8.5)), 1)
                c["value_score"] = round(float(c.get("value_score", 9.0)), 1)
                c["start_time"] = round(float(c.get("start_time", 0.0)), 1)
                c["end_time"] = round(float(c.get("end_time", 30.0)), 1)
                c["duration"] = round(c["end_time"] - c["start_time"], 1)

                title = self.clean_title(c.get("title", ""), video_title=video_title, snippet=c.get("transcript_snippet", ""))
                desc = self.clean_description(c.get("description", ""), video_title=video_title, snippet=c.get("transcript_snippet", ""))
                if youtube_url and youtube_url not in desc:
                    desc = f"{desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()
                c["title"] = title
                c["description"] = desc

            if clips:
                return clips
        except Exception as e:
            logger.warning(f"Topic search LLM error: {e}. Trying text scan...")

        # Metin tarama (Text Scan Fallback)
        return self._search_transcript_text(query, formatted_transcript, video_title, video_duration, youtube_url=youtube_url)

    def _search_transcript_text(
        self,
        query: str,
        formatted_transcript: str,
        video_title: str,
        video_duration: float,
        youtube_url: str = ""
    ) -> List[Dict[str, Any]]:
        """Transkript satırlarında anahtar kelime eşleşmesi arar."""
        lines = formatted_transcript.splitlines()
        q_lower = query.lower()
        matched_clips = []

        for line in lines:
            if q_lower in line.lower():
                # [12.5s - 15.0s]: metin
                match = re.search(r'\[(\d+\.?\d*)s\s*-\s*(\d+\.?\d*)s\]:\s*(.*)', line)
                if match:
                    t_start = max(0.0, float(match.group(1)) - 5.0)
                    t_end = min(video_duration, t_start + 40.0)
                    text_snippet = match.group(3).strip()

                    desc = f"{video_title} videosunda '{query}' konusunun ele alındığı kesit."
                    if youtube_url and youtube_url not in desc:
                        desc = f"{desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()

                    matched_clips.append({
                        "start_time": round(t_start, 1),
                        "end_time": round(t_end, 1),
                        "duration": round(t_end - t_start, 1),
                        "score": 92.0,
                        "hook_score": 9.3,
                        "flow_score": 8.8,
                        "value_score": 9.2,
                        "title": f"🔍 {query.capitalize()}: {video_title}",
                        "description": desc,
                        "hashtags": self.generate_smart_hashtags(f"{query} {video_title}", text_snippet),
                        "summary": f"'{query}' konusu tam olarak bu zaman damgasında geçmektedir.",
                        "transcript_snippet": text_snippet
                    })
                    if len(matched_clips) >= 3:
                        break

        return matched_clips

    def regenerate_clip_metadata(
        self,
        transcript_snippet: str,
        video_title: str,
        current_title: Optional[str] = None,
        youtube_url: str = ""
    ) -> Dict[str, Any]:
        """
        Kullanıcı başlığı veya açıklamayı beğenmediğinde yapay zekadan
        daha çarpıcı, merak uyandırıcı yeni alternatifler üretmesini ister.
        """
        system_prompt = """Sen Instagram Reels, TikTok ve YouTube Shorts için profesyonel video içerik yazarısın.
Kullanıcı sana videodaki bir kesitin transkriptini ve mevcut başlığını verecek.
Senin görevin: Merak uyandırıcı 1 adet yeni Türkçe başlık (title), 1 adet kaliteli açıklama (description) ve içeriğe %100 odaklı en iddialı 6-8 etiket (hashtags) üretmektir.
DİKKAT:
1. Başlık (title): Kesinlikle yarım kalmış cümle, "..." veya bağlaçla biten ifade olmamalıdır! Tam ve vurucu bir soru veya ifade olmalıdır (4-8 kelime).
2. Açıklama (description): Kesinlikle yüklemi olan tam 1-2 edebi/profesyonel cümle olmalıdır. KESİNLİKLE "yorum yazın", "düşüncelerinizi bildirin", "beğenin", "takip edin" gibi yapay kancalar YAZMA!
3. Etiketler (hashtags): KESİNLİKLE konuşulan spesifik konunun anahtar kavramlarını içermelidir (örn: yazılım ise #yazilim, #kodlama, #yapayzeka; para ise #finans, #yatirim; psikoloji ise #psikoloji, #kisiselgelisim). Sadece 1-2 tanesi #kesfet, #reels gibi genel etiket olabilir.

Çıktıyı SADECE aşağıdaki JSON formatında ver:
{
  "title": "Çarpıcı Yeni Başlık",
  "description": "Dikkat çekici ve anlam bütünlüğü tam yeni açıklama.",
  "hashtags": ["#konuEtiketi1", "#konuEtiketi2", "#konuEtiketi3", "#kesfet", "#reels"],
  "summary": "Neden bu başlık daha yüksek izlenme getirecek?"
}
"""
        user_prompt = f"""Ana Video: {video_title}
Mevcut Başlık: {current_title or 'Yok'}
Klipteki Konuşma / İçerik: {transcript_snippet}
"""
        try:
            content = self._call_llm(system_prompt, user_prompt, temperature=0.7, timeout=60)
            res = json.loads(content)
            title = self.clean_title(res.get("title", ""), video_title=video_title, snippet=transcript_snippet)
            desc = self.clean_description(res.get("description", ""), video_title=video_title, snippet=transcript_snippet)
            if youtube_url and youtube_url not in desc:
                desc = f"{desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()
            res["title"] = title
            res["description"] = desc
            if not res.get("hashtags"):
                res["hashtags"] = self.generate_smart_hashtags(video_title, transcript_snippet)
            return res
        except Exception as e:
            logger.warning(f"Regenerate meta error: {e}")
            fallback_title, fallback_desc = self.build_nlp_title_and_description(video_title, transcript_snippet)
            fallback_title = self.clean_title(fallback_title, video_title=video_title, snippet=transcript_snippet)
            fallback_desc = self.clean_description(fallback_desc, video_title=video_title, snippet=transcript_snippet)
            if youtube_url and youtube_url not in fallback_desc:
                fallback_desc = f"{fallback_desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()
            return {
                "title": fallback_title,
                "description": fallback_desc,
                "hashtags": self.generate_smart_hashtags(video_title, transcript_snippet),
                "summary": "Transkript içeriğinden türetilen alternatif başlık ve açıklama."
            }

    @staticmethod
    def generate_smart_hashtags(title: str, snippet: str = "") -> List[str]:
        """Video başlığı ve transkriptten konuya özel, iddialı Türkçe hashtag'ler türetir."""
        combined = f"{title} {snippet}".lower()
        tr_stop = {
            "ve", "ile", "bir", "bu", "icin", "için", "gibi", "daha", "kadar", "olan",
            "nasil", "nasıl", "neden", "diye", "ben", "sen", "biz", "siz", "onlar",
            "sey", "şey", "cok", "çok", "bunu", "sunu", "şunu", "ama", "fakat", "cunku", "çünkü",
            "boyle", "böyle", "oyle", "öyle", "her", "hic", "hiç", "var", "yok", "ise", "ya", "da",
            "de", "ne", "mi", "mu", "en", "ki", "sonra", "once", "önce", "kendi",
            "bana", "sana", "bize", "size", "video", "bölüm", "kesit", "shorts", "reels",
            "kurduk", "yaptik", "yaptık", "ettik", "aldik", "aldık", "geldi", "gitti",
            "tüm", "tam", "az", "fazla", "ilk", "son", "yeni", "eski"
        }

        topic_tags = []
        seen = set()

        niche_mappings = {
            # Donanım, IoT, Robotik, Elektronik, Maker
            ("esp32", "arduino", "raspberry", "sensor", "sensör", "elektronik", "robotik", "robot", "devre", "maker", "iot", "donanim", "donanım", "kamera", "lehim", "baskı", "3d"): ["#esp32", "#elektronik", "#iot", "#robotik", "#maker", "#teknoloji"],
            # Akıllı Ev, Otomasyon, Bitki, Çiçek, Doğa
            ("akilli", "akıllı", "otomasyon", "cicek", "çiçek", "bitki", "sera", "tarim", "tarım", "home", "ev", "oda", "sulama"): ["#otomasyon", "#akilliev", "#kendinyap", "#teknoloji"],
            # Yazılım, Kodlama, Web, Backend, Frontend
            ("yazilim", "yazılım", "kod", "programlama", "developer", "software", "python", "javascript", "react", "backend", "frontend", "fullstack", "github"): ["#yazilim", "#kodlama", "#yazilimci", "#teknoloji"],
            # Yapay Zeka, AI, LLM
            ("yapay", "zeka", "ai", "chatgpt", "gemini", "claude", "llm", "makine", "derin", "ogrenme", "gpt"): ["#yapayzeka", "#ai", "#teknoloji", "#gelecek"],
            # Kariyer, Mülakat, İş Hayatı
            ("mulakat", "mülakat", "kariyer", "cv", "ise", "işe", "terfi", "is", "iş", "maas", "maaş"): ["#mulakat", "#kariyer", "#isgorusmesi", "#kariyertavsiyeleri"],
            # Para, Finans, Borsa, Yatırım
            ("para", "zengin", "finans", "yatirim", "yatırım", "dolar", "kazanc", "kazanç", "gelir", "borsa", "kripto", "bitcoin", "hisse"): ["#para", "#finans", "#yatirim", "#zenginlik"],
            # Psikoloji, Kişisel Gelişim, Zihin
            ("psikoloji", "zihin", "davranis", "davranış", "iliski", "ilişki", "insan", "terapi", "beyin"): ["#psikoloji", "#kisiselgelisim", "#zihinselguc"],
            # Motivasyon, Disiplin, Başarı
            ("motivasyon", "hedef", "basari", "başarı", "disiplin", "odak", "verimlilik", "aliskanlik", "alışkanlık"): ["#motivasyon", "#basari", "#disiplin", "#odaklanma"],
            # Sağlık, Spor, Fitness, Beslenme
            ("saglik", "sağlık", "spor", "fitness", "beslenme", "diyet", "kilo", "kas", "antrenman"): ["#saglik", "#fitness", "#spor", "#saglikliyasam"],
            # Tarih, Savaş, Belgesel
            ("tarih", "savas", "savaş", "imparatorluk", "osmanli", "osmanlı", "belgesel", "antik"): ["#tarih", "#tarihibilgiler", "#belgesel"],
            # Oyun, Gaming, Espor
            ("oyun", "game", "gaming", "gamer", "oyuncu", "espor", "gameplay", "streamer"): ["#oyun", "#gamer", "#gaming", "#oyunlar", "#gameplay"],
            # Bilim, Eğitim, Uzay
            ("bilim", "egitim", "eğitim", "fizik", "kimya", "biyoloji", "uzay", "evren", "astronomi", "deney"): ["#bilim", "#egitim", "#uzay", "#bilgi"],
            # Yemek, Mutfak, Tarif
            ("yemek", "tarif", "mutfak", "lezzet", "tatli", "tatlı", "asci", "aşçı", "gurme", "tarifler"): ["#yemek", "#yemektarifleri", "#mutfak", "#lezzet"],
            # Sinema, Dizi, Film
            ("film", "dizi", "sinema", "fragman", "diziönerisi", "filmönerisi", "inceleme"): ["#filmönerisi", "#dizi", "#sinema", "#film"]
        }

        for keys, tags in niche_mappings.items():
            if any(k in combined for k in keys):
                added_for_niche = 0
                for t in tags:
                    if t not in seen and len(topic_tags) < 6:
                        topic_tags.append(t)
                        seen.add(t)
                        added_for_niche += 1
                        if added_for_niche >= 2:
                            break

        # Alfanümerik kelimeleri çıkar (örn. esp32, yapay, sensor, kamera)
        raw_words = re.findall(r'\b[a-zA-Z0-9çÇğĞıİöÖşŞüÜ]+\b', combined)
        special_shorts = {"ai", "iot", "vr", "ar", "ui", "ux", "pc", "3d", "4k"}

        for w in raw_words:
            w_clean = w.lower()
            if w_clean in tr_stop or w_clean.isdigit():
                continue
            if len(w_clean) >= 3 or w_clean in special_shorts:
                if len(topic_tags) < 6:
                    tag = f"#{w_clean}"
                    if tag not in seen:
                        topic_tags.append(tag)
                        seen.add(tag)

        general_tags = ["#kesfet", "#reels", "#viral", "#shorts", "#fyp"]
        for gt in general_tags:
            if gt not in seen and len(topic_tags) < 8:
                topic_tags.append(gt)
                seen.add(gt)

        return topic_tags[:8]

    def _fallback_clips(
        self,
        video_duration: float,
        count: int,
        video_title: str,
        formatted_transcript: str = "",
        offset: int = 0,
        youtube_url: str = "",
        existing_candidates: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """LLM çağrısı başarısız olursa veya ek klip gerektiğinde transkriptten çakışmayan gerçek kesitler çıkarır."""
        clips = []
        if count <= 0:
            return clips

        # Mevcut adayların kapladığı zaman aralıklarını topla
        occupied = []
        if existing_candidates:
            for ex in existing_candidates:
                try:
                    s = float(ex.get("start_time", 0.0))
                    e = float(ex.get("end_time", s + 30.0))
                    occupied.append((s, e))
                except (ValueError, TypeError):
                    continue

        def is_time_occupied(st: float, et: float) -> bool:
            dur = max(1.0, et - st)
            for os_t, oe_t in occupied:
                o_dur = max(1.0, oe_t - os_t)
                overlap = max(0.0, min(et, oe_t) - max(st, os_t))
                if (abs(st - os_t) < 12.0 and abs(et - oe_t) < 12.0) or (overlap / min(dur, o_dur) > 0.35):
                    return True
            return False

        # Doğal reels süresi (35s - 65s)
        clip_len = min(65.0, max(35.0, video_duration / max(count + 2, 1)))

        # Arama başlangıcı: Eğer mevcut adaylar varsa en sonuncusundan sonra ara
        max_occ_end = max([oe for _, oe in occupied], default=0.0)
        if max_occ_end > 10.0 and (max_occ_end + clip_len) <= video_duration:
            current_time = max_occ_end + 3.0
        else:
            step = max(25.0, (video_duration - 10.0) / max(count + len(occupied) + 2, 1))
            current_time = 5.0 + (offset * step)
            if current_time + 30.0 >= video_duration:
                current_time = 5.0

        transcript_lines = formatted_transcript.splitlines() if formatted_transcript else []
        idx = offset + 1
        attempts = 0
        max_attempts = int(video_duration // 15) + 35

        while len(clips) < count and attempts < max_attempts:
            attempts += 1
            if current_time + 25.0 > video_duration:
                # Başa sar ve arada kalan boşlukları tara
                current_time = 5.0
                if attempts > max_attempts // 2:
                    break

            end_t = min(current_time + clip_len, video_duration)
            if end_t - current_time < 25.0:
                current_time = 5.0
                continue

            # Çakışma kontrolü
            if is_time_occupied(current_time, end_t):
                # Çakışan aralığın sonuna atla
                for os_t, oe_t in occupied:
                    if not (end_t <= os_t or current_time >= oe_t):
                        current_time = oe_t + 2.0
                        break
                else:
                    current_time += 15.0
                continue

            # Bu zaman aralığındaki gerçek transkripti bul
            snippet = ""
            for line in transcript_lines:
                match = re.search(r'\[(\d+\.?\d*)s\s*-\s*(\d+\.?\d*)s\]:\s*(.*)', line)
                if match:
                    t = float(match.group(1))
                    if current_time <= t <= end_t:
                        snippet += " " + match.group(3).strip()
                        if len(snippet) > 220:
                            break
            snippet = snippet.strip() or f"{video_title} kesiti {idx}"
            title, desc = self.build_nlp_title_and_description(video_title, snippet)
            title = self.clean_title(title, video_title=video_title, snippet=snippet)
            desc = self.clean_description(desc, video_title=video_title, snippet=snippet)
            if youtube_url and youtube_url not in desc:
                desc = f"{desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()

            smart_tags = self.generate_smart_hashtags(video_title, snippet)

            clip_item = {
                "start_time": round(current_time, 1),
                "end_time": round(end_t, 1),
                "duration": round(end_t - current_time, 1),
                "score": round(max(75.0, 94.0 - (len(clips) * 1.5)), 1),
                "hook_score": round(max(7.2, 9.4 - (len(clips) * 0.2)), 1),
                "flow_score": round(max(7.0, 8.9 - (len(clips) * 0.15)), 1),
                "value_score": round(max(7.5, 9.1 - (len(clips) * 0.1)), 1),
                "title": title,
                "description": desc,
                "hashtags": smart_tags,
                "summary": "Video içindeki gerçek konuşma metninden türetilen dinamik kesit.",
                "transcript_snippet": snippet[:150]
            }
            clips.append(clip_item)
            occupied.append((current_time, end_t))
            current_time = end_t + 5.0
            idx += 1

        return clips
