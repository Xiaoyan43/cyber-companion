from __future__ import annotations

import struct


def estimate_speech_duration_ms(text: str) -> int:
    estimated = len(text.strip()) * 45
    return min(4200, max(1400, estimated))


def generate_silent_wav(duration_ms: int, sample_rate: int = 22050) -> bytes:
    duration_sec = max(duration_ms, 200) / 1000
    num_samples = int(sample_rate * duration_sec)
    bits_per_sample = 16
    num_channels = 1
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    buffer = bytearray()
    buffer.extend(b"RIFF")
    buffer.extend(struct.pack("<I", 36 + data_size))
    buffer.extend(b"WAVE")
    buffer.extend(b"fmt ")
    buffer.extend(
        struct.pack(
            "<IHHIIHH",
            16,
            1,
            num_channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
        )
    )
    buffer.extend(b"data")
    buffer.extend(struct.pack("<I", data_size))
    buffer.extend(b"\x00" * data_size)
    return bytes(buffer)
