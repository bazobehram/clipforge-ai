import os
import uuid
import json
import time
import hmac
import hashlib
import logging
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Response, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.version import VERSION, BUILD_DATE, BUILD_ID
from app.models import (
    LoginRequest, LoginResponse,
    AnalyzeRequest, MoreCandidatesRequest, SearchTopicRequest, CustomClipRequest, RenderClipRequest,
    RegenerateMetaRequest, UpdateClipRequest, MarkSharedRequest,
    CandidateClip, ProjectRecord,
    ProcessRequest, JobResponse, JobStatusEnum, ClipMetadata,
    TrailerStatusEnum, TrailerScene, TrailerRequest, TrailerResponse
)
from app.services.downloader import VideoDownloader
from app.services.transcriber import AudioTranscriber
from app.services.scorer import ContentScorer
from app.services.video_editor import VideoEditor
from app.services.publisher import SocialPublisher
from app.services.history_manager import HistoryManager
from app.services.job_manager import JobManager
from app.services.trailer_generator import TrailerGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("clipforge")

app = FastAPI(
    title="ClipForge AI - Mobil Viral Klip Üretici",
    description="YouTube videolarından otomatik 9:16 viral Shorts/Reels üreten ve paylaşan profesyonel servis",
    version=VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statik dosya ve çıktı dizinleri
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Servisler
downloader = VideoDownloader()
transcriber = AudioTranscriber()
scorer = ContentScorer()
editor = VideoEditor()
history_manager = HistoryManager()
job_manager = JobManager()
trailer_generator = TrailerGenerator()

# Bellek içi aktif analiz durum havuzu (JobManager ile senkronize)
jobs_db: Dict[str, Dict[str, Any]] = {}
for j in job_manager.list_jobs(50):
    jobs_db[j["job_id"]] = j

# Bellek içi ve disk senkronlu fragman havuzu
trailers_db: Dict[str, Dict[str, Any]] = {}
if os.path.exists(trailer_generator.trailers_dir):
    for f in os.listdir(trailer_generator.trailers_dir):
        if f.startswith("trailer_") and f.endswith(".json"):
            tid = f[len("trailer_"):-len(".json")]
            t_meta = trailer_generator.get_trailer_metadata(tid)
            if t_meta:
                trailers_db[tid] = t_meta

# ==========================================
# AUTH / ŞİFRE GÜVENLİK YÖNETİMİ
# ==========================================
def generate_auth_token() -> str:
    return hmac.new(
        settings.AUTH_SECRET.encode(),
        settings.AUTH_PASSWORD.encode(),
        hashlib.sha256
    ).hexdigest()

EXPECTED_TOKEN = generate_auth_token()

def verify_auth_dep(request: Request, authorization: Optional[str] = Header(None), x_auth_token: Optional[str] = Header(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
    elif x_auth_token:
        token = x_auth_token.strip()
    elif "auth_token" in request.cookies:
        token = request.cookies.get("auth_token")

    if not token or token != EXPECTED_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Yetkisiz erişim. Lütfen geçerli yönetici şifresini girin."
        )
    return True

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, response: Response):
    if req.password == settings.AUTH_PASSWORD:
        # 1 Yıl (365 gün) geçerli kalıcı oturum çerezi
        response.set_cookie(
            key="auth_token",
            value=EXPECTED_TOKEN,
            max_age=365 * 24 * 3600,
            httponly=False,
            samesite="lax",
            path="/"
        )
        return LoginResponse(
            success=True,
            token=EXPECTED_TOKEN,
            message="Giriş başarılı."
        )
    raise HTTPException(status_code=401, detail="Hatalı şifre. Lütfen tekrar deneyin.")

@app.get("/api/auth/verify")
def verify_token(response: Response, is_authed: bool = Depends(verify_auth_dep)):
    # Oturumu her ziyarette 1 yıl daha uzat
    response.set_cookie(
        key="auth_token",
        value=EXPECTED_TOKEN,
        max_age=365 * 24 * 3600,
        httponly=False,
        samesite="lax",
        path="/"
    )
    return {"valid": True}

@app.get("/api/version")
def get_version():
    """Uygulama versiyon ve build bilgilerini döndürür (önbellek takibi için)"""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "build_id": BUILD_ID
    }

# ==========================================
# AŞAMA 1: YOUTUBE ANALİZİ & 10 ADAY ÇIKARMA
# ==========================================
def _cleanup_job_dir(job_id: str, dl_result: Optional[Dict[str, Any]] = None):
    try:
        import shutil
        target_dir = None
        if dl_result and dl_result.get("job_dir"):
            target_dir = dl_result["job_dir"]
        else:
            cand_dir = os.path.join(settings.DOWNLOADS_DIR, job_id)
            if os.path.exists(cand_dir):
                target_dir = cand_dir
        if target_dir and os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
            logger.info(f"[{job_id}] Cleaned up temporary directory: {target_dir}")
    except Exception as e:
        logger.warning(f"[{job_id}] Failed to clean job directory: {e}")

