from __future__ import annotations

import struct


def estimate_speech_duration_ms(text: str) -> int:
    estimated = len(text.strip()) * 45
    return min(4200, max(1400, estimated))


def parse_wav_duration_ms(audio_bytes: bytes) -> int:
    if len(audio_bytes) < 44 or audio_bytes[:4] != b"RIFF" or audio_bytes[8:12] != b"WAVE":
        raise ValueError("Invalid WAV header")

    offset = 12
    byte_rate: int | None = None
    data_size: int | None = None

    while offset + 8 <= len(audio_bytes):
        chunk_id = audio_bytes[offset : offset + 4]
        chunk_size = struct.unpack("<I", audio_bytes[offset + 4 : offset + 8])[0]
        chunk_data_start = offset + 8

        if chunk_id == b"fmt " and chunk_size >= 16 and chunk_data_start + 16 <= len(audio_bytes):
            byte_rate = struct.unpack("<I", audio_bytes[chunk_data_start + 8 : chunk_data_start + 12])[0]
        elif chunk_id == b"data":
            data_size = chunk_size
            break

        offset = chunk_data_start + chunk_size
        if chunk_size % 2 == 1:
            offset += 1

    if byte_rate and data_size:
        return max(1, int((data_size / byte_rate) * 1000))

    sample_rate = struct.unpack("<I", audio_bytes[24:28])[0]
    bits_per_sample = struct.unpack("<H", audio_bytes[34:36])[0]
    num_channels = struct.unpack("<H", audio_bytes[22:24])[0]
    fallback_data_size = struct.unpack("<I", audio_bytes[40:44])[0]
    fallback_byte_rate = sample_rate * num_channels * bits_per_sample // 8
    return max(1, int((fallback_data_size / fallback_byte_rate) * 1000))


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
