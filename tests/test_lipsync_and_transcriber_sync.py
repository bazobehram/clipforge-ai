import pytest
from app.services.speech_corrector import SpeechSlipCorrector
from app.services.video_editor import VideoEditor
from app.services.trailer_generator import TrailerGenerator

def test_transcriber_speech_slip_correction_logic():
    segments = [
        {
            "id": 0,
            "start": 10.0,
            "end": 14.0,
            "text": "uşun uçup uçmadığını gördüm",
            "words": [
                {"word": "uşun", "start": 10.0, "end": 10.5},
                {"word": "uçup", "start": 10.6, "end": 11.2},
                {"word": "uçmadığını", "start": 11.3, "end": 12.0},
                {"word": "gördüm", "start": 12.1, "end": 12.6}
            ]
        }
    ]
    
    for seg in segments:
        if seg.get("words"):
            seg["words"] = SpeechSlipCorrector.correct_words(seg["words"])
            seg["text"] = " ".join(w["word"] for w in seg["words"])
            
    assert segments[0]["words"][0]["word"] == "kuşun"
    assert segments[0]["words"][0]["start"] == 10.0
    assert segments[0]["text"] == "kuşun uçup uçmadığını gördüm"

def test_video_editor_lipsync_filter_pts_alignment():
    import inspect
    source = inspect.getsource(VideoEditor.cut_and_convert_vertical)
    
    assert "setpts=PTS-STARTPTS" in source
    assert "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS" in source
    assert "'-r', '30'" in source or '"-r", "30"' in source

def test_trailer_generator_lipsync_filter_pts_alignment():
    import inspect
    source = inspect.getsource(TrailerGenerator.render_cinematic_trailer)
    
    assert "setpts=PTS-STARTPTS" in source
    assert "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS" in source