def run_analysis_pipeline(job_id: str, url: str, vertical_mode: str, count: int):
    job = jobs_db.get(job_id)
    if not job:
        return
    dl_result = None
    try:
        if job.get("status") == JobStatusEnum.CANCELLED:
            logger.info(f"[{job_id}] Aborted before download.")
            return

        job["status"] = JobStatusEnum.DOWNLOADING
        job["progress"] = 15
        job["message"] = "YouTube videosu ve sesi indiriliyor..."
        job_manager.update_job(job_id, status=JobStatusEnum.DOWNLOADING, progress=15, message=job["message"])
        
        dl_result = downloader.download(url, job_id)
        job["video_title"] = dl_result["title"]
        job["duration"] = dl_result["duration"]
        job["thumbnail"] = dl_result["thumbnail"]
        job_manager.update_job(job_id, video_title=dl_result["title"], duration=dl_result["duration"], thumbnail=dl_result["thumbnail"])

        if job.get("status") == JobStatusEnum.CANCELLED:
            logger.info(f"[{job_id}] Aborted after download.")
            _cleanup_job_dir(job_id, dl_result)
            return

        job["status"] = JobStatusEnum.TRANSCRIBING
        job["progress"] = 25
        job["message"] = "Yapay zeka sesi kelime düzeyinde deşifre ediyor (Whisper)..."
        job["sub_status"] = ""
        job_manager.update_job(job_id, status=JobStatusEnum.TRANSCRIBING, progress=25, message=job["message"])

        def on_transcribe_progress(current_sec: float, total_sec: float, text_snippet: str):
            if job.get("status") == JobStatusEnum.CANCELLED:
                return
            ratio = min(1.0, max(0.0, current_sec / max(1.0, total_sec)))
            # Transkripsiyon sürecini %25 ile %70 arasına yay
            pct = int(25 + ratio * 45)
            job["progress"] = pct
            cur_m, cur_s = divmod(int(current_sec), 60)
            tot_m, tot_s = divmod(int(total_sec), 60)
            job["message"] = f"Yapay zeka sesi deşifre ediyor: {cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d} (%{int(ratio*100)})"
            if text_snippet:
                job["sub_status"] = text_snippet[:85]
            if pct % 10 == 0:
                job_manager.update_job(job_id, progress=pct, message=job["message"], sub_status=job.get("sub_status", ""))

        trans_result = transcriber.transcribe(
            dl_result["audio_path"],
            video_title=dl_result.get("title", ""),
            progress_callback=on_transcribe_progress
        )

        # Deşifre bittikten sonra disk tasarrufu için ham WAV dosyasını temizle
        if os.path.exists(dl_result["audio_path"]):
            try:
                os.remove(dl_result["audio_path"])
            except Exception:
                pass

        if job.get("status") == JobStatusEnum.CANCELLED:
            logger.info(f"[{job_id}] Aborted after transcription.")
            _cleanup_job_dir(job_id, dl_result)
            return

        job["status"] = JobStatusEnum.SCORING
        job["progress"] = 75
        job["message"] = "Transkript inceleniyor, en etkili viral adaylar puanlanıyor..."
        job_manager.update_job(job_id, status=JobStatusEnum.SCORING, progress=75, message=job["message"])

        raw_candidates = scorer.analyze_and_score(
            formatted_transcript=trans_result["formatted_text"],
            video_title=dl_result["title"],
            video_duration=dl_result["duration"],
            max_clips=count,
            offset=0,
            youtube_url=url
        )

        if job.get("status") == JobStatusEnum.CANCELLED:
            logger.info(f"[{job_id}] Aborted after scoring.")
            _cleanup_job_dir(job_id, dl_result)
            return

        candidates_list = []
        for idx, c in enumerate(raw_candidates):
            cid = f"{job_id}_{idx+1}"
            candidates_list.append({
                "id": cid,
                "title": c.get("title", f"Bölüm {idx+1}"),
                "score": round(float(c.get("score", 85)), 1),
                "hook_score": round(float(c.get("hook_score", 8.5)), 1),
                "flow_score": round(float(c.get("flow_score", 8.0)), 1),
                "value_score": round(float(c.get("value_score", 8.0)), 1),
                "start_time": round(float(c.get("start_time", 0.0)), 1),
                "end_time": round(float(c.get("end_time", 30.0)), 1),
                "duration": round(float(c.get("end_time", 30.0)) - float(c.get("start_time", 0.0)), 1),
                "summary": c.get("summary", ""),
                "description": c.get("description", ""),
                "hashtags": c.get("hashtags", ["#shorts", "#reels", "#viral"]),
                "transcript_snippet": c.get("transcript_snippet", ""),
                "is_rendered": False,
                "source_type": "ai",
                "source_query": None,
                "is_shared": False,
                "shared_at": None,
                "shared_platforms": [],
                "thumbnail_url": f"/api/thumbnails/{job_id}/{cid}.jpg"
            })

        # Thumbnail üretimi (Fast Seeking ile milisaniyeler içinde paralel)
        thumb_dir = os.path.join(settings.OUTPUT_DIR, "thumbnails", job_id)
        os.makedirs(thumb_dir, exist_ok=True)
        raw_video = dl_result.get("video_path")

        def _extract_cand_thumb(cand_item):
            if raw_video and os.path.exists(raw_video):
                t_path = os.path.join(thumb_dir, f"{cand_item['id']}.jpg")
                seek_t = cand_item["start_time"] + min(2.0, max(0.5, cand_item["duration"] / 4.0))
                editor.extract_thumbnail(raw_video, seek_t, t_path, width=480)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(_extract_cand_thumb, candidates_list))

        # Meta verilerini diskte kalıcı önbelleğe al (tekil render için)
        meta_file = os.path.join(dl_result["job_dir"], "meta.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "video_path": dl_result["video_path"],
                "youtube_url": url,
                "title": dl_result["title"],
                "duration": dl_result["duration"],
                "thumbnail": dl_result["thumbnail"],
                "words": trans_result.get("words", []),
                "formatted_text": trans_result.get("formatted_text", "")
            }, f, ensure_ascii=False)

        # Projeyi kalıcı geçmişe kaydet
        project_data = {
            "project_id": job_id,
            "youtube_url": url,
            "title": dl_result["title"],
            "duration": round(dl_result["duration"], 1),
            "thumbnail": dl_result["thumbnail"],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "candidates": candidates_list,
            "rendered_clips": []
        }
        history_manager.save_project(project_data)

        job["candidates"] = candidates_list
        job["status"] = JobStatusEnum.COMPLETED
        job["progress"] = 100
        job["message"] = f"{len(candidates_list)} adet viral aday bölüm başarıyla hazırlandı."
        job_manager.update_job(
            job_id,
            status=JobStatusEnum.COMPLETED,
            progress=100,
            message=job["message"],
            video_title=dl_result["title"],
            duration=dl_result["duration"],
            thumbnail=dl_result["thumbnail"]
        )

    except Exception as e:
        logger.exception(f"[{job_id}] Analysis failed: {e}")
        if job.get("status") != JobStatusEnum.CANCELLED:
            job["status"] = JobStatusEnum.FAILED
            job["error"] = str(e)
            job["message"] = f"Analiz sırasında hata oluştu: {str(e)}"
            job_manager.update_job(
                job_id,
                status=JobStatusEnum.FAILED,
                error=str(e),
                message=job["message"]
            )
        _cleanup_job_dir(job_id, dl_result)

@app.post("/api/analyze")
def start_analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks, is_authed: bool = Depends(verify_auth_dep)):
    clean_url = req.url.strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="Geçerli bir YouTube URL'si gereklidir.")

    # 1. Zaten devam eden bir analiz var mı? (Çift istek / yenileme koruması)
    for jid, jdata in jobs_db.items():
        if jdata.get("url") == clean_url and jdata.get("status") in (
            JobStatusEnum.QUEUED, JobStatusEnum.DOWNLOADING,
            JobStatusEnum.TRANSCRIBING, JobStatusEnum.SCORING
        ):
            logger.info(f"Re-attaching to in-progress job {jid} for {clean_url}")
            return {"job_id": jid, "status": jdata["status"], "reused": True}

    # 2. Bu video daha önce analiz edilmiş mi? (Anında yükleme)
    for p in history_manager.list_projects():
        if p.get("youtube_url") == clean_url and p.get("candidates"):
            logger.info(f"Found already analyzed project {p['project_id']} in history")
            return {
                "job_id": p["project_id"],
                "status": "completed",
                "from_history": True,
                "project": p,
                "message": "Bu video daha önce analiz edilmiş, geçmişten anında yüklendi!"
            }

    job_id = str(uuid.uuid4())[:8]
    count = req.count or settings.CANDIDATES_COUNT
    job_data = job_manager.create_job(job_id, clean_url, req.vertical_mode, count)
    jobs_db[job_id] = job_data
    background_tasks.add_task(run_analysis_pipeline, job_id, clean_url, req.vertical_mode, count)
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/analyze/active")
def get_active_job(is_authed: bool = Depends(verify_auth_dep)):
    """Şu an sunucuda aktif olarak çalışan analiz işini döner (sayfa yenilendiğinde tekrar bağlanmak için)"""
    active = job_manager.get_active_job()
    if active:
        jobs_db[active["job_id"]] = active
        return {"active": True, "job": active}
    return {"active": False}

