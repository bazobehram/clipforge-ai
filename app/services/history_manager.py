import os
import json
import logging
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

class HistoryManager:
    def __init__(self, history_file: Optional[str] = None):
        self.history_file = history_file or settings.HISTORY_FILE
        self._lock = threading.RLock()
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _read_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not os.path.exists(self.history_file):
                return []
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Initial history JSON read failed: {e}. Attempting auto-repair...")
                try:
                    with open(self.history_file, "r", encoding="utf-8") as f:
                        raw = f.read()
                    r_idx = raw.rfind("]")
                    if r_idx != -1:
                        fixed_data = json.loads(raw[:r_idx+1])
                        if isinstance(fixed_data, list):
                            self._write_all(fixed_data)
                            logger.info(f"Successfully auto-repaired history file with {len(fixed_data)} projects!")
                            return fixed_data
                except Exception as repair_e:
                    logger.error(f"Auto-repair failed: {repair_e}")
                    bak_file = f"{self.history_file}.bak"
                    if os.path.exists(bak_file):
                        try:
                            with open(bak_file, "r", encoding="utf-8") as f:
                                return json.load(f)
                        except Exception:
                            pass
                return []

    def _write_all(self, data: List[Dict[str, Any]]):
        with self._lock:
            try:
                temp_file = f"{self.history_file}.tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, self.history_file)
                try:
                    import shutil
                    shutil.copyfile(self.history_file, f"{self.history_file}.bak")
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error writing history file: {e}")

    def list_projects(self) -> List[Dict[str, Any]]:
        projects = self._read_all()
        # En yeniden en eskiye sırala
        projects.sort(key=lambda p: p.get("created_at", ""), reverse=True)
        return projects

    @staticmethod
    def deduplicate_project_candidates(project: Dict[str, Any]) -> bool:
        """
        Proje içerisindeki mükerrer (aynı veya çok yakın zaman aralığına sahip)
        aday kesitleri temizler. Render edilmiş olanlar öncelikli korunur.
        Değişiklik yapıldıysa True döner.
        """
        candidates = project.get("candidates", [])
        if not candidates or len(candidates) < 2:
            return False

        unique_cands = []
        changed = False

        for cand in candidates:
            try:
                c_st = float(cand.get("start_time", 0.0))
                c_et = float(cand.get("end_time", 0.0))
            except (ValueError, TypeError):
                unique_cands.append(cand)
                continue

            c_dur = max(1.0, c_et - c_st)
            c_rendered = bool(cand.get("is_rendered", False))

            dup_idx = None
            for idx, u in enumerate(unique_cands):
                try:
                    u_st = float(u.get("start_time", 0.0))
                    u_et = float(u.get("end_time", 0.0))
                except (ValueError, TypeError):
                    continue
                u_dur = max(1.0, u_et - u_st)

                overlap = max(0.0, min(c_et, u_et) - max(c_st, u_st))
                # Çok yakın zaman damgası (< 5s fark) veya %60'tan fazla örtüşme
                if (abs(c_st - u_st) < 5.0 and abs(c_et - u_et) < 5.0) or (overlap / min(c_dur, u_dur) > 0.60):
                    dup_idx = idx
                    break

            if dup_idx is None:
                unique_cands.append(cand)
            else:
                changed = True
                # Eğer yeni aday render edilmişse ve var olan edilmemişse, render edilmişi koy
                if c_rendered and not unique_cands[dup_idx].get("is_rendered", False):
                    unique_cands[dup_idx] = cand

        if changed:
            project["candidates"] = unique_cands
            return True
        return False

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        for p in self._read_all():
            if p.get("project_id") == project_id:
                if self.deduplicate_project_candidates(p):
                    self.save_project(p)
                return p
        return None

    def save_project(self, project: Dict[str, Any]):
        self.deduplicate_project_candidates(project)
        with self._lock:
            projects = self._read_all()
            pid = project.get("project_id")
            updated = False
            for idx, p in enumerate(projects):
                if p.get("project_id") == pid:
                    projects[idx] = project
                    updated = True
                    break
            if not updated:
                projects.insert(0, project)
            self._write_all(projects)

    def add_rendered_clip(self, project_id: str, clip: Dict[str, Any]):
        with self._lock:
            projects = self._read_all()
            cid = str(clip.get("id"))
            for p in projects:
                if str(p.get("project_id")) == str(project_id):
                    if "rendered_clips" not in p:
                        p["rendered_clips"] = []
                    
                    # Varsa güncelle, yoksa ekle
                    updated = False
                    for idx, c in enumerate(p["rendered_clips"]):
                        if str(c.get("id")) == cid:
                            old_fn = c.get("video_filename")
                            new_fn = clip.get("video_filename")
                            if old_fn and new_fn and old_fn != new_fn:
                                old_path = os.path.join(settings.OUTPUT_DIR, old_fn)
                                if os.path.exists(old_path):
                                    try:
                                        os.remove(old_path)
                                    except Exception as e:
                                        logger.warning(f"Failed to delete obsolete video file {old_path}: {e}")
                            p["rendered_clips"][idx] = clip
                            updated = True
                            break
                    if not updated:
                        p["rendered_clips"].append(clip)

                    # Candidates içindeki is_rendered bayrağını ve yeni süre/url bilgilerini güncelle
                    for cand in p.get("candidates", []):
                        if str(cand.get("id")) == cid:
                            cand["is_rendered"] = True
                            cand["start_time"] = clip.get("start_time", cand.get("start_time"))
                            cand["end_time"] = clip.get("end_time", cand.get("end_time"))
                            cand["duration"] = clip.get("duration", cand.get("duration"))
                            cand["video_filename"] = clip.get("video_filename")
                            cand["video_url"] = clip.get("video_url")
                            cand["rendered_at_ts"] = clip.get("rendered_at_ts")
                            cand["share_urls"] = clip.get("share_urls")
                    break
            self._write_all(projects)

    def update_clip_text(self, project_id: str, clip_id: str, title: str, description: str, hashtags: List[str]) -> bool:
        with self._lock:
            projects = self._read_all()
            found = False
            target_cid = str(clip_id)
            for p in projects:
                if str(p.get("project_id")) == str(project_id):
                    # Hem rendered_clips hem candidates içinde güncelle
                    for c in p.get("rendered_clips", []):
                        if str(c.get("id")) == target_cid:
                            c["title"] = title
                            c["description"] = description
                            if "share_urls" in c and isinstance(c["share_urls"], dict):
                                from app.services.publisher import SocialPublisher
                                c["share_urls"] = SocialPublisher.generate_share_urls(title, description, hashtags, youtube_url=p.get("youtube_url", ""))
                            found = True
                    for cand in p.get("candidates", []):
                        if str(cand.get("id")) == target_cid:
                            cand["title"] = title
                            cand["description"] = description
                            cand["hashtags"] = hashtags
                            found = True
                    break
            if found:
                self._write_all(projects)
            return found

    def mark_clip_shared(self, project_id: str, clip_id: str, platform: str = "native", is_shared: bool = True) -> bool:
        with self._lock:
            projects = self._read_all()
            found = False
            target_cid = str(clip_id)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            for p in projects:
                if str(p.get("project_id")) == str(project_id):
                    for c in p.get("rendered_clips", []):
                        if str(c.get("id")) == target_cid:
                            if "shared_platforms" not in c or not isinstance(c["shared_platforms"], list):
                                c["shared_platforms"] = []
                            if is_shared:
                                c["is_shared"] = True
                                c["shared_at"] = now_str
                                if platform and platform not in c["shared_platforms"]:
                                    c["shared_platforms"].append(platform)
                            else:
                                if platform in c["shared_platforms"]:
                                    c["shared_platforms"].remove(platform)
                                elif platform in ("all", "manual", "native"):
                                    c["shared_platforms"] = []
                                c["is_shared"] = len(c["shared_platforms"]) > 0
                            found = True
                    for cand in p.get("candidates", []):
                        if str(cand.get("id")) == target_cid:
                            if "shared_platforms" not in cand or not isinstance(cand["shared_platforms"], list):
                                cand["shared_platforms"] = []
                            if is_shared:
                                cand["is_shared"] = True
                                cand["shared_at"] = now_str
                                if platform and platform not in cand["shared_platforms"]:
                                    cand["shared_platforms"].append(platform)
                            else:
                                if platform in cand["shared_platforms"]:
                                    cand["shared_platforms"].remove(platform)
                                elif platform in ("all", "manual", "native"):
                                    cand["shared_platforms"] = []
                                c["is_shared"] = len(cand["shared_platforms"]) > 0
                            found = True
                    break
            if found:
                self._write_all(projects)
            return found

    def delete_clip(self, project_id: str, clip_id: str) -> bool:
        with self._lock:
            projects = self._read_all()
            target_cid = str(clip_id)
            for p in projects:
                if str(p.get("project_id")) == str(project_id):
                    rendered = p.get("rendered_clips", [])
                    to_remove = None
                    for c in rendered:
                        cid = str(c.get("id", ""))
                        c_clip_id = str(c.get("clip_id", ""))
                        if cid == target_cid or c_clip_id == target_cid or cid.endswith(f"_{target_cid}") or target_cid.endswith(f"_{cid}"):
                            to_remove = c
                            break
                    if to_remove:
                        rendered.remove(to_remove)
                        filename = to_remove.get("video_filename")
                        if filename:
                            file_path = os.path.join(settings.OUTPUT_DIR, filename)
                            if os.path.exists(file_path):
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    logger.warning(f"Failed to delete video file {file_path}: {e}")

                    # Candidate durumunu sıfırla
                    for cand in p.get("candidates", []):
                        cand_id = str(cand.get("id", ""))
                        if cand_id == target_cid or cand_id.endswith(f"_{target_cid}") or target_cid.endswith(f"_{cand_id}"):
                            cand["is_rendered"] = False
                            cand["video_filename"] = None
                            cand["video_url"] = None

                    self._write_all(projects)
                    return True
            return False

    def delete_project(self, project_id: str) -> bool:
        with self._lock:
            projects = self._read_all()
            target_project = None
            for p in projects:
                if p.get("project_id") == project_id:
                    target_project = p
                    break
            if not target_project:
                return False

            # Bu projeye ait tüm render edilmiş video dosyalarını sil
            for clip in target_project.get("rendered_clips", []):
                filename = clip.get("video_filename")
                if filename:
                    fpath = os.path.join(settings.OUTPUT_DIR, filename)
                    if os.path.exists(fpath):
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass

            # İndirilen ham dosyaları ve transkripti sil
            job_dir = os.path.join(settings.DOWNLOADS_DIR, project_id)
            if os.path.exists(job_dir):
                import shutil
                try:
                    shutil.rmtree(job_dir)
                except Exception:
                    pass

            projects.remove(target_project)
            self._write_all(projects)
            return True
