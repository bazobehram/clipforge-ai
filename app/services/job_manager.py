import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from app.models import JobStatusEnum

logger = logging.getLogger(__name__)

class JobManager:
    """
    Sunucudaki tüm video indirme, deşifre ve puanlama işlemlerini kalıcı olarak
    (jobs.json) saklar. Sunucu restart edilse dahi işlemler kaybolmaz,
    kesintiye uğrayanlar 'interrupted' olarak işaretlenip tek tıkla tekrar başlatılabilir.
    """

    def __init__(self):
        self.jobs_file = os.path.join(settings.DATA_DIR, "jobs.json")
        self._ensure_file()
        self.recover_on_startup()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.jobs_file), exist_ok=True)
        if not os.path.exists(self.jobs_file):
            with open(self.jobs_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _read_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.jobs_file):
            return []
        try:
            with open(self.jobs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading jobs.json: {e}. Attempting auto-repair...")
            try:
                with open(self.jobs_file, "r", encoding="utf-8") as f:
                    raw = f.read()
                r_idx = raw.rfind("]")
                if r_idx != -1:
                    fixed = json.loads(raw[:r_idx+1])
                    if isinstance(fixed, list):
                        self._write_all(fixed)
                        return fixed
            except Exception:
                pass
            return []

    def _write_all(self, data: List[Dict[str, Any]]):
        try:
            temp = f"{self.jobs_file}.tmp"
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp, self.jobs_file)
        except Exception as e:
            logger.error(f"Error writing jobs.json: {e}")

    def recover_on_startup(self):
        """Sunucu restart edildiğinde yarım kalmış aktif işleri 'interrupted' olarak işaretler."""
        jobs = self._read_all()
        updated = False
        active_statuses = (
            JobStatusEnum.QUEUED.value,
            JobStatusEnum.DOWNLOADING.value,
            JobStatusEnum.TRANSCRIBING.value,
            JobStatusEnum.SCORING.value,
            JobStatusEnum.RENDERING.value
        )
        for j in jobs:
            if j.get("status") in active_statuses:
                j["status"] = JobStatusEnum.INTERRUPTED.value
                j["message"] = "Sunucu yeniden başlatıldığı için işlem kesintiye uğradı. 'Tekrar Başlat' ile devam edebilirsiniz."
                j["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                logger.info(f"Marked interrupted job: {j.get('job_id')} ({j.get('video_title') or j.get('url')})")

        if updated:
            self._write_all(jobs)

    def create_job(
        self,
        job_id: str,
        url: str,
        vertical_mode: str = "blur_background",
        count: int = 10
    ) -> Dict[str, Any]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        job = {
            "job_id": job_id,
            "url": url,
            "status": JobStatusEnum.QUEUED.value,
            "progress": 5,
            "message": "İşlem kuyruğa alındı...",
            "sub_status": "",
            "vertical_mode": vertical_mode,
            "count": count,
            "video_title": None,
            "duration": None,
            "thumbnail": None,
            "created_at": now_str,
            "updated_at": now_str,
            "error": None
        }
        jobs = self._read_all()
        # En başa ekle
        jobs.insert(0, job)
        # Maksimum 60 adet işlem logu sakla
        self._write_all(jobs[:60])
        return job

    def update_job(self, job_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        jobs = self._read_all()
        target = None
        for j in jobs:
            if j.get("job_id") == job_id:
                for k, v in kwargs.items():
                    if hasattr(v, "value"):
                        v = v.value
                    j[k] = v
                j["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                target = j
                break

        if target:
            self._write_all(jobs)
        return target

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        jobs = self._read_all()
        for j in jobs:
            if j.get("job_id") == job_id:
                return j
        return None

    def get_active_job(self) -> Optional[Dict[str, Any]]:
        """Şu an sunucuda gerçekten aktif çalışan işi bulur."""
        jobs = self._read_all()
        active_statuses = (
            JobStatusEnum.QUEUED.value,
            JobStatusEnum.DOWNLOADING.value,
            JobStatusEnum.TRANSCRIBING.value,
            JobStatusEnum.SCORING.value
        )
        for j in jobs:
            if j.get("status") in active_statuses:
                return j
        return None

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = self._read_all()
        # En yeniden en eskiye
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if not job:
            return False
        if job.get("status") in (
            JobStatusEnum.COMPLETED.value,
            JobStatusEnum.FAILED.value,
            JobStatusEnum.CANCELLED.value,
            JobStatusEnum.INTERRUPTED.value
        ):
            return False
        self.update_job(
            job_id,
            status=JobStatusEnum.CANCELLED.value,
            message="İşlem kullanıcı tarafından iptal edildi."
        )
        return True

    def delete_job(self, job_id: str) -> bool:
        jobs = self._read_all()
        initial_len = len(jobs)
        jobs = [j for j in jobs if j.get("job_id") != job_id]
        if len(jobs) != initial_len:
            self._write_all(jobs)
            return True
        return False