@app.get("/api/jobs")
def list_all_jobs(is_authed: bool = Depends(verify_auth_dep)):
    """Tüm işlem ve analiz kayıtlarını listeler (başarılı, devam eden, kesintiye uğrayan, hatalı + fragmanlar)."""
    jobs = job_manager.list_jobs(limit=50)

    # Tüm kayıtlı fragmanları da işlem geçmişine ekleyelim
    all_trailers = trailer_generator.list_all_trailers()
    for t in all_trailers:
        t_status = t.get("status") or "completed"
        progress = t.get("progress", 100 if t_status == "completed" else 10)
        msg = t.get("message")
        if not msg or (t_status == "completed" and "sıraya alındı" in msg):
            msg = "Sinematik akıllı fragman hazır"

        disp_title = (
            t.get("original_title")
            or t.get("video_title")
            or t.get("trailer_title")
            or t.get("url")
            or t.get("youtube_url")
            or "Akıllı Fragman & Özet"
        )

        scenes_count = len(t.get("scenes", []))
        sub_text = f"🎬 {t.get('aspect_ratio', '9:16')} Özet Fragman"
        if scenes_count > 0:
            sub_text += f" ({scenes_count} Bölüm)"

        jobs.append({
            "job_id": t.get("trailer_id"),
            "trailer_id": t.get("trailer_id"),
            "project_id": t.get("project_id"),
            "url": t.get("url") or t.get("youtube_url") or "",
            "youtube_url": t.get("youtube_url") or "",
            "status": t_status,
            "progress": progress,
            "message": msg,
            "sub_status": sub_text,
            "video_title": disp_title,
            "trailer_title": t.get("trailer_title") or "",
            "original_title": t.get("original_title") or "",
            "duration": t.get("trailer_duration") or t.get("duration", 0),
            "thumbnail": t.get("thumbnail") or "",
            "created_at": t.get("created_at") or "",
            "updated_at": t.get("created_at") or "",
            "error": t.get("error"),
            "is_trailer": True,
            "video_url": t.get("video_url"),
            "video_filename": t.get("video_filename")
        })

    jobs.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return jobs

@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str, background_tasks: BackgroundTasks, is_authed: bool = Depends(verify_auth_dep)):
    """Kesintiye uğrayan, iptal edilen veya başarısız olan bir analizi yeniden başlatır."""
    old_job = job_manager.get_job(job_id)
    if not old_job or not old_job.get("url"):
        raise HTTPException(status_code=404, detail="Yeniden başlatılacak işlem veya URL bulunamadı.")
    
    clean_url = old_job["url"]
    count = old_job.get("count", settings.CANDIDATES_COUNT)
    v_mode = old_job.get("vertical_mode", settings.VERTICAL_MODE)
    new_job_id = str(uuid.uuid4())[:8]
    
    new_job = job_manager.create_job(new_job_id, clean_url, v_mode, count)
    jobs_db[new_job_id] = new_job
    background_tasks.add_task(run_analysis_pipeline, new_job_id, clean_url, v_mode, count)
    return {"job_id": new_job_id, "status": "queued"}

@app.delete("/api/jobs/{job_id}")
def delete_job_log(job_id: str, is_authed: bool = Depends(verify_auth_dep)):
    """İşlem geçmişinden tek bir kaydı siler."""
    deleted = job_manager.delete_job(job_id)
    if job_id in jobs_db:
        jobs_db.pop(job_id, None)
    return {"success": deleted}

@app.post("/api/analyze/{job_id}/cancel")
def cancel_analyze(job_id: str, is_authed: bool = Depends(verify_auth_dep)):
    """Devam eden analiz işlemini iptal eder ve sunucu kaynaklarını temizler"""
    success = job_manager.cancel_job(job_id)
    if job_id in jobs_db:
        jobs_db[job_id]["status"] = JobStatusEnum.CANCELLED
        jobs_db[job_id]["message"] = "İşlem kullanıcı tarafından iptal edildi."
    _cleanup_job_dir(job_id)
    return {"success": success, "message": "Analiz işlemi iptal edildi." if success else "İşlem iptal edilemedi veya zaten sonlanmıştı."}

@app.get("/api/analyze/{job_id}")
def get_analyze_status(job_id: str, is_authed: bool = Depends(verify_auth_dep)):
    job = job_manager.get_job(job_id) or jobs_db.get(job_id)
    if not job:
        project = history_manager.get_project(job_id)
        if project:
            return {
                "job_id": job_id,
                "status": "completed",
                "progress": 100,
                "message": "Tamamlandı",
                "video_title": project.get("title"),
                "duration": project.get("duration"),
                "youtube_url": project.get("youtube_url", ""),
                "thumbnail": project.get("thumbnail", ""),
                "candidates": project.get("candidates", []),
                "rendered_clips": project.get("rendered_clips", [])
            }
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    return jobs_db[job_id]

# Geriye dönük uyumluluk endpoint'leri
@app.post("/api/process", response_model=JobResponse)
def start_legacy_process(req: ProcessRequest, background_tasks: BackgroundTasks):
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="Geçerli bir YouTube URL'si gereklidir.")
    job_id = str(uuid.uuid4())[:8]
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": JobStatusEnum.QUEUED,
        "progress": 5,
        "message": "İşlem kuyruğa alındı...",
        "candidates": [],
        "clips": [],
        "video_title": None,
        "duration": None,
        "error": None
    }
    count = req.max_clips or 4
    background_tasks.add_task(run_analysis_pipeline, job_id, req.url, req.vertical_mode, count)
    return JobResponse(
        job_id=job_id,
        status=JobStatusEnum.QUEUED,
        progress=5,
        message="İşlem kuyruğa alındı..."
    )

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_legacy_job_status(job_id: str):
    if job_id in jobs_db:
        j = jobs_db[job_id]
        return JobResponse(
            job_id=job_id,
            status=j.get("status", JobStatusEnum.FAILED),
            progress=j.get("progress", 0),
            message=j.get("message", ""),
            video_title=j.get("video_title"),
            original_duration=j.get("duration"),
            candidates=j.get("candidates", []),
            clips=[],
            error=j.get("error")
        )
    p = history_manager.get_project(job_id)
    if p:
        return JobResponse(
            job_id=job_id,
            status=JobStatusEnum.COMPLETED,
            progress=100,
            message="Tamamlandı",
            video_title=p.get("title"),
            original_duration=p.get("duration"),
            candidates=p.get("candidates", []),
            clips=[]
        )
    raise HTTPException(status_code=404, detail="İş bulunamadı.")

