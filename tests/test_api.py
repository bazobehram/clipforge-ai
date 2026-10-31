import pytest
from fastapi.testclient import TestClient
from app.main import app, verify_auth_dep, trailers_db, trailer_generator

@pytest.fixture
def client():
    app.dependency_overrides[verify_auth_dep] = lambda: True
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_get_version(client):
    res = client.get("/api/version")
    assert res.status_code == 200
    data = res.json()
    assert "version" in data
    assert "build_date" in data
    assert "build_id" in data

def test_list_trailers_endpoint(client):
    res = client.get("/api/trailers")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_trailer_not_found(client):
    res = client.get("/api/trailer/nonexistent_id_999")
    assert res.status_code == 404

def test_update_trailer_text_endpoint(client, tmp_path):
    orig_dir = trailer_generator.trailers_dir
    trailer_generator.trailers_dir = str(tmp_path)
    tid = "t_edit_1"
    try:
        # Örnek fragman kaydı oluştur
        initial_data = {
            "trailer_id": tid,
            "trailer_title": "Eski Başlık",
            "description": "Eski Açıklama",
            "hashtags": ["#eski", "#etiket"],
            "status": "completed"
        }
        trailer_generator.save_trailer_metadata(tid, initial_data)
        trailers_db[tid] = initial_data

        # Güncelleme isteği gönder
        update_payload = {
            "title": "Yeni Çarpıcı Başlık",
            "description": "Yeni düzenlenmiş açıklama metni.",
            "hashtags": ["#yeni", "#teknoloji", "#ai"]
        }
        res = client.post(f"/api/trailers/{tid}/update", json=update_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["trailer"]["trailer_title"] == "Yeni Çarpıcı Başlık"
        assert data["trailer"]["description"] == "Yeni düzenlenmiş açıklama metni."
        assert data["trailer"]["hashtags"] == ["#yeni", "#teknoloji", "#ai"]

        # Diskteki verinin güncellendiğini doğrula
        persisted = trailer_generator.get_trailer_metadata(tid)
        assert persisted["trailer_title"] == "Yeni Çarpıcı Başlık"
        assert persisted["description"] == "Yeni düzenlenmiş açıklama metni."
    finally:
        trailer_generator.trailers_dir = orig_dir
        trailers_db.pop(tid, None)

def test_generate_trailer_validation(client):
    # Proje ID veya URL olmadan istek atılırsa 400 dönmeli
    res = client.post("/api/trailer/generate", json={})
    assert res.status_code == 400

def test_update_trailer_preserves_youtube_url(client, tmp_path):
    orig_dir = trailer_generator.trailers_dir
    trailer_generator.trailers_dir = str(tmp_path)
    tid = "t_yt_test"
    try:
        sample_yt = "https://www.youtube.com/watch?v=sample123"
        initial_data = {
            "trailer_id": tid,
            "trailer_title": "Başlık",
            "description": f"Harika bir özet.\n\n🎬 Videonun tamamı: {sample_yt}",
            "youtube_url": sample_yt,
            "hashtags": ["#test"],
            "status": "completed"
        }
        trailer_generator.save_trailer_metadata(tid, initial_data)
        trailers_db[tid] = initial_data

        update_payload = {
            "title": "Güncel Başlık"
        }
        res = client.post(f"/api/trailers/{tid}/update", json=update_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["trailer"]["youtube_url"] == sample_yt
        assert sample_yt in data["trailer"]["description"]
    finally:
        trailer_generator.trailers_dir = orig_dir
        trailers_db.pop(tid, None)
