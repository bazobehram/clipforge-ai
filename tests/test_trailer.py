import os
import json
import pytest
from app.services.trailer_generator import TrailerGenerator

class TestTrailerGenerator:
    @pytest.fixture
    def generator(self):
        return TrailerGenerator()

    def test_parse_formatted_text_to_segments(self, generator):
        text = (
            "[0.0s - 5.5s]: Merhaba arkadaşlar bugün harika bir proje yapıyoruz.\n"
            "[6.0s - 12.3s]: ESP32 devremizi kurup sensörleri taktık.\n"
            "[13.0s - 20.0s]: Sistem başarıyla çalışmaya başladı."
        )
        segments = generator.parse_formatted_text_to_segments(text)
        assert len(segments) == 3
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 5.5
        assert "Merhaba" in segments[0]["text"]
        assert segments[1]["start"] == 6.0
        assert "ESP32" in segments[1]["text"]

    def test_group_words_to_segments(self, generator):
        words = [
            {"word": "Merhaba", "start": 0.0, "end": 0.5},
            {"word": "dünya.", "start": 0.6, "end": 1.0},
            {"word": "İkinci", "start": 1.2, "end": 1.8},
            {"word": "cümle.", "start": 1.9, "end": 2.5},
        ]
        segments = generator.group_words_to_segments(words, target_chunk_sec=2.0)
        assert len(segments) >= 1
        assert "Merhaba dünya." in segments[0]["text"]

    def test_select_scenes_heuristic_creates_chronological_acts(self, generator):
        # 1800 saniyelik (30 dk) bir video simülasyonu
        segments = [
            {"start": float(i * 30), "end": float(i * 30 + 15), "text": f"Bu {i}. bölümdeki önemli bir detay ve aşama."}
            for i in range(60)
        ]
        total_duration = 1800.0
        target_duration = 60
        video_title = "Evimizde Akıllı Çiçek Odası Kurduk | ESP32, Sensörler, Android Kamera ve Yapay Zekâ"

        scenes, meta_info = generator._select_scenes_heuristic(
            segments=segments,
            total_duration=total_duration,
            target_duration=target_duration,
            video_title=video_title
        )

        # Doğrulamalar
        assert len(scenes) >= 3
        assert len(scenes) <= 6
        # Kronolojik sıra doğrulaması
        for i in range(len(scenes) - 1):
            assert scenes[i]["start_time"] < scenes[i + 1]["start_time"]

        # Meta veri doğrulamaları
        assert meta_info["trailer_title"] == "Evimizde Akıllı Çiçek Odası Kurduk"
        assert len(meta_info["hashtags"]) >= 4
        assert "#esp32" in meta_info["hashtags"]
        assert meta_info["description"].endswith("👇")

    def test_select_scenes_heuristic_scales_with_target_duration(self, generator):
        segments = [
            {"start": float(i * 20), "end": float(i * 20 + 10), "text": f"Bölüm {i} anlatımı ve sonuçları."}
            for i in range(50)
        ]
        total_duration = 1000.0

        # 30 saniyelik teaser
        scenes_30, _ = generator._select_scenes_heuristic(segments, total_duration, 30, "Test Video")
        # 180 saniyelik detaylı özet
        scenes_180, _ = generator._select_scenes_heuristic(segments, total_duration, 180, "Test Video")

        assert len(scenes_30) <= 4
        assert len(scenes_180) >= 5
        assert len(scenes_180) > len(scenes_30)

    def test_trailer_metadata_persistence(self, generator, tmp_path):
        # Geçici trailers_dir kullan
        orig_dir = generator.trailers_dir
        generator.trailers_dir = str(tmp_path)
        try:
            tid = "test1234"
            sample_data = {
                "trailer_id": tid,
                "video_title": "Test Fragman",
                "status": "completed",
                "trailer_duration": 62.5
            }
            generator.save_trailer_metadata(tid, sample_data)

            loaded = generator.get_trailer_metadata(tid)
            assert loaded is not None
            assert loaded["trailer_id"] == tid
            assert loaded["video_title"] == "Test Fragman"
            assert loaded["trailer_duration"] == 62.5

            # Silme testi
            deleted = generator.delete_trailer(tid)
            assert deleted is True
            assert generator.get_trailer_metadata(tid) is None
        finally:
            generator.trailers_dir = orig_dir

    def test_trailer_metadata_enriches_from_project(self, generator, tmp_path):
        from app.config import settings
        orig_trailers = generator.trailers_dir
        orig_downloads = settings.DOWNLOADS_DIR
        generator.trailers_dir = str(tmp_path / "trailers")
        os.makedirs(generator.trailers_dir, exist_ok=True)
        settings.DOWNLOADS_DIR = str(tmp_path / "downloads")
        os.makedirs(settings.DOWNLOADS_DIR, exist_ok=True)

        try:
            pid = "proj_test_1"
            proj_dir = os.path.join(settings.DOWNLOADS_DIR, pid)
            os.makedirs(proj_dir, exist_ok=True)
            with open(os.path.join(proj_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "title": "Orijinal YouTube Videosu Başlığı",
                    "thumbnail": "https://i.ytimg.com/vi/abc/default.jpg",
                    "youtube_url": "https://www.youtube.com/watch?v=abc"
                }, f)

            tid = "tr_enrich_1"
            generator.save_trailer_metadata(tid, {
                "trailer_id": tid,
                "project_id": pid,
                "trailer_title": "AI Vurucu Başlık",
                "description": "Özet metni burada. 👇. 👇",
                "status": "completed"
            })

            meta = generator.get_trailer_metadata(tid)
            assert meta is not None
            assert meta["original_title"] == "Orijinal YouTube Videosu Başlığı"
            assert meta["thumbnail"] == "https://i.ytimg.com/vi/abc/default.jpg"
            assert meta["youtube_url"] == "https://www.youtube.com/watch?v=abc"
            # Ensure duplicate 👇. 👇 was cleaned and youtube link appended
            assert "👇. 👇" not in meta["description"]
            assert "🎬 Videonun tamamı: https://www.youtube.com/watch?v=abc" in meta["description"]
        finally:
            generator.trailers_dir = orig_trailers
            settings.DOWNLOADS_DIR = orig_downloads

    def test_snap_scene_boundaries_fixes_dangling_ends(self, generator):
        words = [
            {"word": "Bu", "start": 0.0, "end": 0.4},
            {"word": "yapay", "start": 0.5, "end": 0.9},
            {"word": "zeka", "start": 1.0, "end": 1.5},
            {"word": "mimarisidir.", "start": 1.6, "end": 2.2},
            {"word": "Yani", "start": 2.4, "end": 2.8},
            {"word": "zeka", "start": 3.0, "end": 3.4},
            {"word": "üretmek", "start": 3.5, "end": 4.0},
            {"word": "için", "start": 4.1, "end": 4.5},
            {"word": "yapılmış", "start": 4.6, "end": 5.2},
            {"word": "değil.", "start": 5.3, "end": 5.8},
        ]
        # Raw scene cuts right at 'Yani' (2.8s)
        scenes = [{
            "act_number": 1,
            "chapter_title": "1. BÖLÜM",
            "start_time": 0.0,
            "end_time": 2.8,
            "duration": 2.8
        }]

        snapped = generator.snap_scene_boundaries_to_sentences(scenes, words, total_duration=10.0)
        assert len(snapped) == 1
        # It must NOT end on 'Yani' (2.8s); it must extend to 'değil.' (around 5.9s)
        assert snapped[0]["end_time"] >= 5.8
        assert snapped[0]["duration"] > 5.0

    def test_snap_scene_boundaries_fixes_filler_starts(self, generator):
        words = [
            {"word": "görüşlerimi", "start": 70.0, "end": 71.0},
            {"word": "söyledim.", "start": 71.1, "end": 71.8},
            {"word": "He", "start": 74.0, "end": 74.4},
            {"word": "gibi", "start": 74.5, "end": 74.8},
            {"word": "Lego", "start": 75.0, "end": 75.5},
            {"word": "gibi", "start": 75.6, "end": 76.0},
            {"word": "düşün.", "start": 76.1, "end": 76.8},
        ]
        # Raw scene starts at 74.0s right at filler 'He'
        scenes = [{
            "act_number": 1,
            "chapter_title": "1. BÖLÜM",
            "start_time": 74.0,
            "end_time": 77.0,
            "duration": 3.0
        }]

        snapped = generator.snap_scene_boundaries_to_sentences(scenes, words, total_duration=100.0)
        assert len(snapped) == 1
        # It should skip filler 'He' and snap to 'Lego' (>= 74.9s)
        assert snapped[0]["start_time"] >= 74.9

    def test_snap_scene_boundaries_prevents_overlap(self, generator):
        words = [
            {"word": "Birinci", "start": 0.0, "end": 0.5},
            {"word": "cümle.", "start": 0.6, "end": 1.2},
            {"word": "İkinci", "start": 1.5, "end": 2.0},
            {"word": "cümle.", "start": 2.1, "end": 2.8},
            {"word": "Üçüncü", "start": 3.0, "end": 3.5},
            {"word": "cümle.", "start": 3.6, "end": 4.2},
        ]
        scenes = [
            {"act_number": 1, "chapter_title": "1", "start_time": 0.0, "end_time": 2.5, "duration": 2.5},
            {"act_number": 2, "chapter_title": "2", "start_time": 2.2, "end_time": 4.2, "duration": 2.0}
        ]

        snapped = generator.snap_scene_boundaries_to_sentences(scenes, words, total_duration=10.0)
        assert len(snapped) == 2
        # First scene end must not be greater than or equal to second scene start
        assert snapped[0]["end_time"] < snapped[1]["start_time"]

    def test_snap_scene_boundaries_missing_punctuation_uses_pause(self, generator):
        # Transkriptte HİÇ nokta veya soru işareti yok, ancak 15.0s ve 15.8s arasında 0.8s sessizlik/duraksama var
        words = [
            {"word": "arkadaşlar", "start": 0.0, "end": 0.8},
            {"word": "burada", "start": 0.9, "end": 1.5},
            {"word": "bir", "start": 1.6, "end": 2.0},
            {"word": "konuşma", "start": 2.1, "end": 3.0},
            {"word": "yapıyoruz", "start": 3.1, "end": 15.0}, # 15.0'da duruyor
            # 0.8 saniyelik doğal nefes arası
            {"word": "sonrasında", "start": 15.8, "end": 16.5},
            {"word": "diğer", "start": 16.6, "end": 17.2},
            {"word": "konuya", "start": 17.3, "end": 18.0},
        ]
        scenes = [{
            "act_number": 1,
            "chapter_title": "1",
            "start_time": 0.0,
            "end_time": 14.5,
            "duration": 14.5
        }]

        snapped = generator.snap_scene_boundaries_to_sentences(scenes, words, total_duration=30.0)
        assert len(snapped) == 1
        # Noktalama olmasa bile 15.0s'deki nefes arasına kenetlenmeli, 15.8s sonrasına taşmamalı
        assert snapped[0]["end_time"] <= 15.3

    def test_snap_scene_boundaries_clamps_max_duration(self, generator):
        # 60 saniye boyunca hiç durmadan konuşulan aralıksız transkript
        words = [
            {"word": f"kelime{i}", "start": float(i), "end": float(i + 0.8)}
            for i in range(60)
        ]
        # Bitişte nokta var
        words[-1]["word"] = "son."

        scenes = [{
            "act_number": 1,
            "chapter_title": "1",
            "start_time": 0.0,
            "end_time": 20.0,
            "duration": 20.0
        }]

        snapped = generator.snap_scene_boundaries_to_sentences(scenes, words, total_duration=100.0)
        assert len(snapped) == 1
        # 42 saniyeden uzun bir sahneye kontrolsüz genişlememeli
        assert snapped[0]["duration"] <= 42.0

    def test_snap_scene_boundaries_allows_60s_and_70s_duration(self, generator):
        # 100 saniyelik transkript
        words = [
            {"word": f"kelime{i}", "start": float(i), "end": float(i + 0.8)}
            for i in range(100)
        ]
        words[59]["word"] = "bitti."
        words[69]["word"] = "tamamlandı."

        # Kullanıcı 60 saniyelik klip istediğinde 40s'ye düşürülmemeli
        scenes_60 = [{
            "act_number": 1,
            "chapter_title": "1",
            "start_time": 0.0,
            "end_time": 60.0,
            "duration": 60.0
        }]
        snapped_60 = generator.snap_scene_boundaries_to_sentences(scenes_60, words, total_duration=100.0)
        assert len(snapped_60) == 1
        assert snapped_60[0]["duration"] >= 58.0
        assert snapped_60[0]["duration"] <= 65.0

        # Kullanıcı 70 saniyelik klip istediğinde 40s'ye düşürülmemeli
        scenes_70 = [{
            "act_number": 1,
            "chapter_title": "1",
            "start_time": 0.0,
            "end_time": 70.0,
            "duration": 70.0
        }]
        snapped_70 = generator.snap_scene_boundaries_to_sentences(scenes_70, words, total_duration=100.0)
        assert len(snapped_70) == 1
        assert snapped_70[0]["duration"] >= 68.0
        assert snapped_70[0]["duration"] <= 75.0

    def test_build_trailer_ass_subtitles_character_aware_chunking(self, generator, tmp_path):
        ass_path = str(tmp_path / "test_sub.ass")
        scenes = [{"start_time": 0.0, "end_time": 10.0}]
        # Uzun Türkçe kelimeler
        words = [
            {"word": "gerçekleştirilemeyebileceğinden", "start": 0.0, "end": 2.0},
            {"word": "bahsediyorlardı", "start": 2.1, "end": 4.0},
            {"word": "çünkü", "start": 4.1, "end": 5.0},
            {"word": "sistem", "start": 5.1, "end": 6.0},
        ]
        has_sub = generator.build_trailer_ass_subtitles(scenes, words, ass_path, aspect_ratio="9:16")
        assert has_sub is True
        assert os.path.exists(ass_path)
        content = open(ass_path, encoding="utf-8").read()
        assert "Dialogue:" in content