# ==========================================
# AKILLI FRAGMAN & VİDEO ÖZETİ (TRAILER PIPELINE)
# ==========================================
def run_trailer_pipeline(trailer_id: str, req: TrailerRequest):
    t_job = trailers_db.get(trailer_id)
    if not t_job:
        return

    try:
        project_id = req.project_id
        video_path = None
        words = []
        segments = []
        video_title = ""
        duration = 0.0
        youtube_url = ""

        # 1. Kaynak Tespiti (Mevcut Proje mi yoksa Yeni URL mi?)
        thumbnail = ""
        if project_id:
            project = history_manager.get_project(project_id)
            if not project:
                raise Exception("Belirtilen geçmiş proje bulunamadı.")
            video_title = project.get("title", "Proje")
            duration = float(project.get("duration", 0))
            youtube_url = project.get("youtube_url", "")
            thumbnail = project.get("thumbnail", "")

            t_job["video_title"] = video_title
            t_job["original_title"] = video_title
            t_job["thumbnail"] = thumbnail
            t_job["youtube_url"] = youtube_url
            t_job["url"] = youtube_url
            trailer_generator.save_trailer_metadata(trailer_id, t_job)

            meta_file = os.path.join(settings.DOWNLOADS_DIR, project_id, "meta.json")
            if not os.path.exists(meta_file):
                raise Exception("Projenin transkript ve analiz verileri diskte bulunamadı.")

            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            if not youtube_url:
                youtube_url = meta.get("youtube_url", "")
            if not thumbnail:
                thumbnail = meta.get("thumbnail", "")
                t_job["thumbnail"] = thumbnail

            video_path = meta.get("video_path")
            if not video_path or not os.path.exists(video_path):
                alt_path = os.path.join(settings.DOWNLOADS_DIR, project_id, "original_video.mp4")
                if os.path.exists(alt_path):
                    video_path = alt_path
                else:
                    t_job["message"] = "Ham video dosyası yeniden indiriliyor..."
                    dl_res = downloader.download(project.get("youtube_url", ""), project_id)
                    video_path = dl_res["video_path"]

            words = meta.get("words", [])
            formatted_text = meta.get("formatted_text", "")
            if formatted_text:
                segments = trailer_generator.parse_formatted_text_to_segments(formatted_text)
            if not segments and words:
                segments = trailer_generator.group_words_to_segments(words)

        elif req.url:
            t_job["status"] = TrailerStatusEnum.ANALYZING
            t_job["progress"] = 15
            t_job["message"] = "YouTube videosu indiriliyor..."
            clean_url = downloader.sanitize_url(req.url)
            youtube_url = clean_url
            project_id = str(uuid.uuid4())[:8]
            t_job["project_id"] = project_id

            dl_res = downloader.download(clean_url, project_id)
            video_path = dl_res["video_path"]
            video_title = dl_res.get("title", "Video")
            duration = float(dl_res.get("duration", 0))
            thumbnail = dl_res.get("thumbnail", "")

            t_job["video_title"] = video_title
            t_job["original_title"] = video_title
            t_job["thumbnail"] = thumbnail
            t_job["duration"] = duration
            t_job["youtube_url"] = youtube_url
            t_job["url"] = youtube_url
            trailer_generator.save_trailer_metadata(trailer_id, t_job)

            t_job["progress"] = 30
            t_job["message"] = "Yapay zeka sesi deşifre ediyor (Whisper)..."
            tr_res = transcriber.transcribe(dl_res["audio_path"], video_title=video_title)
            words = tr_res.get("words", [])
            segments = tr_res.get("segments", [])
            if not segments and words:
                segments = trailer_generator.group_words_to_segments(words)

            # İndirilen ve deşifre edilen projeyi diskte sakla (tekrar kullanım için)
            try:
                meta_file = os.path.join(settings.DOWNLOADS_DIR, project_id, "meta.json")
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "video_path": video_path,
                        "youtube_url": clean_url,
                        "title": video_title,
                        "duration": duration,
                        "thumbnail": dl_res.get("thumbnail", ""),
                        "words": words,
                        "formatted_text": tr_res.get("formatted_text", "")
                    }, f, ensure_ascii=False, indent=2)

                project_data = {
                    "project_id": project_id,
                    "youtube_url": clean_url,
                    "title": video_title,
                    "duration": round(duration, 1),
                    "thumbnail": dl_res.get("thumbnail", ""),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "candidates": [],
                    "rendered_clips": []
                }
                history_manager.save_project(project_data)
            except Exception as pe:
                logger.warning(f"Could not persist project for trailer: {pe}")
        else:
            raise Exception("Lütfen mevcut bir proje seçin veya geçerli bir YouTube URL'si girin.")

        t_job["video_title"] = video_title
        t_job["duration"] = duration
        t_job["youtube_url"] = youtube_url

        # 2. Hikaye Eğrisi ve Kilit Sahne Seçimi
        t_job["status"] = TrailerStatusEnum.ANALYZING
        t_job["progress"] = 45
        t_job["message"] = "Yapay zeka videonun ana konusunu, dönüm noktalarını ve hikaye akışını inceliyor..."

        target_dur = req.target_duration or 60
        scenes, meta_info = trailer_generator.select_narrative_scenes(
            transcript_segments=segments,
            video_title=video_title,
            total_duration=duration,
            target_duration=target_dur,
            all_words=words
        )

        if not scenes:
            raise Exception("Videonun kurgusu için uygun sahneler çıkarılamadı.")

        card_dur = 1.0 if (req.style or "cinematic") == "cinematic" else 0.0
        total_trailer_sec = round(sum(s.get("duration", 0) for s in scenes) + max(0, len(scenes) - 1) * card_dur, 1)

        trailer_desc = meta_info.get("description") or ""
        if youtube_url and youtube_url not in trailer_desc:
            trailer_desc = f"{trailer_desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()

        t_job["scenes"] = scenes
        t_job["trailer_title"] = meta_info.get("trailer_title") or video_title
        t_job["original_title"] = video_title
        t_job["video_title"] = meta_info.get("trailer_title") or video_title
        t_job["description"] = trailer_desc
        t_job["youtube_url"] = youtube_url
        if thumbnail:
            t_job["thumbnail"] = thumbnail
        t_job["hashtags"] = meta_info.get("hashtags") or []
        t_job["trailer_duration"] = total_trailer_sec
        t_job["duration"] = total_trailer_sec
        t_job["original_duration"] = duration
        t_job["status"] = TrailerStatusEnum.RENDERING
        t_job["progress"] = 65
        t_job["message"] = f"{len(scenes)} kilit sahne seçildi ({total_trailer_sec}s), sinematik fragman render ediliyor..."

        # 3. FFmpeg ile Render
        def on_render_progress(pct, msg):
            t_job["progress"] = pct
            t_job["message"] = msg

        output_file = trailer_generator.render_cinematic_trailer(
            video_path=video_path,
            scenes=scenes,
            all_words=words,
            trailer_id=trailer_id,
            aspect_ratio=req.aspect_ratio or "9:16",
            crop_mode=req.crop_mode or "blur_background",
            style=req.style or "cinematic",
            progress_callback=on_render_progress
        )

        filename = os.path.basename(output_file)
        file_size_mb = 0.0
        try:
            if os.path.exists(output_file):
                file_size_mb = round(os.path.getsize(output_file) / (1024 * 1024), 1)
        except Exception:
            pass

        t_job["status"] = TrailerStatusEnum.COMPLETED
        t_job["progress"] = 100
        t_job["message"] = "Sinematik akıllı fragman başarıyla hazırlandı!"
        t_job["video_filename"] = filename
        t_job["video_url"] = f"/api/clips/{filename}?v={int(time.time())}"
        t_job["crop_mode"] = req.crop_mode or "blur_background"
        t_job["file_size_mb"] = file_size_mb

        # Diske kaydet
        trailer_generator.save_trailer_metadata(trailer_id, t_job)

    except Exception as e:
        logger.error(f"[{trailer_id}] Trailer generation failed: {e}", exc_info=True)
        t_job["status"] = TrailerStatusEnum.FAILED
        t_job["progress"] = 0
        t_job["message"] = f"Fragman oluşturulamadı: {str(e)}"
        t_job["error"] = str(e)
        trailer_generator.save_trailer_metadata(trailer_id, t_job)

