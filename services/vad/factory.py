"""VAD factory with Silero → Energy fallback."""

from __future__ import annotations

import logging

from core.interfaces.vad import IVAD
from infrastructure.config import UtteranceConfig
from services.vad.energy_vad import EnergyVAD

logger = logging.getLogger(__name__)


def create_vad(config: UtteranceConfig, *, sample_rate: int = 16000) -> IVAD:
    if config.use_silero_vad:
        try:
            import torch  # noqa: F401

            from services.vad.silero_vad import SileroVAD

            logger.info("Using SileroVAD")
            return SileroVAD(
                sample_rate=sample_rate,
                frame_ms=config.vad_frame_ms,
                threshold=config.vad_threshold,
            )
        except Exception:
            logger.warning("torch not installed; SileroVAD unavailable")

    logger.info("Falling back to EnergyVAD")
    return EnergyVAD(
        sample_rate=sample_rate,
        frame_ms=config.vad_frame_ms,
        energy_threshold=config.energy_threshold,
    )
