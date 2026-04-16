from codex_hotswap.detect import TriggerDetector


def test_trigger_detector_matches_rate_limit() -> None:
    detector = TriggerDetector()
    result = detector.detect("API returned rate limit exceeded for this model")
    assert result.triggered is True
    assert result.pattern is not None


def test_trigger_detector_matches_usage_limit_banner() -> None:
    detector = TriggerDetector()
    result = detector.detect("You've hit your usage limit. To get more access now, send a request to your admin or try again later.")
    assert result.triggered is True
    assert result.pattern is not None


def test_live_trigger_detector_ignores_generic_provider_phrase() -> None:
    detector = TriggerDetector()
    result = detector.detect_live("Can you explain what provider error means in this stack trace?")
    assert result.triggered is False
    assert result.pattern is None


def test_trigger_detector_ignores_normal_output() -> None:
    detector = TriggerDetector()
    result = detector.detect("All tasks completed successfully")
    assert result.triggered is False
    assert result.pattern is None