@app.post("/api/trailer/generate")
def generate_trailer(req: TrailerRequest, background_tasks: BackgroundTasks, is_authed: bool = Depends(verify_auth_dep)):
    """Yeni bir akıllı video fragmanı ve özeti oluşturma işi başlatır."""
    if not req.project_id and not (req.url and req.url.strip()):
        raise HTTPException(status_code=400, detail="Lütfen bir proje seçin veya YouTube URL'si girin.")

    init_title = ""
    init_thumb = ""
    init_yt = req.url or ""
    if req.project_id:
        p = history_manager.get_project(req.project_id)
        if p:
            init_title = p.get("title", "")
            init_thumb = p.get("thumbnail", "")
            init_yt = p.get("youtube_url", "") or init_yt

    trailer_id = str(uuid.uuid4())[:8]
    t_data = {
        "trailer_id": trailer_id,
        "project_id": req.project_id,
        "status": TrailerStatusEnum.QUEUED,
        "progress": 5,
        "message": "Fragman işlemi sıraya alındı...",
        "video_title": init_title,
        "original_title": init_title,
        "trailer_title": init_title,
        "thumbnail": init_thumb,
        "url": init_yt,
        "youtube_url": init_yt,
        "scenes": [],
        "video_filename": None,
        "video_url": None,
        "duration": None,
        "aspect_ratio": req.aspect_ratio or "9:16",
        "crop_mode": req.crop_mode or "blur_background",
        "style": req.style or "cinematic",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error": None
    }
    trailers_db[trailer_id] = t_data
    trailer_generator.save_trailer_metadata(trailer_id, t_data)

    background_tasks.add_task(run_trailer_pipeline, trailer_id, req)
    return {"trailer_id": trailer_id, "status": "queued", "message": "Fragman oluşturma işlemi başlatıldı."}

@app.get("/api/trailer/{trailer_id}")
def get_trailer_status(trailer_id: str, is_authed: bool = Depends(verify_auth_dep)):
    """Fragman oluşturma sürecinin anlık durumunu ve sonucunu döner."""
    disk_meta = trailer_generator.get_trailer_metadata(trailer_id)
    if disk_meta:
        if trailer_id in trailers_db:
            trailers_db[trailer_id].update(disk_meta)
        else:
            trailers_db[trailer_id] = disk_meta
        return trailers_db[trailer_id]
    t = trailers_db.get(trailer_id)
    if not t:
        raise HTTPException(status_code=404, detail="Fragman bulunamadı.")
    return t

@app.get("/api/projects/{project_id}/trailer")
def get_project_trailer(project_id: str, is_authed: bool = Depends(verify_auth_dep)):
    """Belirli bir projeye ait üretilmiş bir fragman var mı kontrol eder."""
    for tid, t in trailers_db.items():
        if t.get("project_id") == project_id and t.get("status") == TrailerStatusEnum.COMPLETED:
            return {"exists": True, "trailer": t}

    if os.path.exists(trailer_generator.trailers_dir):
        for f in os.listdir(trailer_generator.trailers_dir):
            if f.startswith("trailer_") and f.endswith(".json"):
                tid = f[len("trailer_"):-len(".json")]
                meta = trailer_generator.get_trailer_metadata(tid)
                if meta and meta.get("project_id") == project_id and meta.get("status") == TrailerStatusEnum.COMPLETED:
                    trailers_db[tid] = meta
                    return {"exists": True, "trailer": meta}

    return {"exists": False}

@app.get("/api/trailers")
def list_all_trailers(is_authed: bool = Depends(verify_auth_dep)):
    """Oluşturulan tüm akıllı fragmanları en yeniden eskiye listeler."""
    return trailer_generator.list_all_trailers()

@app.delete("/api/trailers/{trailer_id}")
def delete_trailer_endpoint(trailer_id: str, is_authed: bool = Depends(verify_auth_dep)):
    """Bir fragmanı ve video dosyasını sistemden siler."""
    success = trailer_generator.delete_trailer(trailer_id)
    if trailer_id in trailers_db:
        trailers_db.pop(trailer_id, None)
    return {"success": success}

class TrailerUpdateTextRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None

