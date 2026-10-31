import pytest
from app.services.scorer import ContentScorer

class TestContentScorerTextCleaning:
    def test_clean_title_removes_trailing_conjunctions(self):
        titles = [
            ("Yapay Zeka Dünyayı Değiştiriyor ve", "Yapay Zeka Dünyayı Değiştiriyor"),
            ("Yeni Nesil Teknolojiler ile", "Yeni Nesil Teknolojiler"),
            ("Geleceğe Hazır mısınız çünkü", "Geleceğe Hazır mısınız"),
            ("Yazılımcı Olmak İsteyenler İçin ama", "Yazılımcı Olmak İsteyenler İçin"),
            ("Bu Proje Nasıl Çalışır ki", "Bu Proje Nasıl Çalışır")
        ]
        for inp, expected in titles:
            cleaned = ContentScorer.clean_title(inp)
            assert cleaned == expected

    def test_clean_title_removes_leading_conjunctions(self):
        titles = [
            ("Bence en iyi yazılım dili Python", "En iyi yazılım dili Python"),
            ("Aslında her şey çok farklıydı", "Her şey çok farklıydı"),
            ("Yani bu sistemi kurmak zor değil", "Bu sistemi kurmak zor değil"),
            ("Çünkü başarı disiplin gerektirir", "Başarı disiplin gerektirir")
        ]
        for inp, expected in titles:
            cleaned = ContentScorer.clean_title(inp)
            assert cleaned == expected

    def test_clean_title_strips_quotes_and_ellipses(self):
        titles = [
            ('"Evde Akıllı Oda Kurduk!"', "Evde Akıllı Oda Kurduk!"),
            ('“ESP32 ile Otomasyon”', "ESP32 ile Otomasyon"),
            ('Geleceğin Teknolojisi...', "Geleceğin Teknolojisi"),
            ('Büyük Dönüm Noktası ---', "Büyük Dönüm Noktası"),
            ('Yapay Zeka ve Gelecek |', "Yapay Zeka ve Gelecek")
        ]
        for inp, expected in titles:
            cleaned = ContentScorer.clean_title(inp)
            assert cleaned == expected

    def test_clean_title_extracts_hook_from_youtube_pipe_title(self):
        long_yt_title = "Evimizde Akıllı Çiçek Odası Kurduk | ESP32, Sensörler, Android Kamera ve Yapay Zekâ"
        cleaned = ContentScorer.clean_title(long_yt_title)
        assert cleaned == "Evimizde Akıllı Çiçek Odası Kurduk"

    def test_clean_title_fallback_on_empty_or_short(self):
        cleaned = ContentScorer.clean_title("", video_title="Ana Video Başlığı")
        assert cleaned == "Ana Video Başlığı"

    def test_clean_description_removes_artificial_hooks(self):
        desc = (
            "ESP32 sensörleri ile odadaki nem ve sıcaklığı anlık takip ettik. "
            "Videoyu beğenmeyi ve kanala abone olmayı unutmayın! Takipte kalın. "
            "Siz bu konuda ne düşünüyorsunuz?"
        )
        cleaned = ContentScorer.clean_description(desc)
        assert "beğenmeyi" not in cleaned
        assert "abone" not in cleaned
        assert "takipte kalın" not in cleaned
        assert "ne düşünüyorsunuz" not in cleaned
        assert cleaned.startswith("ESP32 sensörleri")
        assert "takip ettik" in cleaned  # Gerçek cümlenin bozulmadığını doğrula
        assert cleaned.endswith(".")

    def test_clean_description_removes_trailer_boilerplate(self):
        desc = "Yapay zeka ile oluşturulan akıllı video özeti! ESP32 projemizin tüm adımları."
        cleaned = ContentScorer.clean_description(desc)
        assert "akıllı video özeti" not in cleaned
        assert "ESP32 projemizin tüm adımları." in cleaned

    def test_clean_description_ensures_terminal_punctuation(self):
        desc = "Bu videoda donanım ve yazılım aşamalarını adım adım ele alıyoruz"
        cleaned = ContentScorer.clean_description(desc)
        assert cleaned.endswith(".")


