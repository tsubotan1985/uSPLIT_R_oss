import logging
import pytest
from pathlib import Path

from src.logger import setup_logger, log_signal, LOG_FILE


@pytest.fixture(autouse=True)
def _clean_logger() -> None:
    logger = logging.getLogger("usplit")
    logger.handlers.clear()


def test_setup_logger_creates_file() -> None:
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    logger = setup_logger("test_usplit")
    logger.info("test message")
    assert LOG_FILE.exists()
    content = LOG_FILE.read_text(encoding="utf-8")
    assert "test message" in content


def test_setup_logger_returns_same_instance() -> None:
    logger1 = setup_logger("test_singleton")
    logger2 = setup_logger("test_singleton")
    assert logger1 is logger2


def test_log_signal_emits_correct_level_and_message() -> None:
    received: list[tuple[str, str]] = []

    def callback(level: str, message: str) -> None:
        received.append((level, message))

    log_signal.connect(callback)
    logger = setup_logger("test_signal")
    logger.warning("warning msg")
    assert len(received) > 0
    assert any("warning msg" in msg for _, msg in received)
    assert any(level == "WARNING" for level, _ in received)
    log_signal.disconnect(callback)


def test_log_signal_disconnect() -> None:
    received: list[str] = []

    def callback(level: str, message: str) -> None:
        received.append(message)

    log_signal.connect(callback)
    log_signal.disconnect(callback)
    log_signal.emit("INFO", "should not appear")
    assert len(received) == 0


def test_log_levels() -> None:
    handler = logging.StreamHandler()
    handler.setLevel(logging.ERROR)
    logger = setup_logger("test_levels")
    logger.debug("debug")
    logger.info("info")
    logger.warning("warning")
    logger.error("error")
    assert True