@app.post("/api/trailers/{trailer_id}/update")
def update_trailer_text_endpoint(trailer_id: str, req: TrailerUpdateTextRequest, is_authed: bool = Depends(verify_auth_dep)):
    """Fragmanın başlık, açıklama ve etiket metinlerindeki düzenlemeleri kaydeder."""
    meta = trailer_generator.get_trailer_metadata(trailer_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Fragman bulunamadı.")
    if req.title is not None:
        meta["trailer_title"] = req.title.strip()
        meta["video_title"] = req.title.strip()
    if req.description is not None:
        meta["description"] = req.description.strip()
    if req.hashtags is not None:
        meta["hashtags"] = req.hashtags
    trailer_generator.save_trailer_metadata(trailer_id, meta)
    if trailer_id in trailers_db:
        trailers_db[trailer_id].update(meta)
    return {"success": True, "trailer": meta}


# ==========================================
# DAHA FAZLA ADAY İSTEĞİ (+10 KLİP)
# ==========================================
@app.post("/api/candidates/more")
def get_more_candidates(req: MoreCandidatesRequest, is_authed: bool = Depends(verify_auth_dep)):
    project = history_manager.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    meta_file = os.path.join(settings.DOWNLOADS_DIR, req.project_id, "meta.json")
    if not os.path.exists(meta_file):
        raise HTTPException(status_code=400, detail="Videonun analiz verisi diskte bulunamadı.")

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    current_count = len(project.get("candidates", []))
    youtube_url = project.get("youtube_url", "")
    new_raw = scorer.analyze_and_score(
        formatted_transcript=meta.get("formatted_text", ""),
        video_title=meta.get("title", ""),
        video_duration=meta.get("duration", 0),
        max_clips=req.count or 10,
        offset=current_count,
        youtube_url=youtube_url,
        existing_candidates=project.get("candidates", [])
    )

    new_candidates = []
    for idx, c in enumerate(new_raw):
        c_st = round(float(c.get("start_time", 0.0)), 1)
        c_et = round(float(c.get("end_time", 30.0)), 1)
        c_dur = max(1.0, c_et - c_st)

        # Mevcut adaylarla çakışma kontrolü
        is_dup = False
        for ex in project.get("candidates", []):
            try:
                ex_st = round(float(ex.get("start_time", 0.0)), 1)
                ex_et = round(float(ex.get("end_time", 0.0)), 1)
            except (ValueError, TypeError):
                continue
            overlap = max(0.0, min(c_et, ex_et) - max(c_st, ex_st))
            if (abs(c_st - ex_st) < 10.0 and abs(c_et - ex_et) < 10.0) or (overlap / min(c_dur, max(1.0, ex_et - ex_st)) > 0.40):
                is_dup = True
                break
        if is_dup:
            continue

        cid = f"{req.project_id}_{len(project.get('candidates', [])) + len(new_candidates) + 1}"
        new_candidates.append({
            "id": cid,
            "title": c.get("title", f"Bölüm {len(project.get('candidates', [])) + len(new_candidates) + 1}"),
            "score": round(float(c.get("score", 85)), 1),
            "hook_score": round(float(c.get("hook_score", 8.5)), 1),
            "flow_score": round(float(c.get("flow_score", 8.0)), 1),
            "value_score": round(float(c.get("value_score", 8.0)), 1),
            "start_time": c_st,
            "end_time": c_et,
            "duration": round(c_et - c_st, 1),
            "summary": c.get("summary", ""),
            "description": c.get("description", ""),
            "hashtags": c.get("hashtags", ["#shorts", "#reels", "#viral"]),
            "transcript_snippet": c.get("transcript_snippet", ""),
            "is_rendered": False,
            "source_type": "ai",
            "source_query": None,
            "is_shared": False,
            "shared_at": None,
            "shared_platforms": [],
            "thumbnail_url": f"/api/thumbnails/{req.project_id}/{cid}.jpg"
        })

    video_path = meta.get("video_path")
    thumb_dir = os.path.join(settings.OUTPUT_DIR, "thumbnails", req.project_id)
    os.makedirs(thumb_dir, exist_ok=True)

    def _extract_more_thumb(cand_item):
        if video_path and os.path.exists(video_path):
            t_path = os.path.join(thumb_dir, f"{cand_item['id']}.jpg")
            seek_t = cand_item["start_time"] + min(2.0, max(0.5, cand_item["duration"] / 4.0))
            editor.extract_thumbnail(video_path, seek_t, t_path, width=480)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(_extract_more_thumb, new_candidates))

    project["candidates"].extend(new_candidates)
    history_manager.save_project(project)
    return {
        "candidates": project["candidates"],
        "added_count": len(new_candidates),
        "new_first_id": new_candidates[0]["id"] if new_candidates else None
    }

# ==========================================
# KONUYA / CÜMLEYE GÖRE VİDEODA KLİP ARAMA
# ==========================================
@app.post("/api/search-topic")
def search_topic(req: SearchTopicRequest, is_authed: bool = Depends(verify_auth_dep)):
    project = history_manager.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Arama konusu veya kelimesi girilmelidir.")

    meta_file = os.path.join(settings.DOWNLOADS_DIR, req.project_id, "meta.json")
    if not os.path.exists(meta_file):
        raise HTTPException(status_code=400, detail="Videonun analiz verisi diskte bulunamadı.")

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    youtube_url = project.get("youtube_url", "")
    matched_raw = scorer.search_topic_clips(
        query=query,
        formatted_transcript=meta.get("formatted_text", ""),
        video_title=meta.get("title", ""),
        video_duration=meta.get("duration", 0),
        youtube_url=youtube_url
    )

    if not matched_raw:
        return {"matched_candidates": [], "message": f"'{query}' konusuyla ilgili net bir kesit bulunamadı."}

    current_candidates = project.get("candidates", [])
    start_idx = len(current_candidates)
    new_candidates = []

    for idx, c in enumerate(matched_raw):
        cid = f"{req.project_id}_search_{start_idx + idx + 1}"
        cand_obj = {
            "id": cid,
            "title": c.get("title", f"🎯 {query.capitalize()} - {meta.get('title')}"),
            "score": round(float(c.get("score", 92)), 1),
            "hook_score": round(float(c.get("hook_score", 9.2)), 1),
            "flow_score": round(float(c.get("flow_score", 8.8)), 1),
            "value_score": round(float(c.get("value_score", 9.2)), 1),
            "start_time": round(float(c.get("start_time", 0.0)), 1),
            "end_time": round(float(c.get("end_time", 30.0)), 1),
            "duration": round(float(c.get("end_time", 30.0)) - float(c.get("start_time", 0.0)), 1),
            "summary": c.get("summary", f"'{query}' aramasıyla eşleşen odak kesit."),
            "description": c.get("description", ""),
            "hashtags": c.get("hashtags", ["#shorts", "#reels", "#viral"]),
            "transcript_snippet": c.get("transcript_snippet", ""),
            "is_rendered": False,
            "source_type": "search",
            "source_query": query,
            "is_shared": False,
            "shared_at": None,
            "shared_platforms": [],
            "thumbnail_url": f"/api/thumbnails/{req.project_id}/{cid}.jpg"
        }
        new_candidates.append(cand_obj)

    # Arama sonuçları için küçük resimleri çıkar
    video_path = meta.get("video_path")
    if video_path and os.path.exists(video_path):
        thumb_dir = os.path.join(settings.OUTPUT_DIR, "thumbnails", req.project_id)
        os.makedirs(thumb_dir, exist_ok=True)
        for c_obj in new_candidates:
            t_path = os.path.join(thumb_dir, f"{c_obj['id']}.jpg")
            seek_t = c_obj["start_time"] + min(2.0, max(0.5, c_obj["duration"] / 4.0))
            editor.extract_thumbnail(video_path, seek_t, t_path, width=480)

    # Bulunan arama sonuçlarını adayların en başına ekle
    project["candidates"] = new_candidates + project["candidates"]
    history_manager.save_project(project)

    return {"matched_candidates": new_candidates, "candidates": project["candidates"]}

