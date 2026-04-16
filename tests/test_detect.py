from codex_hotswap.detect import TriggerDetector


def test_trigger_detector_matches_rate_limit() -> None:
    detector = TriggerDetector()
    result = detector.detect("API returned rate limit exceeded for this model")
    assert result.triggered is True
    assert result.pattern is not None


def test_trigger_detector_ignores_normal_output() -> None:
    detector = TriggerDetector()
    result = detector.detect("All tasks completed successfully")
    assert result.triggered is False
    assert result.pattern is None

