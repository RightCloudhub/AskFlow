"""Document parsers for txt / markdown / plain bytes (PRD §4.8).

Text is decoded strictly: UTF-8 (with or without BOM), UTF-16 with a BOM, then GB18030,
which covers GBK/GB2312 files saved by Chinese Windows. Bytes that fit none of these are
rejected so the document lands as FAILED instead of being indexed as mojibake (D-08).
"""

from __future__ import annotations

import codecs

UTF16_BOMS = (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)
FALLBACK_ENCODINGS = ("utf-8-sig", "gb18030")


class UnsupportedEncodingError(ValueError):
    def __init__(self) -> None:
        super().__init__("unsupported_encoding: save the file as UTF-8 or GBK and re-upload")


def decode_text(data: bytes) -> str:
    if data.startswith(UTF16_BOMS):
        return data.decode("utf-16")
    for encoding in FALLBACK_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnsupportedEncodingError()


def parse_bytes(data: bytes, *, filename: str = "", content_type: str = "") -> str:
    del filename, content_type  # every supported upload is plain text today
    return decode_text(data)
