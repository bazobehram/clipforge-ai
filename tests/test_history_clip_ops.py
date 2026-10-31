import os
import json
import pytest
from app.services.history_manager import HistoryManager
from app.config import settings

@pytest.fixture
def temp_history(tmp_path, monkeypatch):
    test_history_file = tmp_path / "history.json"
    monkeypatch.setattr(settings, "HISTORY_FILE", str(test_history_file))
    monkeypatch.setattr(settings, "OUTPUT_DIR", str(tmp_path))
    hm = HistoryManager()
    return hm, str(test_history_file), tmp_path

def test_delete_clip_type_insensitive(temp_history):
    hm, hist_file, out_dir = temp_history
    
    # Proje verisi: ID'ler int 0 ve 1
    dummy_video_path = os.path.join(out_dir, "clip_0.mp4")
    with open(dummy_video_path, "w") as f:
        f.write("fake video data")
        
    project = {
        "project_id": "proj_123",
        "title": "Test Video",
        "duration": 120.0,
        "candidates": [
            {"id": 0, "start_time": 10.0, "end_time": 70.0, "duration": 60.0, "is_rendered": True, "video_filename": "clip_0.mp4"},
            {"id": 1, "start_time": 80.0, "end_time": 110.0, "duration": 30.0, "is_rendered": False}
        ],
        "rendered_clips": [
            {"id": 0, "start_time": 10.0, "end_time": 70.0, "duration": 60.0, "video_filename": "clip_0.mp4"}
        ]
    }
    hm.save_project(project)
    
    # String "0" ile silmeyi dene (FastAPI'den gelen durum)
    res = hm.delete_clip("proj_123", "0")
    assert res is True
    
    # Dosya silinmiş mi?
    assert not os.path.exists(dummy_video_path)
    
    # Projeyi kontrol et
    p = hm.get_project("proj_123")
    assert len(p["rendered_clips"]) == 0
    assert p["candidates"][0]["is_rendered"] is False
    assert p["candidates"][0]["video_filename"] is None

def test_add_rendered_clip_updates_existing_and_cleans_old_file(temp_history):
    hm, hist_file, out_dir = temp_history

    old_vid = os.path.join(out_dir, "clip_0_old.mp4")
    with open(old_vid, "w") as f:
        f.write("old video")

    project = {
        "project_id": "proj_456",
        "title": "Test Video 2",
        "duration": 150.0,
        "candidates": [
            {"id": 0, "start_time": 10.0, "end_time": 70.0, "duration": 60.0, "is_rendered": True, "video_filename": "clip_0_old.mp4"}
        ],
        "rendered_clips": [
            {"id": 0, "start_time": 10.0, "end_time": 70.0, "duration": 60.0, "video_filename": "clip_0_old.mp4"}
        ]
    }
    hm.save_project(project)

    # 70s ile re-render edilmiş klip ekle (ID: str "0", yeni filename)
    new_clip = {
        "id": "0",
        "start_time": 10.0,
        "end_time": 80.0,
        "duration": 70.0,
        "video_filename": "clip_0_new.mp4",
        "video_url": "/api/clips/clip_0_new.mp4?v=12345"
    }
    hm.add_rendered_clip("proj_456", new_clip)

    # Eski dosya diskten silinmiş olmalı
    assert not os.path.exists(old_vid)

    p = hm.get_project("proj_456")
    # rendered_clips boyutu 1 olmalı (duplicate oluşmamalı)
    assert len(p["rendered_clips"]) == 1
    assert p["rendered_clips"][0]["duration"] == 70.0
    assert p["rendered_clips"][0]["video_filename"] == "clip_0_new.mp4"
    assert p["candidates"][0]["duration"] == 70.0
    assert p["candidates"][0]["is_rendered"] is True

def test_delete_clip_with_composite_id_or_suffix(temp_history):
    hm, hist_file, out_dir = temp_history

    fake_file = os.path.join(out_dir, "clip_07668f34_8.mp4")
    with open(fake_file, "w") as f:
        f.write("fake video")

    project = {
        "project_id": "07668f34",
        "title": "Composite ID Project",
        "duration": 300.0,
        "candidates": [
            {
                "id": "07668f34_8",
                "start_time": 120.0,
                "end_time": 180.0,
                "duration": 60.0,
                "is_rendered": True,
                "video_filename": "clip_07668f34_8.mp4"
            }
        ],
        "rendered_clips": [
            {
                "id": "07668f34_8",
                "start_time": 120.0,
                "end_time": 180.0,
                "duration": 60.0,
                "video_filename": "clip_07668f34_8.mp4"
            }
        ]
    }
    hm.save_project(project)

    # 1. Kullanıcı basit indeks "8" ile silme isteği yollasa bile "07668f34_8" eşleşmeli ve silinmeli
    res = hm.delete_clip("07668f34", "8")
    assert res is True
    assert not os.path.exists(fake_file)

    p = hm.get_project("07668f34")
    assert len(p["rendered_clips"]) == 0
    assert p["candidates"][0]["is_rendered"] is False
    assert p["candidates"][0]["video_filename"] is None

def test_deduplicate_project_candidates(temp_history):
    hm, hist_file, out_dir = temp_history

    project = {
        "project_id": "proj_dup",
        "title": "Duplicate Candidates Test",
        "duration": 500.0,
        "candidates": [
            {"id": "c1", "start_time": 10.0, "end_time": 60.0, "duration": 50.0, "is_rendered": False, "title": "Bölüm 1"},
            {"id": "c2", "start_time": 10.2, "end_time": 59.8, "duration": 49.6, "is_rendered": True, "title": "Bölüm 1 Tekrar (Rendered)"},
            {"id": "c3", "start_time": 100.0, "end_time": 150.0, "duration": 50.0, "is_rendered": False, "title": "Bölüm 2"},
            {"id": "c4", "start_time": 100.0, "end_time": 150.0, "duration": 50.0, "is_rendered": False, "title": "Bölüm 2 Kopya"}
        ],
        "rendered_clips": []
    }

    changed = HistoryManager.deduplicate_project_candidates(project)
    assert changed is True
    # 4 adaydan mükerrer olan 2 tanesi elenmeli, 2 aday kalmalı
    assert len(project["candidates"]) == 2
    # c1 ve c2 arasından render edilmiş olan c2 seçilmiş olmalı
    assert project["candidates"][0]["is_rendered"] is True
    assert project["candidates"][0]["title"] == "Bölüm 1 Tekrar (Rendered)"
    # c3 ve c4 arasından ilk gelen korunmalı
    assert project["candidates"][1]["title"] == "Bölüm 2"