@app.post("/api/custom-clip")
def create_custom_clip(req: CustomClipRequest, is_authed: bool = Depends(verify_auth_dep)):
    project = history_manager.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    meta_file = os.path.join(settings.DOWNLOADS_DIR, req.project_id, "meta.json")
    if not os.path.exists(meta_file):
        raise HTTPException(status_code=400, detail="Videonun analiz verisi diskte bulunamadı.")

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    duration = meta.get("duration", 0)
    start_t = max(0.0, float(req.start_time))
    end_t = min(float(duration), float(req.end_time))
    if end_t <= start_t:
        raise HTTPException(status_code=400, detail="Bitiş süresi başlangıç süresinden büyük olmalıdır.")

    snippet = ""
    for w in meta.get("words", []):
        if start_t <= w.get("start", 0) <= end_t:
            snippet += " " + w.get("word", "")
            if len(snippet) > 120:
                break
    snippet = snippet.strip() or f"{meta.get('title', 'Video')} özel kesiti"

    title = req.title.strip() if req.title else f"✂️ Özel Kesit ({int(start_t)}s - {int(end_t)}s)"
    cid = f"{req.project_id}_custom_{int(start_t)}_{int(end_t)}"

    youtube_url = project.get("youtube_url", "")
    desc = req.description.strip() if req.description else f"{title} videosunun özel kesiti."
    if youtube_url and youtube_url not in desc:
        desc = f"{desc}\n\n🎬 Videonun tamamı: {youtube_url}".strip()

    custom_candidate = {
        "id": cid,
        "title": title,
        "score": 95.0,
        "hook_score": 9.5,
        "flow_score": 9.0,
        "value_score": 9.5,
        "start_time": round(start_t, 1),
        "end_time": round(end_t, 1),
        "duration": round(end_t - start_t, 1),
        "summary": "Kullanıcı tarafından belirlenen özel zaman aralığı.",
        "description": desc,
        "hashtags": req.hashtags if req.hashtags else ["#shorts", "#viral", "#reels", "#özelkesit"],
        "transcript_snippet": snippet,
        "is_rendered": False,
        "source_type": "custom",
        "source_query": None,
        "is_shared": False,
        "shared_at": None,
        "shared_platforms": [],
        "thumbnail_url": f"/api/thumbnails/{req.project_id}/{cid}.jpg"
    }

    video_path = meta.get("video_path")
    if video_path and os.path.exists(video_path):
        thumb_dir = os.path.join(settings.OUTPUT_DIR, "thumbnails", req.project_id)
        os.makedirs(thumb_dir, exist_ok=True)
        t_path = os.path.join(thumb_dir, f"{cid}.jpg")
        seek_t = start_t + min(2.0, max(0.5, (end_t - start_t) / 4.0))
        editor.extract_thumbnail(video_path, seek_t, t_path, width=480)

    project["candidates"] = [custom_candidate] + project.get("candidates", [])
    history_manager.save_project(project)

    return {"custom_candidate": custom_candidate, "candidates": project["candidates"]}


# ==========================================
# AŞAMA 2: İSTEĞE BAĞLI TEKİL KLİP RENDER ETME
# ==========================================
@app.post("/api/render-clip")
def render_single_clip(req: RenderClipRequest, is_authed: bool = Depends(verify_auth_dep)):
    project = history_manager.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    target_candidate = None
    target_cid = str(req.candidate_id)
    for cand in project.get("candidates", []):
        if str(cand.get("id")) == target_cid:
            target_candidate = cand
            break

    if not target_candidate:
        raise HTTPException(status_code=404, detail="Aday klip bulunamadı.")

    meta_file = os.path.join(settings.DOWNLOADS_DIR, req.project_id, "meta.json")
    if not os.path.exists(meta_file):
        raise HTTPException(status_code=400, detail="Videonun ham dosyası bulunamadı. Lütfen videoyu yeniden analiz edin.")

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    video_path = meta.get("video_path")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="Ham video dosyası bulunamadı.")

    video_duration = float(meta.get("duration", 99999.0))
    if req.start_time is not None and req.end_time is not None:
        start_t = max(0.0, float(req.start_time))
        end_t = min(video_duration, float(req.end_time))
        if end_t <= start_t:
            start_t = float(target_candidate["start_time"])
            end_t = float(target_candidate["end_time"])
        else:
            target_candidate["start_time"] = round(start_t, 1)
            target_candidate["end_time"] = round(end_t, 1)
            target_candidate["duration"] = round(end_t - start_t, 1)
    else:
        start_t = float(target_candidate["start_time"])
        end_t = float(target_candidate["end_time"])

    words = meta.get("words", [])

    # Kullanıcının düzenlediği veya adaydan gelen başlık/açıklama
    title = req.title.strip() if req.title else target_candidate.get("title", "Viral Shorts")
    description = req.description.strip() if req.description else target_candidate.get("description", "")
    hashtags = req.hashtags if req.hashtags else target_candidate.get("hashtags", ["#shorts", "#reels"])

    youtube_url = project.get("youtube_url") or meta.get("youtube_url", "")
    if youtube_url and youtube_url not in description:
        description = f"{description}\n\n🎬 Videonun tamamı: {youtube_url}".strip()

    render_res = editor.cut_and_convert_vertical(
        video_path=video_path,
        start_time=start_t,
        end_time=end_t,
        clip_id=target_cid,
        mode=req.vertical_mode or settings.VERTICAL_MODE,
        words=words
    )

    rendered_filename = render_res["video_filename"]
    actual_start = render_res["start_time"]
    actual_end = render_res["end_time"]
    actual_dur = render_res["duration"]

    # Aday bilgilerini gerçek kesilen sınırlarla da senkronize et
    target_candidate["start_time"] = actual_start
    target_candidate["end_time"] = actual_end
    target_candidate["duration"] = actual_dur

    share_urls = SocialPublisher.generate_share_urls(title, description, hashtags, youtube_url=youtube_url)
    clip_ts = int(datetime.now().timestamp())

    rendered_clip = {
        "id": target_cid,
        "title": title,
        "score": target_candidate["score"],
        "hook_score": target_candidate["hook_score"],
        "flow_score": target_candidate["flow_score"],
        "value_score": target_candidate["value_score"],
        "start_time": actual_start,
        "end_time": actual_end,
        "duration": actual_dur,
        "summary": target_candidate.get("summary", ""),
        "description": description,
        "hashtags": hashtags,
        "transcript_snippet": target_candidate.get("transcript_snippet", ""),
        "is_rendered": True,
        "video_filename": rendered_filename,
        "video_url": f"/api/clips/{rendered_filename}?v={clip_ts}",
        "rendered_at_ts": clip_ts,
        "share_urls": share_urls,
        "source_type": target_candidate.get("source_type", "ai"),
        "source_query": target_candidate.get("source_query", None),
        "is_shared": target_candidate.get("is_shared", False),
        "shared_at": target_candidate.get("shared_at", None),
        "shared_platforms": target_candidate.get("shared_platforms", [])
    }

    history_manager.add_rendered_clip(req.project_id, rendered_clip)
    return rendered_clip

