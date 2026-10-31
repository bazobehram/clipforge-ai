import re
import copy
from typing import List, Dict, Any, Optional

class SpeechSlipCorrector:
    """
    Konuşmacının dil sürçmelerini, eksik harf yutmalarını, kekelemeleri ve 
    akustik deşifre hatalarını bağlamsal olarak düzelten motor.
    
    Örnekler:
    - 'uşun' -> 'kuşun' (bağlamda 'uçup', 'uçmadığını', 'kuş' vb. varsa)
    - 'satran' -> 'satranç'
    - 'üstürürse' -> 'üstlenirse'
    - 'bi' -> 'bir'
    - 'herkez' -> 'herkes'
    - 'yanlız' -> 'yalnız'
    - 'farketmek' -> 'fark etmek'
    - 'ko-konuşacağız' -> 'konuşacağız'
    
    Tüm düzeltmelerde Whisper'ın 'start' ve 'end' zaman damgaları KESİNLİKLE korunur.
    """

    TR_UPPER_MAP = {'i': 'İ', 'ı': 'I', 'ğ': 'Ğ', 'ü': 'Ü', 'ş': 'Ş', 'ö': 'Ö', 'ç': 'Ç'}
    TR_LOWER_MAP = {'İ': 'i', 'I': 'ı', 'Ğ': 'ğ', 'Ü': 'ü', 'Ş': 'ş', 'Ö': 'ö', 'Ç': 'ç'}

    @classmethod
    def tr_upper(cls, text: str) -> str:
        return "".join(cls.TR_UPPER_MAP.get(ch, ch.upper()) for ch in text)

    @classmethod
    def tr_lower(cls, text: str) -> str:
        return "".join(cls.TR_LOWER_MAP.get(ch, ch.lower()) for ch in text)

    # Doğrudan / bağımsız düzeltme sözlüğü (Konuşma dili & yaygın sürçmeler)
    DIRECT_REPLACEMENTS = {
        "satran": "satranç",
        "üstürürse": "üstlenirse",
        "herkez": "herkes",
        "herkezin": "herkesin",
        "herkeze": "herkese",
        "herkezden": "herkesten",
        "yanlız": "yalnız",
        "yanlızım": "yalnızım",
        "yanlızlık": "yalnızlık",
        "farketmek": "fark etmek",
        "farketmez": "fark etmez",
        "farketti": "fark etti",
        "farkettim": "fark ettim",
        "terketmek": "terk etmek",
        "terketti": "terk etti",
        "tabiki": "tabii ki",
        "tabikide": "tabii ki de",
        "eşşek": "eşek",
        "traş": "tıraş",
        "klavuz": "kılavuz",
        "matamatik": "matematik",
        "proğram": "program",
        "proğramlama": "programlama",
        "algortima": "algoritma",
        "algortiması": "algoritması",
        "bilgisyar": "bilgisayar",
        "bilgisyarın": "bilgisayarın",
        "orjinal": "orijinal",
        "orjinallik": "orijinallik",
        "dinazor": "dinozor",
        "döküman": "doküman",
        "dökümantasyon": "dokümantasyon",
        "labaratuvar": "laboratuvar",
        "labratuar": "laboratuvar",
        "karekter": "karakter",
        "entellektüel": "entelektüel",
        "kolektif": "kolektif",
        "komplike": "komplike",
        "fotoraf": "fotoğraf",
        "fotoraflar": "fotoğraflar",
        "süpriz": "sürpriz",
        "yanılsama": "yanılsama",
        "halisünasyon": "halüsinasyon",
        "halusinasyon": "halüsinasyon",
        "halisinasyon": "halüsinasyon",
        "herşey": "her şey",
        "birşey": "bir şey",
        "hiçbirşey": "hiçbir şey",
        "yanısıra": "yanı sıra",
        "yada": "ya da",
        "malesef": "maalesef",
        "makina": "makine",
        "hoperlör": "hoparlör",
        "şarz": "şarj",
        "egzos": "egzoz",
        "egsoz": "egzoz",
        "ünvan": "unvan",
        "ahçı": "aşçı",
        "yanıca": "yalnızca",
        "eriştire": "eleştirel",
        "eriştirel": "eleştirel"
    }

    # Bağlamsal sürçme kalıpları (Contextual Triggers):
    # Bir kelime belirli bir bağlamda veya komşu kelimelerle geçtiğinde düzeltilir
    CONTEXTUAL_RULES = [
        # uşun / kuşun uçup uçmadığını
        {
            "targets": {"uşun", "uş", "uşlar", "uşu"},
            "context_keywords": {"uç", "uçup", "uçmadığını", "uçtuğunu", "kanat", "uçmak", "tüy", "kuş", "gökyüzü", "hava", "uçak"},
            "replacement": "kuşun",
            "replacement_map": {
                "uş": "kuş",
                "uşun": "kuşun",
                "uşu": "kuşu",
                "uşlar": "kuşlar"
            }
        },
        # yapay zeka / yz kısaltması veya deşifre bozulması
        {
            "targets": {"yz", "yz'nin", "yz'ye", "yz'yi", "yz'de"},
            "context_keywords": {"yapay", "zeka", "model", "llm", "algoritma", "derin", "öğrenme", "kod"},
            "replacement": "yapay zeka",
            "replacement_map": {
                "yz": "yapay zeka",
                "yz'nin": "yapay zekanın",
                "yz'ye": "yapay zekaya",
                "yz'yi": "yapay zekayı",
                "yz'de": "yapay zekada"
            }
        },
        # derin öğrenme / derin düşünme
        {
            "targets": {"öğrenm", "ögrenme"},
            "context_keywords": {"derin", "makine", "yapay", "zeka", "model"},
            "replacement": "öğrenme"
        }
    ]

    @classmethod
    def clean_stutter(cls, word: str) -> str:
        """
        Kekeleme veya duraksama hece tekrarlarını temizler:
        'ko-konuşacağız' -> 'konuşacağız'
        'ya-yapay' -> 'yapay'
        'b-bence' -> 'bence'
        """
        if not word:
            return word

        match_punct = re.match(r'^([^a-zA-Z0-9çÇğĞıİöÖşŞüÜ]*)(.*?)([^a-zA-Z0-9çÇğĞıİöÖşŞüÜ]*)$', word)
        lead, core, trail = match_punct.groups() if match_punct else ("", word, "")

        match = re.match(r'^([a-zA-ZçÇğĞıİöÖşŞüÜ]{1,3})-+([a-zA-ZçÇğĞıİöÖşŞüÜ]{2,})$', core)
        if match:
            prefix, rest = match.groups()
            if cls.tr_lower(rest).startswith(cls.tr_lower(prefix)) or len(prefix) == 1:
                return f"{lead}{rest}{trail}"
        return word

    @classmethod
    def preserve_case_and_punctuation(cls, original: str, corrected: str) -> str:
        """
        Orijinal kelimedeki büyük/küçük harf durumunu ve noktalama işaretlerini korur.
        Örn: 'Uşun,' -> 'Kuşun,' veya 'SATRAN!' -> 'SATRANÇ!'
        """
        if not original or not corrected:
            return corrected or original

        # Başındaki ve sonundaki noktalama işaretlerini ayır
        match_punct = re.match(r'^([^a-zA-Z0-9çÇğĞıİöÖşŞüÜ]*)(.*?)([^a-zA-Z0-9çÇğĞıİöÖşŞüÜ]*)$', original)
        lead_punct, core, trail_punct = match_punct.groups() if match_punct else ("", original, "")

        # Büyük harf düzeni
        if core.isupper() and len(core) > 1:
            corrected = cls.tr_upper(corrected)
        elif core and core[0].isupper():
            corrected = cls.tr_upper(corrected[:1]) + cls.tr_lower(corrected[1:])
        elif core.islower():
            corrected = cls.tr_lower(corrected)

        return f"{lead_punct}{corrected}{trail_punct}"

    @classmethod
    def correct_words(cls, words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Kelime listesindeki dil sürçmelerini bağlama göre düzeltir.
        Her kelimenin 'start' ve 'end' zaman damgalarını birebir muhafaza eder.
        """
        if not words:
            return []

        cleaned_words = [copy.copy(w) for w in words]
        n = len(cleaned_words)

        # Tüm kelimelerin çekirdek (noktalamasız, küçük harfli) hallerini çıkar
        cores = []
        for w in cleaned_words:
            raw = str(w.get("word", "")).strip()
            # Kekelemeyi temizle
            raw = cls.clean_stutter(raw)
            core = cls.tr_lower(re.sub(r'[^a-zA-ZçÇğĞıİöÖşŞüÜ]', '', raw))
            cores.append(core)

        # Kelimeleri tek tek ve komşu bağlamlarıyla incele
        for idx in range(n):
            w = cleaned_words[idx]
            raw_word = str(w.get("word", "")).strip()
            raw_word = cls.clean_stutter(raw_word)
            core = cores[idx]

            if not core:
                w["word"] = raw_word
                continue

            replacement = None

            # 1. Doğrudan Değiştirme (Sözlük eşleşmesi)
            if core in cls.DIRECT_REPLACEMENTS:
                replacement = cls.DIRECT_REPLACEMENTS[core]

            # 2. Bağlamsal Kurallar (Örn: uşun -> kuşun)
            if not replacement:
                # ±8 kelimelik pencere bağlamını topla
                ctx_start = max(0, idx - 8)
                ctx_end = min(n, idx + 9)
                window_cores = set(cores[ctx_start:ctx_end])

                for rule in cls.CONTEXTUAL_RULES:
                    if core in rule["targets"]:
                        # Eğer bağlamdaki anahtar kelimelerden en az biri pencerede varsa
                        if window_cores.intersection(rule["context_keywords"]):
                            rep_map = rule.get("replacement_map")
                            if rep_map and core in rep_map:
                                replacement = rep_map[core]
                            else:
                                replacement = rule["replacement"]
                            break

            # 3. Eğer düzeltme bulunduysa orijinal noktalama ve harf boyutunu koruyarak ata
            if replacement:
                w["word"] = cls.preserve_case_and_punctuation(raw_word, replacement)
            else:
                w["word"] = raw_word

        return cleaned_words
