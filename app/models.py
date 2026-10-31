from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class JobStatusEnum(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    SCORING = "scoring"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"

# ==========================================
# GİRİŞ & YETKİLENDİRME
# ==========================================
class LoginRequest(BaseModel):
    password: str

class LoginResponse(BaseModel):
    success: bool
    token: str
    message: str

# ==========================================
# KLİP VE PROJE MODELLERİ
# ==========================================
class CandidateClip(BaseModel):
    id: str
    title: str
    score: float = Field(..., ge=0, le=100)
    hook_score: float = Field(..., ge=0, le=10)
    flow_score: float = Field(..., ge=0, le=10)
    value_score: float = Field(..., ge=0, le=10)
    start_time: float
    end_time: float
    duration: float
    summary: str = ""
    description: str = ""
    hashtags: List[str] = []
    transcript_snippet: Optional[str] = ""
    is_rendered: bool = False
    video_filename: Optional[str] = None
    video_url: Optional[str] = None
    share_urls: Optional[Dict[str, str]] = None
    source_type: Optional[str] = "ai"  # "ai", "search", "custom"
    source_query: Optional[str] = None
    is_shared: Optional[bool] = False
    shared_at: Optional[str] = None
    shared_platforms: Optional[List[str]] = []
    thumbnail_url: Optional[str] = None

class ProjectRecord(BaseModel):
    project_id: str
    youtube_url: str
    title: str
    duration: float
    thumbnail: str = ""
    created_at: str
    candidates: List[CandidateClip] = []
    rendered_clips: List[CandidateClip] = []

# ==========================================
# İSTEK MODELLERİ
# ==========================================
class AnalyzeRequest(BaseModel):
    url: str
    vertical_mode: Optional[str] = "blur_background"
    count: Optional[int] = 10

class MoreCandidatesRequest(BaseModel):
    project_id: str
    count: Optional[int] = 10

class SearchTopicRequest(BaseModel):
    project_id: str
    query: str

class CustomClipRequest(BaseModel):
    project_id: str
    start_time: float
    end_time: float
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None

class RenderClipRequest(BaseModel):
    project_id: str
    candidate_id: str
    vertical_mode: Optional[str] = "blur_background"
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class RegenerateMetaRequest(BaseModel):
    project_id: str
    candidate_id: str
    current_title: Optional[str] = None
    style: Optional[str] = "viral_hook"

class UpdateClipRequest(BaseModel):
    project_id: str
    clip_id: str
    title: str
    description: str
    hashtags: List[str]

class MarkSharedRequest(BaseModel):
    project_id: str
    clip_id: str
    platform: Optional[str] = "native"
    is_shared: Optional[bool] = True

# ==========================================
# GERİYE DÖNÜK UYUMLULUK MODELLERİ
# ==========================================
class ProcessRequest(BaseModel):
    url: str
    max_clips: Optional[int] = 4
    vertical_mode: Optional[str] = "blur_background"
    custom_instructions: Optional[str] = None

class ClipMetadata(BaseModel):
    id: str
    title: str
    score: float = Field(..., ge=0, le=100)
    hook_score: float = Field(..., ge=0, le=10)
    flow_score: float = Field(..., ge=0, le=10)
    value_score: float = Field(..., ge=0, le=10)
    start_time: float
    end_time: float
    duration: float
    summary: str
    description: str
    hashtags: List[str]
    video_filename: str
    video_url: str
    share_urls: Dict[str, str]

class JobResponse(BaseModel):
    job_id: str
    status: JobStatusEnum
    progress: int = 0
    message: str = ""
    video_title: Optional[str] = None
    original_duration: Optional[float] = None
    candidates: List[CandidateClip] = []
    clips: List[ClipMetadata] = []
    error: Optional[str] = None

# ==========================================
# AKILLI FRAGMAN & VİDEO ÖZET MODELLERİ
# ==========================================
class TrailerStatusEnum(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    SELECTING = "selecting"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"

class TrailerScene(BaseModel):
    act_number: int
    chapter_title: str
    start_time: float
    end_time: float
    duration: float
    summary: str = ""
    quote: str = ""

class TrailerRequest(BaseModel):
    project_id: Optional[str] = None
    url: Optional[str] = None
    target_duration: Optional[int] = 60
    aspect_ratio: Optional[str] = "9:16"  # "9:16" veya "16:9"
    crop_mode: Optional[str] = "blur_background"  # "blur_background" veya "crop_center"
    style: Optional[str] = "cinematic"    # "cinematic" (ara kartlı) veya "dynamic" (hızlı geçişli)

class TrailerResponse(BaseModel):
    trailer_id: str
    project_id: Optional[str] = None
    status: str
    progress: int = 0
    message: str = ""
    video_title: str = ""
    scenes: List[TrailerScene] = []
    video_filename: Optional[str] = None
    video_url: Optional[str] = None
    duration: Optional[float] = None
    aspect_ratio: Optional[str] = "9:16"
    crop_mode: Optional[str] = "blur_background"
    created_at: Optional[str] = None
    error: Optional[str] = None

