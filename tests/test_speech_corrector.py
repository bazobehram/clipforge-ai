import pytest
from app.services.speech_corrector import SpeechSlipCorrector

def test_speech_corrector_direct_replacements():
    words = [
        {"word": "satran", "start": 1.0, "end": 1.5},
        {"word": "maçıydı.", "start": 1.6, "end": 2.0},
        {"word": "Herkez", "start": 2.1, "end": 2.5},
        {"word": "farketti.", "start": 2.6, "end": 3.0}
    ]
    corrected = SpeechSlipCorrector.correct_words(words)
    assert corrected[0]["word"] == "satranç"
    assert corrected[0]["start"] == 1.0
    assert corrected[0]["end"] == 1.5

    assert corrected[2]["word"] == "Herkes"
    assert corrected[3]["word"] == "fark etti."

def test_speech_corrector_contextual_rules():
    # 'uşun uçup uçmadığını' bağlamında 'uşun' -> 'kuşun'
    words = [
        {"word": "O", "start": 10.0, "end": 10.2},
        {"word": "uşun", "start": 10.3, "end": 10.6},
        {"word": "uçup", "start": 10.7, "end": 11.0},
        {"word": "uçmadığını", "start": 11.1, "end": 11.6},
        {"word": "gördük.", "start": 11.7, "end": 12.0}
    ]
    corrected = SpeechSlipCorrector.correct_words(words)
    assert corrected[1]["word"] == "kuşun"
    assert corrected[1]["start"] == 10.3
    assert corrected[1]["end"] == 10.6

def test_speech_corrector_stutter_cleaning():
    words = [
        {"word": "ko-konuşacağız.", "start": 5.0, "end": 5.8},
        {"word": "ya-yapay", "start": 5.9, "end": 6.3},
        {"word": "zeka", "start": 6.4, "end": 6.8}
    ]
    corrected = SpeechSlipCorrector.correct_words(words)
    assert corrected[0]["word"] == "konuşacağız."
    assert corrected[1]["word"] == "yapay"

def test_speech_corrector_turkish_casing_and_punctuation():
    words = [
        {"word": "UŞUN...", "start": 1.0, "end": 1.5},
        {"word": "uçup", "start": 1.6, "end": 2.0},
        {"word": "SATRAN!", "start": 2.1, "end": 2.5},
        {"word": "Uşun?", "start": 2.6, "end": 3.0},
        {"word": "uçtu.", "start": 3.1, "end": 3.5}
    ]
    corrected = SpeechSlipCorrector.correct_words(words)
    assert corrected[0]["word"] == "KUŞUN..."
    assert corrected[2]["word"] == "SATRANÇ!"
    assert corrected[3]["word"] == "Kuşun?"

def test_speech_corrector_empty_and_corrupt_inputs():
    assert SpeechSlipCorrector.correct_words([]) == []
    corrupt = [
        {"word": ""},
        {"word": "   "},
        {"word": "!?."},
        {"word": "123"}
    ]
    res = SpeechSlipCorrector.correct_words(corrupt)
    assert len(res) == 4

def test_speech_corrector_expanded_lexicon():
    words = [
        {"word": "malesef", "start": 0.0, "end": 0.5},
        {"word": "herşey", "start": 0.6, "end": 1.0},
        {"word": "ahçı", "start": 1.1, "end": 1.5}
    ]
    res = SpeechSlipCorrector.correct_words(words)
    assert res[0]["word"] == "maalesef"
    assert res[1]["word"] == "her şey"
    assert res[2]["word"] == "aşçı"