class TestSmartHashtags:
    def test_smart_hashtags_hardware_and_iot(self):
        title = "Evimizde Akıllı Çiçek Odası Kurduk | ESP32, Sensörler, Android Kamera ve Yapay Zekâ"
        snippet = "esp32 mikrodenetleyici ve dht22 sıcaklık sensörü ile sistemi bağladık"
        tags = ContentScorer.generate_smart_hashtags(title, snippet)

        assert "#esp32" in tags
        assert "#iot" in tags or "#elektronik" in tags
        assert "#yapayzeka" in tags or "#ai" in tags
        assert len(tags) <= 8
        assert len(set(tags)) == len(tags)  # Benzersiz olmalı
        assert "#ClipForge" not in tags
        assert "#Fragman" not in tags

    def test_smart_hashtags_software_and_ai(self):
        title = "Python ile Sıfırdan Yapay Zeka Modeli Eğitimi (LLM & ChatGPT)"
        tags = ContentScorer.generate_smart_hashtags(title)

        assert "#yazilim" in tags or "#kodlama" in tags
        assert "#yapayzeka" in tags or "#ai" in tags
        assert len(tags) <= 8

    def test_smart_hashtags_finance(self):
        title = "Borsa ve Kripto Para ile Pasif Gelir Elde Etme Yolları"
        tags = ContentScorer.generate_smart_hashtags(title)

        assert "#para" in tags or "#finans" in tags or "#yatirim" in tags

    def test_smart_hashtags_includes_short_tech_terms(self):
        title = "Yeni AI Araçları ile Web Geliştirme ve IoT"
        tags = ContentScorer.generate_smart_hashtags(title)

        # ai ve iot 2-3 harfli ama teknoloji kısaltması olarak kabul edilmeli
        assert any(t in tags for t in ["#ai", "#iot", "#teknoloji", "#yapayzeka"])

    def test_smart_hashtags_filters_stop_words_and_digits(self):
        title = "2026 Yılında Bu ve Şu Nasıl Yapılır Diye Sorduk"
        tags = ContentScorer.generate_smart_hashtags(title)

        assert "#2026" not in tags
        assert "#ve" not in tags
        assert "#bu" not in tags
        assert "#nasil" not in tags
        assert "#nasıl" not in tags

class TestContentScorerCandidateProgression:
    def test_get_transcript_window_short_returns_all(self):
        text = "[0.0s - 10.0s]: Kısa transkript metni."
        window = ContentScorer.get_transcript_window(text, offset=0, max_chars=1000)
        assert window == text

    def test_get_transcript_window_advances_past_existing_candidates(self):
        # 100 satırlık uzun transkript simülasyonu
        lines = [f"[{i * 10}.0s - {i * 10 + 9}.5s]: Bu {i}. cümlenin içeriğidir ve detaylı açıklamadır." for i in range(100)]
        long_transcript = "\n".join(lines)

        # İlk adaylar 0-250s arasını kapsıyor olsun
        existing = [
            {"start_time": 10.0, "end_time": 60.0, "title": "Bölüm 1"},
            {"start_time": 80.0, "end_time": 150.0, "title": "Bölüm 2"},
            {"start_time": 160.0, "end_time": 250.0, "title": "Bölüm 3"}
        ]

        window = ContentScorer.get_transcript_window(long_transcript, offset=3, existing_candidates=existing, max_chars=1500)
        # Pencere 240-250s civarından başlamalı, 0. saniyeden başlamamalı
        assert "[0.0s -" not in window
        assert "[10.0s -" not in window
        assert any(f"[{s}.0s" in window for s in [240, 250, 260, 270])

    def test_is_overlapping_or_duplicate_detects_overlap(self):
        existing = [
            {"start_time": 50.0, "end_time": 100.0, "title": "Mevcut Klip"}
        ]

        # 1. Birebir aynı aralık
        cand_dup = {"start_time": 51.0, "end_time": 99.0, "title": "Yeni Klip"}
        assert ContentScorer.is_overlapping_or_duplicate(cand_dup, existing) is True

        # 2. Belirgin (%50+) çakışan aralık
        cand_overlap = {"start_time": 75.0, "end_time": 130.0, "title": "Çakışan Klip"}
        assert ContentScorer.is_overlapping_or_duplicate(cand_overlap, existing) is True

        # 3. Bağımsız, çakışmayan aralık
        cand_clean = {"start_time": 150.0, "end_time": 200.0, "title": "Temiz Klip"}
        assert ContentScorer.is_overlapping_or_duplicate(cand_clean, existing) is False

    def test_fallback_clips_avoids_existing_candidates(self):
        scorer = ContentScorer()
        lines = [f"[{i * 10}.0s - {i * 10 + 9}.0s]: Konuşma satırı {i}." for i in range(120)]
        transcript = "\n".join(lines)

        existing = [
            {"start_time": 10.0, "end_time": 80.0, "title": "İlk Klip"}
        ]

        # 3 adet fallback klip iste
        clips = scorer._fallback_clips(
            video_duration=1200.0,
            count=3,
            video_title="Test Video",
            formatted_transcript=transcript,
            offset=1,
            existing_candidates=existing
        )

        assert len(clips) == 3
        for c in clips:
            # Hiçbiri ilk adayın [10s - 80s] aralığıyla çakışmamalı
            assert not (c["start_time"] < 80.0 and c["end_time"] > 10.0)

