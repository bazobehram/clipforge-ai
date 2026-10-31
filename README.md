# ⚡ ClipForge AI — Viral Shorts, Reels & Smart Video Trailer Studio

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Faster-Whisper](https://img.shields.io/badge/Whisper-Word--Level%20ASR-74AA9C?logo=openai&logoColor=white)](https://github.com/SYSTRAN/faster-whisper)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-9%3A16%20%26%20ASS%20Subtitles-007808?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![PWA Ready](https://img.shields.io/badge/PWA-Mobile%20Ready-5A0FC8?logo=pwa&logoColor=white)](#)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./LICENSE)

**ClipForge AI** is a full-stack, mobile-first Progressive Web App (PWA) and automated video production studio that transforms long-form YouTube videos into high-retention **9:16 vertical clips** and **multi-act cinematic video trailers** for **YouTube Shorts, Instagram Reels, TikTok, X (Twitter), and Bluesky**.

---

## ✨ Key Features

### 1. Automated YouTube Ingestion & Word-Level Transcription
* **Smart URL Sanitizer & Downloader (`VideoDownloader`):** Powered by `yt-dlp`, automatically strips tracking/playlist parameters, supports standard YouTube videos, Shorts, and `youtu.be` links, and extracts 16 kHz mono PCM audio for transcription.
* **Hybrid Cloud + Local Failsafe ASR (`AudioTranscriber`):** Supports local `faster-whisper` (`base`, `small`, `large-v3-turbo` with `int8` CPU optimization and VAD filtering) as well as cloud Whisper APIs (Groq / OpenAI). If cloud rate limits (`429`) or network errors occur, it automatically falls back to local `faster-whisper` without interrupting the job.
* **Contextual Speech-Slip & Stutter Corrector (`SpeechSlipCorrector`):** Cleans speaker stutters (e.g., `ko-konuşacağız` → `konuşacağız`), fixes common phonetic transcription errors using an 8-word sliding context window, and preserves exact word-level `start` and `end` timestamps.

### 2. AI Virality Scoring & Semantic Topic Search
* **Multi-Metric Virality Scorer (`ContentScorer`):** Uses OpenAI-compatible LLMs (Pollinations, Ollama, Groq, OpenAI, DeepSeek) with a deterministic NLP heuristic fallback to evaluate transcript segments on:
  * **Hook Score (`0–10`):** Attention-grabbing opening strength.
  * **Flow Score (`0–10`):** Narrative pacing and coherence.
  * **Value Score (`0–10`):** Information density and takeaway impact.
  * **Overall Virality (`0–100`):** Weighted ranking with automatic title cleaning, boilerplate CTA removal, and smart domain-aware hashtag generation.
* **Topic Search & Custom Time-Range Clips:** Search inside any video transcript by keyword/topic or manually specify custom start/end timestamps to generate targeted clips on demand.

### 3. Safe-Zone Karaoke Subtitles & Lip-Sync 9:16 Rendering
* **Word-Level Karaoke ASS Subtitles (`VideoEditor`):** Generates 1080×1920 `.ass` subtitle tracks positioned inside the TikTok/Reels/Shorts UI safe zone (`MarginV: 560`), featuring active-word electric-yellow pop highlighting (`\fscx108\fscy108`) and automatic contextual keyword emojis.
* **Sentence-Boundary Snapping:** Automatically aligns clip start/end cut points to natural sentence endings and speech pauses so speakers are never cut off mid-word.
* **Zero-Drift Lip-Sync & 5× Faster Blur Rendering:** Uses `setpts=PTS-STARTPTS` and `aresample=async=1:first_pts=0` with smooth audio fade-in/out filters to guarantee frame-accurate audio-video sync, plus a downscaled `270×480` boxblur pipeline for rapid `blur_background` or `crop_center` rendering.

### 4. Multi-Act Smart Video Trailer Generator
* **Chronological Story Arc Synthesis (`TrailerGenerator`):** Analyzes long videos and selects 3–6 chronological acts (Hook, Setup, Climax, Conclusion) scaled to your target duration (`30s`–`180s`).
* **Cinematic & Dynamic Styles:** Supports `cinematic` mode (with chapter title cards between acts) and `dynamic` mode (fast-cut transitions) in both `9:16` vertical and `16:9` widescreen formats.

### 5. Mobile PWA & One-Tap Social Publishing
* **Installable Mobile Studio:** Includes Web App Manifest (`manifest.json`), Service Worker (`sw.js`), and iOS/Android home-screen icons.
* **Deep-Link Social Publisher (`SocialPublisher`):** Generates ready-to-post captions, character-counted X/Bluesky posts that always preserve the source YouTube link and hashtags, and mobile app deep links (`instagram://camera`, `snssdk1233://`, `vnd.youtube://`, `twitter://post`).
* **Persistent Job & History Recovery (`JobManager` & `HistoryManager`):** Atomic JSON storage with automatic corruption repair and interrupted-job recovery across server restarts.

---

## 🏗️ Architecture & Project Structure

```
clipforge/
├── app/
│   ├── main.py                      # FastAPI application, auth middleware & REST endpoints
│   ├── config.py                    # Environment configuration loader
│   ├── models.py                    # Pydantic request/response schemas
│   ├── version.py                   # Release version & build metadata
│   ├── services/
│   │   ├── downloader.py            # yt-dlp video downloader & 16kHz WAV extractor
│   │   ├── transcriber.py           # Hybrid faster-whisper + Cloud Whisper ASR engine
│   │   ├── speech_corrector.py      # Contextual speech-slip & stutter correction engine
│   │   ├── scorer.py                # LLM & NLP virality scorer, title cleaner & hashtag generator
│   │   ├── video_editor.py          # FFmpeg 9:16 renderer & karaoke ASS subtitle generator
│   │   ├── trailer_generator.py     # Multi-act chronological trailer synthesizer
│   │   ├── publisher.py             # Social media caption formatter & mobile deep-link builder
│   │   ├── history_manager.py       # Thread-safe project & clip persistence with auto-repair
│   │   └── job_manager.py           # Background job state tracker & startup recovery
│   └── static/                      # Mobile-first dark-mode PWA frontend (HTML5/JS/Tailwind/SW)
├── scripts/
│   ├── generate_icons.py            # Vector SVG & multi-size PWA icon generator
│   └── publish.py                   # Version & cache-busting build utility
├── tests/                           # 49 Pytest unit & integration tests
├── data/                            # Runtime storage (downloads, output, temp, trailers, JSON DB)
├── Dockerfile                       # Production container image (Python 3.11 + FFmpeg + Fonts)
└── docker-compose.yml               # Single-command Docker Compose deployment
```

---

## 🚀 Getting Started

### Option 1: Run with Docker (Recommended)

Make sure [Docker](https://docs.docker.com/get-docker/) and Docker Compose are installed.

```bash
# 1. Clone the repository
git clone https://github.com/bazobehram/clipforge-ai.git
cd clipforge-ai

# 2. Create your .env configuration from the example template
cp .env.example .env

# 3. Edit .env to set your AUTH_PASSWORD and LLM_API_KEY (or local Ollama URL)
nano .env

# 4. Build and start the container
docker compose up -d --build
```

Open **`http://localhost:8000`** in your browser and log in with the `AUTH_PASSWORD` configured in `.env`.

---

### Option 2: Local Development Setup

#### Prerequisites
* **Python 3.10+**
* **FFmpeg** (`ffmpeg` and `ffprobe` installed and available in `PATH`)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows PowerShell

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env

# 4. Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ⚙️ Environment Variables (`.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | HTTP server port |
| `AUTH_PASSWORD` | `change_me_in_production` | Admin password required to log into the studio |
| `AUTH_SECRET` | `change_this_secret_key...` | HMAC secret key used to sign session tokens |
| `LLM_BASE_URL` | `https://gen.pollinations.ai/v1` | OpenAI-compatible API base URL (Pollinations, Ollama, Groq, OpenAI) |
| `LLM_API_KEY` | `your_api_key_here` | API key for the LLM provider |
| `LLM_MODEL` | `deepseek/deepseek-v4-flash` | Model identifier used for clip scoring and trailer generation |
| `WHISPER_TYPE` | `local` | `local` (`faster-whisper`), `groq`, `openai`, or `auto` |
| `WHISPER_MODEL_SIZE` | `base` | Local Whisper model (`base`, `small`, `large-v3-turbo`) |
| `VERTICAL_MODE` | `blur_background` | Default framing (`blur_background` or `crop_center`) |

---

## 🔌 Core API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Authenticate with `AUTH_PASSWORD` and receive a session token/cookie. |
| `POST` | `/api/analyze` | Download a YouTube URL, transcribe audio, and score viral clip candidates. |
| `POST` | `/api/render-clip` | Render a candidate or custom time range into a subtitled 9:16 MP4 clip. |
| `POST` | `/api/search-topic` | Search a project's transcript for a specific topic and generate matching clips. |
| `POST` | `/api/trailer/generate` | Generate a multi-act chronological video trailer (`9:16` or `16:9`). |
| `GET` | `/api/projects` | List analyzed video projects, candidates, and rendered clips. |
| `GET` | `/api/trailers` | List generated smart video trailers. |

---

## 🧪 Running Tests

ClipForge AI includes **49 unit and integration tests** covering API endpoints, speech-slip correction, sentence-boundary snapping, lip-sync filter alignment, virality scoring, smart hashtags, and history deduplication:

```bash
pytest -v
```

---

## 📄 License

This project is free software: you can redistribute it and/or modify it under the terms of the **[GNU General Public License v3.0](./LICENSE)** as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