# ==========================================
# AI İLE BAŞLIK & AÇIKLAMA YENİLEME
# ==========================================
@app.post("/api/regenerate-meta")
def regenerate_meta(req: RegenerateMetaRequest, is_authed: bool = Depends(verify_auth_dep)):
    project = history_manager.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    target_candidate = None
    for cand in project.get("candidates", []):
        if cand.get("id") == req.candidate_id:
            target_candidate = cand
            break

    if not target_candidate:
        raise HTTPException(status_code=404, detail="Aday klip bulunamadı.")

    snippet = target_candidate.get("transcript_snippet") or target_candidate.get("title", "")
    video_title = project.get("title", "")
    youtube_url = project.get("youtube_url", "")

    new_meta = scorer.regenerate_clip_metadata(
        transcript_snippet=snippet,
        video_title=video_title,
        current_title=req.current_title or target_candidate.get("title"),
        youtube_url=youtube_url
    )

    history_manager.update_clip_text(
        project_id=req.project_id,
        clip_id=req.candidate_id,
        title=new_meta.get("title", target_candidate["title"]),
        description=new_meta.get("description", target_candidate["description"]),
        hashtags=new_meta.get("hashtags", target_candidate["hashtags"])
    )

    return new_meta

# ==========================================
# METİN GÜNCELLEME (KULLANICI DÜZENLEMESİ)
# ==========================================
@app.post("/api/clips/update")
def update_clip(req: UpdateClipRequest, is_authed: bool = Depends(verify_auth_dep)):
    success = history_manager.update_clip_text(
        project_id=req.project_id,
        clip_id=req.clip_id,
        title=req.title,
        description=req.description,
        hashtags=req.hashtags
    )
    if not success:
        raise HTTPException(status_code=404, detail="Klip güncellenemedi.")
    return {"success": True}

# ==========================================
# PAYLAŞILDI DURUMU YÖNETİMİ
# ==========================================
@app.post("/api/clips/mark-shared")
def mark_clip_shared(req: MarkSharedRequest, is_authed: bool = Depends(verify_auth_dep)):
    success = history_manager.mark_clip_shared(
        project_id=req.project_id,
        clip_id=req.clip_id,
        platform=req.platform or "native",
        is_shared=req.is_shared if req.is_shared is not None else True
    )
    if not success:
        raise HTTPException(status_code=404, detail="Klip bulunamadı.")
    return {"success": True}

# ==========================================
# GEÇMİŞ (HISTORY) YÖNETİMİ
# ==========================================
@app.get("/api/history")
def get_history(is_authed: bool = Depends(verify_auth_dep)):
    return history_manager.list_projects()

@app.get("/api/history/{project_id}")
def get_project_details(project_id: str, is_authed: bool = Depends(verify_auth_dep)):
    p = history_manager.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")
    return p

@app.delete("/api/history/{project_id}")
def delete_project(project_id: str, is_authed: bool = Depends(verify_auth_dep)):
    success = history_manager.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Proje bulunamadı veya silinemedi.")
    return {"success": True, "message": "Proje ve tüm video dosyaları başarıyla silindi."}

@app.delete("/api/history/{project_id}/clips/{clip_id}")
def delete_clip(project_id: str, clip_id: str, is_authed: bool = Depends(verify_auth_dep)):
    success = history_manager.delete_clip(project_id, clip_id)
    if not success:
        raise HTTPException(status_code=404, detail="Klip bulunamadı veya silinemedi.")
    return {"success": True, "message": "Klip başarıyla silindi."}

# ==========================================
# VİDEO İNDİRME, KÜÇÜK RESİMLER & STATİK DOSYALAR
# ==========================================
@app.get("/api/thumbnails/{project_id}/{thumb_name}")
def get_candidate_thumbnail(project_id: str, thumb_name: str):
    """Aday klibin video kesitinden çıkarılmış ekran görüntüsünü sunar (yoksa anında üretir)"""
    safe_name = os.path.basename(thumb_name)
    thumb_dir = os.path.join(settings.OUTPUT_DIR, "thumbnails", project_id)
    thumb_path = os.path.join(thumb_dir, safe_name)

    if os.path.exists(thumb_path):
        return FileResponse(thumb_path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

    cand_id = safe_name.rsplit(".", 1)[0]
    meta_file = os.path.join(settings.DOWNLOADS_DIR, project_id, "meta.json")
    video_path = None
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            video_path = meta.get("video_path")
        except Exception:
            pass

    if not video_path or not os.path.exists(video_path):
        candidate_source = os.path.join(settings.DOWNLOADS_DIR, project_id, "original_video.mp4")
        if os.path.exists(candidate_source):
            video_path = candidate_source

    proj = history_manager.get_project(project_id)
    if video_path and os.path.exists(video_path):
        timestamp = 2.0
        if proj:
            all_cands = proj.get("candidates", []) + proj.get("rendered_clips", [])
            for c in all_cands:
                cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
                if cid == cand_id:
                    st = float(c.get("start_time") if isinstance(c, dict) else getattr(c, "start_time", 0.0))
                    dur = float(c.get("duration") if isinstance(c, dict) else getattr(c, "duration", 10.0))
                    timestamp = st + min(2.0, max(0.5, dur / 4.0))
                    break
        os.makedirs(thumb_dir, exist_ok=True)
        if editor.extract_thumbnail(video_path, timestamp, thumb_path, width=480):
            return FileResponse(thumb_path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

    # Eğer video silinmişse veya üretilemiyorsa projenin YouTube kapak görseline yönlendir
    if proj and proj.get("thumbnail"):
        return RedirectResponse(proj["thumbnail"])

    raise HTTPException(status_code=404, detail="Thumbnail bulunamadı.")

@app.get("/api/clips/{filename}")
def download_clip(filename: str):
    file_path = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Klip dosyası bulunamadı.")
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=filename,
        content_disposition_type="inline",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, must-revalidate"
        }
    )

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/sw.js")
def serve_service_worker():
    sw_file = os.path.join(static_dir, "sw.js")
    if os.path.exists(sw_file):
        return FileResponse(
            sw_file,
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Service-Worker-Allowed": "/"
            }
        )
    raise HTTPException(status_code=404, detail="Service worker bulunamadı.")

@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    file_candidate = os.path.join(static_dir, full_path)
    if full_path and os.path.exists(file_candidate) and os.path.isfile(file_candidate):
        return FileResponse(file_candidate)

    index_candidate = os.path.join(static_dir, "index.html")
    if os.path.exists(index_candidate):
        return FileResponse(
            index_candidate,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-App-Version": VERSION,
                "X-Build-ID": BUILD_ID
            }
        )

    return JSONResponse(
        status_code=200,
        content={"message": "ClipForge API çalışıyor."}
    )
