import os
import re
import json
import time
import uuid
import logging
import subprocess
from typing import List, Dict, Any, Optional, Tuple

from app.config import settings
from app.services.scorer import ContentScorer
from app.services.video_editor import turkish_upper, clean_subtitle_word, get_word_emoji

logger = logging.getLogger(__name__)

TRAILERS_DIR = os.path.join(settings.DATA_DIR, "trailers")
os.makedirs(TRAILERS_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)

class TrailerGenerator:
    def __init__(self):
        self.scorer = ContentScorer()
        self.output_dir = settings.OUTPUT_DIR
        self.temp_dir = settings.TEMP_DIR
        self.trailers_dir = TRAILERS_DIR

    def get_trailer_metadata(self, trailer_id: str) -> Optional[Dict[str, Any]]:
        """Kayıtlı bir fragmanın JSON meta verilerini döner."""
        meta_path = os.path.join(self.trailers_dir, f"trailer_{trailer_id}.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    vname = meta.get("video_filename")
                    if vname:
                        vpath = os.path.join(self.output_dir, vname)
                        if os.path.exists(vpath):
                            meta["file_exists"] = True
                            if not meta.get("file_size_mb"):
                                meta["file_size_mb"] = round(os.path.getsize(vpath) / (1024 * 1024), 1)
                        else:
                            meta["file_exists"] = False

                    # Akıllı sosyal medya alanlarını zenginleştir
                    vt = meta.get("video_title", "")
                    if not meta.get("trailer_title"):
                        meta["trailer_title"] = vt.split("|")[0].split("-")[0].strip() if vt else "Akıllı Fragman"
                    if not meta.get("description"):
                        summaries = [sc.get("summary") for sc in meta.get("scenes", []) if sc.get("summary")]
                        if summaries:
                            meta["description"] = " ".join(summaries[:2]) + " Projenin tüm kilit anları bu videoda! 👇"
                        else:
                            clean_t = meta.get("trailer_title") or "Fragman"
                            meta["description"] = f"{clean_t} projesinin en önemli anları ve sonuçları! 👇"
                    # Eğer youtube_url, thumbnail veya original_title eksikse project_id üzerinden tamamla
                    pid = meta.get("project_id")
                    if pid:
                        try:
                            p_meta_file = os.path.join(settings.DOWNLOADS_DIR, pid, "meta.json")
                            if os.path.exists(p_meta_file):
                                with open(p_meta_file, "r", encoding="utf-8") as pmf:
                                    p_meta = json.load(pmf)
                                    if not meta.get("youtube_url") and p_meta.get("youtube_url"):
                                        meta["youtube_url"] = p_meta["youtube_url"]
                                    if not meta.get("thumbnail") and p_meta.get("thumbnail"):
                                        meta["thumbnail"] = p_meta["thumbnail"]
                                    if not meta.get("original_title") and p_meta.get("title"):
                                        meta["original_title"] = p_meta["title"]
                        except Exception:
                            pass

                    # Açıklama metnindeki mükerrer "👇" ve noktalama işaretlerini temizle
                    if meta.get("description"):
                        desc = meta["description"]
                        desc = re.sub(r'(👇\s*[\.\,\:]*\s*)+', '👇\n\n', desc)
                        yt_link = meta.get("youtube_url")
                        if yt_link and yt_link not in desc:
                            desc = f"{desc.strip()}\n\n🎬 Videonun tamamı: {yt_link}".strip()
                        meta["description"] = re.sub(r'\n{3,}', '\n\n', desc).strip()

                    # Doğru fragman süresini hesapla
                    if not meta.get("trailer_duration") and meta.get("scenes"):
                        scenes_dur = sum(sc.get("duration", 0) for sc in meta["scenes"])
                        card_dur = 1.0 if meta.get("style") == "cinematic" else 0.0
                        meta["trailer_duration"] = round(scenes_dur + max(0, len(meta["scenes"]) - 1) * card_dur, 1)
                        meta["duration"] = meta["trailer_duration"]

                    return meta
            except Exception as e:
                logger.error(f"Error reading trailer metadata {trailer_id}: {e}")
        return None

    def save_trailer_metadata(self, trailer_id: str, data: Dict[str, Any]) -> None:
        """Fragman meta verilerini diske kaydeder."""
        meta_path = os.path.join(self.trailers_dir, f"trailer_{trailer_id}.json")
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving trailer metadata {trailer_id}: {e}")

    def list_all_trailers(self) -> List[Dict[str, Any]]:
        """Tüm kayıtlı fragmanları en yeniden en eskiye doğru listeler."""
        results = []
        if not os.path.exists(self.trailers_dir):
            return results
        for fn in os.listdir(self.trailers_dir):
            if fn.startswith("trailer_") and fn.endswith(".json"):
                tid = fn.replace("trailer_", "").replace(".json", "")
                meta = self.get_trailer_metadata(tid)
                if meta and meta.get("trailer_id"):
                    if not meta.get("title"):
                        meta["title"] = meta.get("trailer_title") or meta.get("video_title") or meta.get("original_title") or "Sinematik Fragman"
                    vname = meta.get("video_filename")
                    vpath = os.path.join(self.output_dir, vname) if vname else None
                    if vpath and os.path.exists(vpath):
                        meta["file_exists"] = True
                        if not meta.get("file_size_mb"):
                            meta["file_size_mb"] = round(os.path.getsize(vpath) / (1024 * 1024), 1)
                    else:
                        meta["file_exists"] = False
                    results.append(meta)
        results.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return results

    def delete_trailer(self, trailer_id: str) -> bool:
        """Fragman video dosyasını ve meta veri JSON dosyasını siler."""
        meta = self.get_trailer_metadata(trailer_id)
        if meta and meta.get("video_filename"):
            v_path = os.path.join(self.output_dir, meta["video_filename"])
            if os.path.exists(v_path):
                try:
                    os.remove(v_path)
                except Exception as e:
                    logger.warning(f"Could not remove trailer video {v_path}: {e}")
        meta_path = os.path.join(self.trailers_dir, f"trailer_{trailer_id}.json")
        if os.path.exists(meta_path):
            try:
                os.remove(meta_path)
                return True
            except Exception as e:
                logger.error(f"Could not remove trailer json {meta_path}: {e}")
        return False

    @staticmethod
    def parse_formatted_text_to_segments(formatted_text: str) -> List[Dict[str, Any]]:
        """formatted_text string'ini [{start, end, text}] listesine çevirir."""
        segments = []
        for line in formatted_text.splitlines():
            line = line.strip()
            m = re.match(r'\[([\d\.]+)s\s*-\s*([\d\.]+)s\]:\s*(.+)', line)
            if m:
                segments.append({
                    "start": float(m.group(1)),
                    "end": float(m.group(2)),
                    "text": m.group(3).strip()
                })
        return segments

    @staticmethod
    def group_words_to_segments(words: List[Dict[str, Any]], target_chunk_sec: float = 6.0) -> List[Dict[str, Any]]:
        """Kelime listesini zaman aralıklarına göre segmentlere gruplar."""
        if not words:
            return []
        segments = []
        cur_words = []
        seg_start = words[0].get("start", 0)

        for w in words:
            cur_words.append(w.get("word", ""))
            if (w.get("end", 0) - seg_start) >= target_chunk_sec or w.get("word", "").endswith((".", "!", "?")):
                segments.append({
                    "start": seg_start,
                    "end": w.get("end", seg_start + 1),
                    "text": " ".join(cur_words).strip()
                })
                cur_words = []
                seg_start = w.get("end", 0)

        if cur_words:
            segments.append({
                "start": seg_start,
                "end": words[-1].get("end", seg_start + 1),
                "text": " ".join(cur_words).strip()
            })
        return segments

    @staticmethod
    def snap_scene_boundaries_to_sentences(
        scenes: List[Dict[str, Any]],
        words: List[Dict[str, Any]],
        total_duration: float,
        max_extend_end: float = 7.5,
        max_shrink_end: float = 3.5,
        max_shift_start: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Sahnelerin başlangıç ve bitiş zamanlarını Whisper kelime zaman damgaları
        ve noktalama işaretlerine göre kenetler.
        Böylece konuşmacının sözleri asla cümlenin ortasında, bağlaçlarda
        (ve, yani, ortaya, kendi, çünkü) veya yan cümleciklerde kesilmez;
        tam bir düşünce ve cümle sonuna kadar uzatılır.
        """
        if not scenes or not words:
            return scenes

        terminal_punct = {".", "?", "!", "..."}
        clause_punct = {",", ";", ":"}

        forbidden_ends = {
            "ve", "veya", "ama", "fakat", "lakin", "ancak", "çünkü", "yani", "oysa", "oysaki",
            "için", "gibi", "kadar", "diye", "göre", "doğru", "karşı", "beri", "üzere", "rağmen",
            "bu", "şu", "o", "bunlar", "şunlar", "onlar", "kendi", "kendisi", "kendileri",
            "bir", "bunu", "şunu", "onu", "bunun", "şunun", "onun", "burada", "şurada", "orada",
            "hangi", "nasıl", "neden", "ortaya", "meydana", "yer", "karar", "hareket", "kabul",
            "dahil", "ait", "sahip", "ile", "de", "da", "ki", "hem", "ise", "ya", "yahut",
            "zira", "nitekim", "halbuki", "üretmezse", "kullanırsa", "yaparsa", "ederse",
            "olursa", "giderse", "bakarsa", "görürse", "üstürürse", "üstlenirse", "olduğunda",
            "başladığında", "dediğimizde", "söylediğimizde"
        }

        forbidden_starts = {
            "he", "ııı", "eee", "hımm", "şey", "yani", "ama", "fakat", "çünkü", "ve", "veya",
            "lakin", "ancak", "oysa", "oysaki", "madem", "zira", "gibi", "için", "kadar", "diye",
            "göre", "ile", "de", "da", "ki"
        }

        def clean_w(w_str: str) -> str:
            return re.sub(r"[^\wçÇğĞıİöÖşŞüÜ]", "", w_str).lower()

        def has_terminal(w_str: str) -> bool:
            return any(w_str.endswith(p) for p in terminal_punct)

        snapped_scenes = []

        for idx, sc in enumerate(scenes):
            raw_st = float(sc.get("start_time", 0.0))
            raw_et = float(sc.get("end_time", raw_st + 10.0))
            raw_dur = max(3.0, raw_et - raw_st)

            # --- 1. BAŞLANGIÇ KENETLEME (START SNAPPING) ---
            start_candidates = [
                (i, w) for i, w in enumerate(words)
                if (raw_st - max_shift_start) <= w.get("start", 0.0) <= (raw_st + 3.0)
            ]

            best_start_idx = None
            best_start_score = -999.0

            for i, w in start_candidates:
                w_clean = clean_w(w.get("word", ""))
                prev_w = words[i - 1] if i > 0 else None

                if w_clean in forbidden_starts:
                    continue

                score = 0.0
                if raw_st <= 1.0 and i == 0:
                    score += 100.0

                if prev_w and has_terminal(prev_w.get("word", "")):
                    score += 60.0
                elif prev_w and (w.get("start", 0.0) - prev_w.get("end", 0.0)) >= 0.35:
                    score += 35.0
                elif prev_w and any(prev_w.get("word", "").endswith(p) for p in clause_punct):
                    score += 15.0

                # Görsel referans başlangıç bonusu ("Ekranda", "Özellikle", "Şimdi", "Bakın")
                if w_clean in {"ekranda", "özellikle", "şimdi", "bakın", "mesela"} and prev_w and has_terminal(prev_w.get("word", "")):
                    score += 25.0

                dist = abs(w.get("start", 0.0) - raw_st)
                score -= dist * 4.0

                if score > best_start_score:
                    best_start_score = score
                    best_start_idx = i

            if best_start_idx is not None:
                snapped_st = max(0.0, round(words[best_start_idx].get("start", 0.0) - 0.08, 2))
            else:
                snapped_st = round(raw_st, 2)

            # --- 2. BİTİŞ KENETLEME (END SNAPPING) ---
            # Öncelik 1: raw_et'den sonraki ilk tam cümle sonunu ara [raw_et, raw_et + max_extend_end]
            forward_candidates = [
                (i, w) for i, w in enumerate(words)
                if raw_et <= w.get("end", 0.0) <= (raw_et + max_extend_end)
            ]

            chosen_end_idx = None
            for i, w in forward_candidates:
                if has_terminal(w.get("word", "")) and (w.get("end", 0.0) - snapped_st) >= min(3.0, raw_dur):
                    chosen_end_idx = i
                    break

            # Öncelik 2: İleriye doğru bulunamadıysa geriye doğru tam cümle sonu ara [raw_et - max_shrink_end, raw_et]
            if chosen_end_idx is None:
                backward_candidates = [
                    (i, w) for i, w in enumerate(words)
                    if (raw_et - max_shrink_end) <= w.get("end", 0.0) <= raw_et
                ]
                for i, w in reversed(backward_candidates):
                    if has_terminal(w.get("word", "")) and (w.get("end", 0.0) - snapped_st) >= min(4.0, raw_dur * 0.6):
                        chosen_end_idx = i
                        break

            # Öncelik 3: Hiç tam nokta/soru işareti bulunamadıysa yasaklı olmayan, nefes/duraksama olan en iyi kelimeyi seç
            if chosen_end_idx is None:
                all_candidates = [
                    (i, w) for i, w in enumerate(words)
                    if (raw_et - max_shrink_end) <= w.get("end", 0.0) <= (raw_et + max_extend_end)
                ]
                best_e_score = -999.0
                for i, w in all_candidates:
                    w_clean = clean_w(w.get("word", ""))
                    if w_clean in forbidden_ends and not has_terminal(w.get("word", "")):
                        continue
                    next_w = words[i + 1] if i + 1 < len(words) else None
                    pause_gap = (next_w.get("start", 0.0) - w.get("end", 0.0)) if next_w else 0.0
                    score = 0.0
                    if has_terminal(w.get("word", "")):
                        score += 80.0
                    elif pause_gap >= 0.55:
                        score += 65.0  # Güçlü duraksama (noktalama olmasa bile doğal nefes sınırı)
                    elif pause_gap >= 0.35:
                        score += 35.0
                    elif any(w.get("word", "").endswith(p) for p in clause_punct):
                        score += 20.0
                    diff = abs(w.get("end", 0.0) - raw_et)
                    score -= diff * 3.0
                    if score > best_e_score:
                        best_e_score = score
                        chosen_end_idx = i

            if chosen_end_idx is not None:
                # Seçilen kelime havada kalan bağlaç veya yan cümlecikse cümleyi bitirene veya nefese kadar ileri tara
                w_clean = clean_w(words[chosen_end_idx].get("word", ""))
                if w_clean in forbidden_ends and not has_terminal(words[chosen_end_idx].get("word", "")):
                    for fwd_i in range(chosen_end_idx + 1, min(len(words), chosen_end_idx + 18)):
                        fwd_w = words[fwd_i]
                        fwd_next = words[fwd_i + 1] if fwd_i + 1 < len(words) else None
                        fwd_pause = (fwd_next.get("start", 0.0) - fwd_w.get("end", 0.0)) if fwd_next else 0.0
                        if has_terminal(fwd_w.get("word", "")) or fwd_pause >= 0.5:
                            chosen_end_idx = fwd_i
                            break

                snapped_et = min(total_duration, round(words[chosen_end_idx].get("end", 0.0) + 0.18, 2))
            else:
                snapped_et = round(raw_et, 2)

            # Minimum ve maksimum sahne süresi sınırları
            raw_dur = max(3.0, raw_et - raw_st)
            if snapped_et <= snapped_st + 3.0:
                snapped_et = min(total_duration, round(snapped_st + min(raw_dur, 8.0), 2))
            else:
                # Kullanıcının talep ettiği süreye göre dinamik tavan (kullanıcı 60s veya 70s seçtiyse asla 40s'ye zorlanmaz)
                max_allowed_dur = max(42.0, raw_dur + max_extend_end)
                if (snapped_et - snapped_st) > max_allowed_dur:
                    snapped_et = min(total_duration, round(snapped_st + max_allowed_dur, 2))

            new_sc = dict(sc)
            new_sc["start_time"] = snapped_st
            new_sc["end_time"] = snapped_et
            new_sc["duration"] = round(snapped_et - snapped_st, 2)
            snapped_scenes.append(new_sc)

        # 3. Sahneler Arası Çakışmaları Engelle (Prevent Inter-Scene Overlaps)
        for i in range(len(snapped_scenes) - 1):
            if snapped_scenes[i]["end_time"] >= snapped_scenes[i + 1]["start_time"]:
                snapped_scenes[i]["end_time"] = round(snapped_scenes[i + 1]["start_time"] - 0.2, 2)
                snapped_scenes[i]["duration"] = round(snapped_scenes[i]["end_time"] - snapped_scenes[i]["start_time"], 2)

        return snapped_scenes

    # =========================================================================
    # 1. AKILLI HİKAYE EĞRİSİ ANALİZİ (NARRATIVE ARC SELECTION)
    # =========================================================================
    def select_narrative_scenes(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_title: str,
        total_duration: float,
        target_duration: int = 60,
        all_words: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Videonun tüm transkriptini baştan sona analiz ederek izleyicide
        'tüm videoyu izlemiş kadar doyurucu bilgi' bırakan, mantık zinciri
        kopmayan kilit sahneleri seçer ve cümle sınırlarına kenetler.
        """
        if not transcript_segments:
            return [], {}

        # A. LLM ile Derin Anlatı Analizi Denemesi
        try:
            scenes, meta_info = self._select_scenes_via_llm(
                transcript_segments, video_title, total_duration, target_duration
            )
            if scenes and len(scenes) >= 2:
                if all_words:
                    scenes = self.snap_scene_boundaries_to_sentences(scenes, all_words, total_duration)
                logger.info(f"LLM successfully selected {len(scenes)} trailer scenes.")
                return scenes, meta_info
        except Exception as e:
            logger.warning(f"LLM narrative selection failed ({e}), falling back to smart heuristic arc...")

        # B. Fallback: Akıllı Kronolojik Kural Tabanlı Hikaye Eğrisi
        scenes, meta_info = self._select_scenes_heuristic(transcript_segments, total_duration, target_duration, video_title)
        if all_words:
            scenes = self.snap_scene_boundaries_to_sentences(scenes, all_words, total_duration)
        return scenes, meta_info

    def _select_scenes_via_llm(
        self,
        segments: List[Dict[str, Any]],
        video_title: str,
        total_duration: float,
        target_duration: int
    ) -> List[Dict[str, Any]]:
        """LLM kullanarak transkriptten hikaye sırasına göre kilit sahneleri seçer."""
        # 1. Hedef süreye göre dinamik sahne sayısı ve süre aralıklarını belirle
        if target_duration <= 45:
            min_scenes, max_scenes = 3, 4
            per_scene_dur_text = "8-14 saniye"
            structure_text = (
                "   - Perde 1 (Giriş & Amaç): Video ne hakkında, sorun veya amaç nedir?\n"
                "   - Perde 2 (Gelişme & Detay): Yapılan çalışmalar veya kritik detay.\n"
                "   - Perde 3 (Sonuç & Zirve): Çözüm ve nihai sonuç."
            )
        elif target_duration <= 75:
            min_scenes, max_scenes = 4, 5
            per_scene_dur_text = "12-18 saniye"
            structure_text = (
                "   - Perde 1 (Giriş & Amaç): Video ne hakkında, sorun veya amaç nedir?\n"
                "   - Perde 2 (Gelişme & Zorluk): Yapılan çalışmalar, karşılaşılan engel veya kritik detay.\n"
                "   - Perde 3 (Zirve & Çözüm): Çözümün çalıştığı an, yapay zeka/teknolojinin devreye girdiği nokta.\n"
                "   - Perde 4 (Sonuç & Gelecek): Ortaya çıkan nihai başarı veya kapanış."
            )
        elif target_duration <= 105:
            min_scenes, max_scenes = 4, 6
            per_scene_dur_text = "15-22 saniye"
            structure_text = (
                "   - 1. Başlangıç, Amaç & Proje\n"
                "   - 2. Sistem Tasarımı & Altyapı\n"
                "   - 3. Zorluklar & Karşılaşılan Engeller\n"
                "   - 4. Çözüm & Canlı Deneyim\n"
                "   - 5. Nihai Sonuç & Kapanış"
            )
        elif target_duration <= 150:  # 2 Dakika (120s)
            min_scenes, max_scenes = 5, 7
            per_scene_dur_text = "18-28 saniye"
            structure_text = (
                "   - 1. Giriş & Projenin Ana Hedefi\n"
                "   - 2. Karşılaşılan Problem & İhtiyaç\n"
                "   - 3. Mimari / Teknik Uygulama & Donanım\n"
                "   - 4. Testler, Canlı Demo & Analizler\n"
                "   - 5. Zirve Noktası & Elde Edilen Başarı\n"
                "   - 6. Gelecek Planları & Değerlendirme"
            )
        elif target_duration <= 240:  # 3-4 Dakika (180s - 240s)
            min_scenes, max_scenes = 6, 9
            per_scene_dur_text = "20-35 saniye"
            structure_text = (
                "   - Videonun 30-40 dakikalık derinliğini yansıtan detaylı kurgu: Girişten sonuca kadar "
                "tüm ana bölümleri kronolojik sırayla kapsayan 6 ila 9 kilit sahne seç."
            )
        elif target_duration <= 360:  # 5-6 Dakika (300s - 360s)
            min_scenes, max_scenes = 8, 12
            per_scene_dur_text = "25-40 saniye"
            structure_text = (
                "   - Kapsamlı mini belgesel kurgusu: Giriş, Problem, Hazırlık, Uygulama, Donanım/Yazılım, "
                "Analizler, Zorluklar, Çözüm, Canlı Sonuçlar ve Kapanış olmak üzere 8 ila 12 kilit sahne seç."
            )
        else:  # 10 Dakika ve üzeri (600s+)
            min_scenes, max_scenes = 10, 16
            per_scene_dur_text = "30-50 saniye"
            structure_text = (
                "   - Derinlemesine konu anlatımı kurgusu: Videonun tüm ana başlıklarını ve kilometre taşlarını "
                "eksiksiz kapsayan 10 ila 16 kilit sahne seç."
            )

        # 2. Transkripti kompakt ve anlamlı cümle bloklarına dönüştür (Token verimliliği)
        condensed_blocks = []
        cur_block_start = None
        cur_block_end = None
        cur_block_text = []

        for s in segments:
            st = s.get("start", 0)
            et = s.get("end", 0)
            txt = s.get("text", "").strip()
            if not txt:
                continue

            if cur_block_start is None:
                cur_block_start = st
                cur_block_end = et
                cur_block_text.append(txt)
            else:
                cur_block_end = et
                cur_block_text.append(txt)
                if (cur_block_end - cur_block_start) >= 12.0 or txt.endswith((".", "!", "?")):
                    condensed_blocks.append({
                        "start": cur_block_start,
                        "end": cur_block_end,
                        "text": " ".join(cur_block_text)
                    })
                    cur_block_start = None
                    cur_block_end = None
                    cur_block_text = []

        if cur_block_start is not None and cur_block_text:
            condensed_blocks.append({
                "start": cur_block_start,
                "end": cur_block_end,
                "text": " ".join(cur_block_text)
            })

        if not condensed_blocks:
            condensed_blocks = segments

        transcript_lines = [
            f"[{b['start']:.1f}s - {b['end']:.1f}s]: {b['text']}"
            for b in condensed_blocks
        ]
        full_text = "\n".join(transcript_lines)

        # 30-40 dakikalık uzun videolarda LLM bağlam penceresini aşmamak için dengeli örnekleme yap
        if len(full_text) > 36000:
            step = max(1.2, len(transcript_lines) / (36000 / 120))
            sampled_lines = []
            cur_idx = 0.0
            while int(cur_idx) < len(transcript_lines):
                sampled_lines.append(transcript_lines[int(cur_idx)])
                cur_idx += step
            full_text = "\n".join(sampled_lines)
            if len(full_text) > 36000:
                full_text = full_text[:36000] + "\n...[transkript sonu]"

        system_prompt = f"""Sen ödüllü bir belgesel, film ve YouTube video kurgu yönetmenisin.
Görevin: Verilen video transkriptini baştan sona BÜTÜNCÜL olarak analiz etmek ve izleyicide "tüm videoyu izlemiş kadar net ve doyurucu bilgi" bırakan akıllı bir video fragmanı / özeti kurgulamak; ayrıca bu fragman için sosyal medyada (Reels, TikTok, Shorts) maksimum izlenme ve etkileşim getirecek başlık, açıklama ve etiketler üretmektir.

KURALLAR:
1. RASTGELE PARÇALAR SEÇME! Videonun doğal zaman çizelgesini takip eden {min_scenes} ila {max_scenes} kronolojik bölüm seç:
{structure_text}
2. DİLBİLGİSEL BAĞLAM VE GÖRSEL REFERANS KURALI:
   - Asla öncesi bilinmeden anlaşılamayan cümlelerle başlama ("O yüzden...", "Bunun gibi...", "O adam da öyle deyince..." gibi cümleleri seçme).
   - Mutlaka bağımsız, öznesi belli, anlamlı ve tam cümleleri seç.
   - GÖRSEL VE REFERANS VİDEO BÜTÜNLÜĞÜ (ÇOK ÖNEMLİ): Eğer videoda ekranda bir maç (örn. Kasparov Deep Blue), oyun tahtası (AlphaGo 37. hamle), donanım, grafik veya fotoğraf gösteriliyorsa; konuşmacının "Ekranda gördüğünüz...", "Şu an ekrana gelen...", "Özellikle meşhur..." gibi o referansı sunduğu giriş cümlesini ASLA ATLAYIP ORTADAN BAŞLAMA! Sahneyi referansın sunulduğu cümlenin tam başından başlat.
   - SÖZÜ VE DÜŞÜNCEYİ ASLA YARIM BIRAKMA: Konuşmacının sözünü ve fikrini bitirmeden, bağlaçlarda ("ve", "yani", "çünkü", "ama") veya yan cümleciklerde ("yaparsa,", "kullanırsa,") kesme! Cümlenin nokta (.) veya soru işareti (?) ile biten nihai yüklemine kadar devam ettir.
3. ELEŞTİRİ, TEPKİ & DIŞ KAYNAK VİDEOLARI (REACTION / ELEŞTİRİ BÜTÜNLÜĞÜ):
   - Videoda ana anlatıcı başka bir videodan kesit, alıntı veya örnek bir olay gösterip bunu eleştiriyor ya da yorumluyorsa; KESİNLİKLE sadece aradaki alıntıyı tek başına kesme!
   - Kurgu üçlemesini koru: [Ana Anlatıcının Sorusu / Girişi] -> [İzletilen Dış Video/Alıntı] -> [Ana Anlatıcının Eleştirisi / Hükmü]. Sahne dışarıdan bir kesit içeriyorsa, bitişi MUTLAKA ana anlatıcının o kesite yaptığı eleştirinin/yorumun bittiği cümlenin sonuna kadar uzat.
4. SÜRE HEDEFİ:
   - Seçilen tüm sahnelerin toplam konuşma süresi yaklaşık hedef süreye (hedef: {target_duration} saniye) yakın olsun. Her sahne {per_scene_dur_text} arasında olmalıdır.
5. BÖLÜM BAŞLIĞI:
   - Her sahne için aralarda gösterilecek 1-3 kelimelik etkileyici ve sinematik Türkçe bir başlık yaz (Örn: "1. HEDEF & PROJE", "2. BÜYÜK ZORLUK", "3. YAPAY ZEKA DEVRİNDE", "4. NİHAİ SONUÇ").
6. FRAGMAN BAŞLIĞI (trailer_title):
   - Orijinal YouTube başlığını aynen kopyalama! Sosyal medyada (Reels / TikTok) merak uyandıracak, ana videodan daha kısa (4-7 kelime), vurucu ve dikkat çekici bir Türkçe başlık yaz (Örn: "Evde Yapay Zekalı Çiçek Odası Kurduk! 🌸🤖" veya "Tüm Projeyi 60 Saniyede Özetledik!").
7. AÇIKLAMA (description):
   - İzleyicide videoyu izleme isteği uyandıran, videoda ne anlatıldığını özetleyen 1-2 cümlelik akıcı, doğal ve kaliteli bir sosyal medya açıklama metni yaz. Asla "yapay zeka özeti" gibi robotik/klişe ifadeler kullanma.
8. ETİKETLER (hashtags):
   - KESİNLİKLE videoda konuşulan spesifik konunun anahtar kavramlarına odaklı 6-8 etiket dizisi (Örn: ["#yapayzeka", "#esp32", "#iot", "#akilliev", "#teknoloji", "#bitkibakimi", "#reels"]). Asla konuyla alakasız etiket yazma!

YANIT FORMATI: Sadece ve sadece aşağıdaki JSON şemasını döndür, başka hiçbir açıklama yazma:
{{
  "trailer_title": "Evde Yapay Zekalı Çiçek Odası Kurduk! 🌸🤖",
  "description": "ESP32 sensörleri ve yapay zeka ile bitkilerin dilinden anlayan akıllı oda projemizin tüm aşamaları! 👇",
  "hashtags": ["#yapayzeka", "#esp32", "#iot", "#akilliev", "#teknoloji", "#reels"],
  "scenes": [
    {{
      "act_number": 1,
      "chapter_title": "1. BAŞLANGIÇ & HEDEF",
      "start_time": 10.5,
      "end_time": 24.0,
      "summary": "Projenin amacını anlatıyor",
      "quote": "Evimizde akıllı çiçek odası kurduk..."
    }}
  ]
}}"""

        user_prompt = f"Video Başlığı: {video_title}\nToplam Video Süresi: {total_duration:.1f} saniye\nHedef Fragman Süresi: {target_duration} saniye\n\nTranskript:\n{full_text}"

        try:
            raw_json = self.scorer._call_llm(system_prompt, user_prompt, temperature=0.3, timeout=90)
            data = json.loads(raw_json)
            scenes = data.get("scenes", [])
            logger.info(f"LLM successfully selected {len(scenes)} trailer scenes for target {target_duration}s.")
        except Exception as e:
            logger.warning(f"LLM trailer selection failed ({e}), falling back to narrative heuristic.")
            return self._select_scenes_heuristic(segments, total_duration, target_duration, video_title)

        # Doğrulama ve temizleme
        valid_scenes = []
        max_single_dur = max(40.0, (target_duration / min_scenes) * 1.6)
        for idx, sc in enumerate(scenes):
            st = float(sc.get("start_time", 0))
            et = float(sc.get("end_time", 0))
            dur = et - st
            if 4.0 <= dur <= max_single_dur and st < total_duration:
                et = min(et, total_duration)
                valid_scenes.append({
                    "act_number": idx + 1,
                    "chapter_title": sc.get("chapter_title", f"{idx + 1}. BÖLÜM").strip(),
                    "start_time": round(st, 2),
                    "end_time": round(et, 2),
                    "duration": round(et - st, 2),
                    "summary": sc.get("summary", ""),
                    "quote": sc.get("quote", "")
                })

        if len(valid_scenes) < min_scenes:
            logger.warning(f"LLM produced only {len(valid_scenes)} valid scenes (min needed {min_scenes}). Using heuristic fallback.")
            return self._select_scenes_heuristic(segments, total_duration, target_duration, video_title)

        # Kronolojik sıraya diz
        valid_scenes.sort(key=lambda x: x["start_time"])

        # Akıllı başlık, açıklama ve etiket çıkarma
        trailer_title = data.get("trailer_title")
        if not trailer_title or len(trailer_title) > 85:
            clean_t = video_title.split("|")[0].split("-")[0].strip() if video_title else "Akıllı Fragman"
            trailer_title = clean_t if clean_t else video_title[:60].strip()
        trailer_title = ContentScorer.clean_title(trailer_title, video_title=video_title)

        description = data.get("description")
        if not description:
            actual_quotes = [sc.get("quote", "").replace("...", "").strip() for sc in valid_scenes if sc.get("quote")]
            meaningful_text = " ".join(actual_quotes[:2]).strip()
            if meaningful_text and len(meaningful_text) > 20:
                description = ContentScorer.clean_description(meaningful_text, video_title=video_title)
            else:
                description = f"{trailer_title} hakkında tüm detaylar ve kilit anlar!"
        else:
            description = ContentScorer.clean_description(description, video_title=video_title)

        if not description.endswith("👇"):
            description = f"{description} 👇"

        hashtags = data.get("hashtags")
        if not hashtags or not isinstance(hashtags, list) or len(hashtags) < 3 or any("clipforge" in h.lower() for h in hashtags):
            snippet = " ".join([sc.get("summary", "") + " " + sc.get("quote", "") for sc in valid_scenes])
            hashtags = self.scorer.generate_smart_hashtags(video_title or trailer_title, snippet)

        meta_info = {
            "trailer_title": trailer_title,
            "description": description,
            "hashtags": hashtags
        }
        return valid_scenes, meta_info

    def _select_scenes_heuristic(
        self,
        segments: List[Dict[str, Any]],
        total_duration: float,
        target_duration: int,
        video_title: str = ""
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        LLM yanıt vermediğinde veya arıza yaptığında devreye giren
        hedef süreye göre dinamik ölçeklenen kronolojik akıllı seçim algoritması.
        """
        if target_duration <= 50:
            num_acts = 3
        elif target_duration <= 80:
            num_acts = 4
        elif target_duration <= 130:  # 2 Dakika
            num_acts = 5
        elif target_duration <= 210:  # 3 Dakika
            num_acts = 6
        elif target_duration <= 360:  # 5-6 Dakika
            num_acts = 8
        else:  # 10 Dakika ve üzeri
            num_acts = min(12, max(8, target_duration // 35))

        titles_pool = [
            "1. GİRİŞ & AMAÇ",
            "2. İLK HAZIRLIKLAR",
            "3. GELİŞME & ZORLUK",
            "4. TEKNİK SİSTEM",
            "5. YAPAY ZEKA & TEŞHİS",
            "6. TESTLER & DENEYİM",
            "7. KRİTİK DÖNÜM NOKTASI",
            "8. ÇÖZÜM & BAŞARI",
            "9. GELECEK VİZYONU",
            "10. NİHAİ DEĞERLENDİRME",
            "11. SON SÖZLER & KAPANIŞ",
            "12. PROJE ÖZETİ"
        ]

        per_scene_target = max(10, target_duration // num_acts)
        forbidden_starts = ("o yüzden", "bunun gibi", "bu yüzden", "çünkü", "ve", "ama", "fakat", "o da", "onun gibi")

        scenes = []
        for i in range(num_acts):
            start_pct = i / num_acts
            end_pct = (i + 1) / num_acts
            title = titles_pool[i] if i < len(titles_pool) else f"{i + 1}. BÖLÜM"

            min_sec = total_duration * start_pct
            max_sec = total_duration * end_pct

            bucket_segs = [s for s in segments if min_sec <= s.get("start", 0) < max_sec]
            if not bucket_segs:
                closest_seg = min(segments, key=lambda s: abs(s.get("start", 0) - (min_sec + max_sec) / 2))
                bucket_segs = [closest_seg]

            # En iyi başlangıç segmentini bul (Yasaklı bağlaçlarla başlamayan, dolgun cümle)
            best_start_idx = -1
            best_score = -1
            for idx_s, seg in enumerate(bucket_segs):
                txt = seg.get("text", "").strip().lower()
                if any(txt.startswith(fb) for fb in forbidden_starts):
                    continue
                score = len(txt)
                if "?" in txt or "!" in txt or "yapay zeka" in txt or "sistem" in txt or "amaç" in txt or "proje" in txt:
                    score += 50
                if score > best_score:
                    best_score = score
                    best_start_idx = idx_s

            if best_start_idx == -1:
                best_start_idx = 0

            # İdeal süreye ulaşana kadar ardışık segmentleri topla
            cur_start = bucket_segs[best_start_idx].get("start", min_sec)
            cur_end = bucket_segs[best_start_idx].get("end", cur_start + 5)
            collected_text = [bucket_segs[best_start_idx].get("text", "")]

            for j in range(best_start_idx + 1, len(bucket_segs)):
                next_seg = bucket_segs[j]
                if (next_seg.get("end", 0) - cur_start) > per_scene_target + 4:
                    break
                cur_end = next_seg.get("end", cur_end)
                collected_text.append(next_seg.get("text", ""))

            dur = cur_end - cur_start
            if dur >= 5.0:
                scenes.append({
                    "act_number": len(scenes) + 1,
                    "chapter_title": title,
                    "start_time": round(cur_start, 2),
                    "end_time": round(cur_end, 2),
                    "duration": round(dur, 2),
                    "summary": f"{title} bölümünden seçildi.",
                    "quote": " ".join(collected_text)[:140] + "..."
                })

        raw_clean_t = video_title.split("|")[0].split("-")[0].strip() if video_title else "Akıllı Fragman"
        clean_title = ContentScorer.clean_title(raw_clean_t, video_title=video_title)

        meaningful_quotes = [sc.get("quote", "").replace("...", "").strip() for sc in scenes if sc.get("quote") and not sc.get("quote", "").startswith("1.") and not sc.get("quote", "").startswith("2.")]
        quote_text = " ".join(meaningful_quotes[:2]).strip()
        if quote_text and len(quote_text) > 20:
            desc = ContentScorer.clean_description(quote_text, video_title=video_title)
            if not desc.endswith("👇"):
                desc = f"{desc} Tüm detaylar ve kilit anlar bu videoda! 👇"
        else:
            desc = f"{clean_title} projesinin tüm aşamaları ve en önemli anları! 👇"

        snippet = " ".join([sc.get("quote", "") for sc in scenes])
        smart_tags = self.scorer.generate_smart_hashtags(video_title or clean_title, snippet)

        return scenes, {
            "trailer_title": clean_title,
            "description": desc,
            "hashtags": smart_tags
        }

    # =========================================================================
    # 2. BİRLEŞTİRİLMİŞ VİDEO İÇİN ALTYAZI RE-TIMING (SUBTITLES)
    # =========================================================================
    def build_trailer_ass_subtitles(
        self,
        scenes: List[Dict[str, Any]],
        all_words: List[Dict[str, Any]],
        ass_output_path: str,
        aspect_ratio: str = "9:16",
        card_duration: float = 1.0,
        style: str = "cinematic"
    ) -> bool:
        """
        Her sahnenin içindeki Whisper kelimelerini, birleştirilmiş yeni
        fragman videosunun zaman çizgisine (kartlar dahil) göre re-time eder.
        """
        if aspect_ratio == "16:9":
            # 16:9 Yatay YouTube Formatı için Altyazı
            play_res_x, play_res_y = 1920, 1080
            font_size = 56
            margin_v = 120
        else:
            # 9:16 Dikey Shorts/Reels Formatı için Altyazı
            play_res_x, play_res_y = 1080, 1920
            font_size = 62
            margin_v = 560

        header = f"""[Script Info]
Title: ClipForge AI Trailer Subtitles
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,5.0,2.0,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def format_time(sec: float) -> str:
            sec = max(0.0, sec)
            hrs = int(sec // 3600)
            mins = int((sec % 3600) // 60)
            secs = int(sec % 60)
            centisecs = int((sec - int(sec)) * 100)
            return f"{hrs:01d}:{mins:02d}:{secs:02d}.{centisecs:02d}"

        events = []
        timeline_cursor = 0.0

        for idx, sc in enumerate(scenes):
            st = sc["start_time"]
            et = sc["end_time"]

            # Sahne öncesi ara başlık kartı süresi (İlk sahne hariç, cinematic modda)
            if idx > 0 and style == "cinematic":
                timeline_cursor += card_duration

            scene_start_in_trailer = timeline_cursor

            # Bu sahneye ait kelimeleri filtrele
            scene_words = [
                w for w in all_words
                if w.get("start", 0) >= st - 0.2 and w.get("end", 0) <= et + 0.2
            ]

            # Dil sürçmelerini, eksik telaffuzları ve kekelemeleri bağlamsal olarak düzelt (zaman damgaları korunur)
            from app.services.speech_corrector import SpeechSlipCorrector
            scene_words = SpeechSlipCorrector.correct_words(scene_words)

            # Mobil ekranda taşmayı önleyen akıllı karakter uzunluğuna duyarlı parçalama (en fazla 24 karakter veya 3 kelime)
            chunks = []
            cur_chunk = []
            cur_len = 0
            for w in scene_words:
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

                emoji_idx = -1
                chunk_emoji = ""
                for c_idx, w in enumerate(chunk):
                    em = get_word_emoji(w.get("word", ""))
                    if em:
                        emoji_idx = c_idx
                        chunk_emoji = em
                        break

                for j, active_w in enumerate(chunk):
                    rel_s = active_w["start"] - st
                    rel_e = active_w["end"] - st

                    if j < len(chunk) - 1:
                        next_rel_s = chunk[j + 1]["start"] - st
                        end_t_val = scene_start_in_trailer + next_rel_s
                    else:
                        end_t_val = scene_start_in_trailer + rel_e

                    start_t = format_time(scene_start_in_trailer + rel_s)
                    end_t = format_time(end_t_val)

                    line_parts = []
                    for k, w in enumerate(chunk):
                        txt = clean_subtitle_word(w.get("word", ""))
                        if k == emoji_idx:
                            txt = f"{txt} {chunk_emoji}"
                        if k == j:
                            line_parts.append(f"{{\\c&H002BF7FF&\\fscx108\\fscy108}}{txt}{{\\r}}")
                        else:
                            line_parts.append(txt)

                    full_line = " ".join(line_parts)
                    events.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{full_line}")

            # Sahne süresini kurgu imlecine ekle
            timeline_cursor += (et - st)

        with open(ass_output_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events) + "\n")

        return len(events) > 0

    # =========================================================================
    # 3. SİNEMATİK BÖLÜM ARA KARTI (FFMPEG & ASS ENGINE - SIFIR BAĞIMLILIK)
    # =========================================================================
    def generate_chapter_card_clip(
        self,
        chapter_title: str,
        act_number: int,
        output_mp4_path: str,
        aspect_ratio: str = "9:16",
        card_duration: float = 1.0
    ) -> None:
        """
        Sahneler arasında gösterilmek üzere FFmpeg ve ASS ile yüksek kaliteli
        sinematik bir bölüm başlığı video parçası (1.0 sn) oluşturur.
        Pillow veya harici kütüphane bağımlılığı gerektirmez.
        """
        w, h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
        card_ass = output_mp4_path.replace(".mp4", ".ass")

        title_text = turkish_upper(chapter_title)
        badge_text = f"◆ BÖLÜM {act_number} ◆"
        badge_margin = 130 if aspect_ratio == "9:16" else 90
        title_font_size = 64 if aspect_ratio == "9:16" else 72

        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CardBadge,DejaVu Sans,34,&H00FFFFFF,&H00FFFFFF,&H00A855F7,&H004F46E5,-1,0,0,0,100,100,2,0,1,3.0,0.0,5,0,0,{badge_margin},1
Style: CardTitle,DejaVu Sans,{title_font_size},&H00FFFFFF,&H00FFFFFF,&H001E1B4B,&H80000000,-1,0,0,0,100,100,1,0,1,6.0,4.0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:{card_duration:05.2f},CardBadge,,0,0,0,,{{\\fad(200,200)\\c&H00F472B6&}}{badge_text}{{\\r}}
Dialogue: 0,0:00:00.00,0:00:{card_duration:05.2f},CardTitle,,0,0,0,,{{\\fad(200,200)}}{title_text}
"""
        with open(card_ass, "w", encoding="utf-8") as f:
            f.write(ass_content)

        escaped_ass = os.path.abspath(card_ass).replace(":", "\\:").replace("\\", "/")
        card_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x070a13:s={w}x{h}:d={card_duration}:r=30",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", f"ass='{escaped_ass}'",
            "-t", str(card_duration),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "192k",
            "-shortest",
            output_mp4_path
        ]
        subprocess.run(card_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(card_ass):
            try:
                os.remove(card_ass)
            except Exception:
                pass

    # =========================================================================
    # 4. FFMPEG KESİM, GEÇİŞ VE BİRLEŞTİRME MOTORU
    # =========================================================================
    def render_cinematic_trailer(
        self,
        video_path: str,
        scenes: List[Dict[str, Any]],
        all_words: List[Dict[str, Any]],
        trailer_id: str,
        aspect_ratio: str = "9:16",
        crop_mode: str = "blur_background",
        style: str = "cinematic",
        progress_callback: Any = None
    ) -> str:
        """
        Seçilen tüm kilit sahneleri keser, ara başlık kartlarını oluşturur,
        video parçalarını birleştirir ve re-timed altyazıyı giydirir.
        """
        output_filename = f"trailer_{trailer_id}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        temp_files_to_clean = []

        card_duration = 1.0 if style == "cinematic" else 0.0

        # Eğer Whisper kelime verisi mevcutsa sınırları kusursuz cümle ve konuşma bitişlerine kenetle
        if all_words:
            scenes = self.snap_scene_boundaries_to_sentences(scenes, all_words, total_duration=999999.0)

        if progress_callback:
            progress_callback(60, "Sahneler kesiliyor ve ara bölümler hazırlanıyor...")

        # 1. Her bir sahneyi kes ve hedef formata çevir
        scene_clip_paths = []
        for idx, sc in enumerate(scenes):
            clip_id = f"t_{trailer_id}_sc_{idx}"
            sc_out = os.path.join(self.temp_dir, f"{clip_id}.mp4")
            temp_files_to_clean.append(sc_out)

            st = sc["start_time"]
            dur = sc["duration"]

            # Ses patlamalarını ve ani kesilmeleri önleyen yumuşak audio fade filtresi ve kusursuz lip-sync
            fade_in_dur = 0.08
            fade_out_dur = 0.18
            fade_out_start = max(0.0, round(dur - fade_out_dur, 2))
            af_filter = f"aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS,afade=t=in:ss=0:d={fade_in_dur},afade=t=out:st={fade_out_start:.2f}:d={fade_out_dur}"

            # Video formatı filtresi (setpts ile PTS sıfırlama)
            if aspect_ratio == "16:9":
                vf = "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1"
            elif crop_mode == "crop_center":
                # 9:16 Tam Ekran Kapla / Ortadan Kırp (Reels gibi sıfır boşluk)
                vf = "setpts=PTS-STARTPTS,scale=-1:1920,crop=1080:1920,setsar=1"
            else:
                # 9:16 Dikey Bulanık Arka Plan
                vf = (
                    "[0:v]setpts=PTS-STARTPTS,scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=7:1,scale=1080:1920[bg];"
                    "[0:v]setpts=PTS-STARTPTS,scale=1080:-2[fg];"
                    "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
                )

            cmd = [
                "ffmpeg", "-y",
                "-threads", "0",
                "-ss", str(st),
                "-i", video_path,
                "-t", str(dur),
                "-avoid_negative_ts", "make_zero",
                "-filter_complex" if "[bg]" in vf else "-vf", vf,
                "-af", af_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "25",
                "-maxrate", "2200k",
                "-bufsize", "4400k",
                "-r", "30",
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                sc_out
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            scene_clip_paths.append(sc_out)

            # Sahneler arası geçiş kartı üret (Son sahne hariç)
            if idx < len(scenes) - 1 and style == "cinematic":
                next_scene = scenes[idx + 1]
                card_mp4 = os.path.join(self.temp_dir, f"card_{trailer_id}_{idx + 1}.mp4")
                temp_files_to_clean.append(card_mp4)

                self.generate_chapter_card_clip(
                    chapter_title=next_scene["chapter_title"],
                    act_number=next_scene["act_number"],
                    output_mp4_path=card_mp4,
                    aspect_ratio=aspect_ratio,
                    card_duration=card_duration
                )
                scene_clip_paths.append(card_mp4)

        if progress_callback:
            progress_callback(80, "Sahneler birleştiriliyor ve altyazı giydiriliyor...")

        # 2. Concat Listesi Oluştur
        concat_txt = os.path.join(self.temp_dir, f"concat_{trailer_id}.txt")
        temp_files_to_clean.append(concat_txt)
        with open(concat_txt, "w", encoding="utf-8") as f:
            for p in scene_clip_paths:
                abs_p = os.path.abspath(p).replace("\\", "/")
                f.write(f"file '{abs_p}'\n")

        merged_raw = os.path.join(self.temp_dir, f"merged_{trailer_id}.mp4")
        temp_files_to_clean.append(merged_raw)

        # 3. Klipleri Tek Parça Halinde Birleştir
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_txt,
            "-c", "copy",
            merged_raw
        ]
        subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        # 4. Altyazıyı Hazırla ve Giydir
        ass_path = os.path.join(self.temp_dir, f"trailer_{trailer_id}.ass")
        temp_files_to_clean.append(ass_path)
        has_subtitles = self.build_trailer_ass_subtitles(
            scenes, all_words, ass_path, aspect_ratio, card_duration, style
        )

        if has_subtitles and os.path.exists(ass_path):
            escaped_ass = os.path.abspath(ass_path).replace(":", "\\:").replace("\\", "/")
            burn_cmd = [
                "ffmpeg", "-y",
                "-i", merged_raw,
                "-vf", f"ass='{escaped_ass}'",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "25",
                "-maxrate", "2200k",
                "-bufsize", "4400k",
                "-c:a", "copy",
                "-movflags", "+faststart",
                output_path
            ]
            try:
                subprocess.run(burn_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except subprocess.CalledProcessError as b_err:
                logger.warning(f"ASS subtitle burning failed: {b_err.stderr.decode('utf-8', errors='ignore')[:300]}. Falling back to clean un-subtitled video...")
                import shutil
                shutil.copyfile(merged_raw, output_path)
        else:
            # Altyazısız doğrudan kopyala
            import shutil
            shutil.copyfile(merged_raw, output_path)

        # 5. Geçici Dosyaları Temizle
        for tf in temp_files_to_clean:
            if os.path.exists(tf):
                try:
                    os.remove(tf)
                except Exception:
                    pass

        if progress_callback:
            progress_callback(100, "Akıllı fragman başarıyla hazırlandı!")

        logger.info(f"Trailer successfully created at: {output_path}")
        return output_path
