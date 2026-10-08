"""
Content types and file names of attachments.

Both come from the name alone, with the standard library: the content is not inspected, so a policy built on
them stops a wrong file being sent by accident, not a file renamed on purpose.
"""
import mimetypes
import os
import re

DEFAULT_CONTENT_TYPE = "application/octet-stream"
_FALLBACK_FILENAME = "attachment"
# Path separators, control characters and what Windows refuses in a file name.
_UNSAFE_CHARACTERS = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')
# Names Windows opens as devices, with any extension (``NUL.txt`` is still the null device).
_WINDOWS_DEVICE_NAME = re.compile(r"(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\..*)?", re.IGNORECASE)


def guess_content_type(filename: str) -> str:
    """
    The MIME type a file name suggests.

    :param filename: a file name or path
    :return: the type, or ``application/octet-stream`` when the name suggests none or a compressed encoding
        (``report.txt.gz``)
    """
    content_type, encoding = mimetypes.guess_type(filename)
    if content_type is None or encoding is not None:
        return DEFAULT_CONTENT_TYPE
    return content_type


def file_extension(filename: str) -> str:
    """
    The last extension of a file name, lower-cased and with its dot.

    :param filename: a file name or path
    :return: ``".pdf"`` for ``Report.PDF``, ``".exe"`` for ``report.pdf.exe``, ``""`` without an extension
    """
    return os.path.splitext(os.path.basename(filename))[1].lower()


def safe_filename(filename: object, fallback: str = _FALLBACK_FILENAME) -> str:
    """
    A file name that stays inside the directory it is written to, whatever a mail header asked for.

    Directory parts (of either separator style), control characters, the characters Windows refuses and
    ``..`` are removed or replaced, and a Windows device name (``NUL``, ``COM1``) gets a leading underscore.

    :param filename: the name a message gave, possibly ``None``
    :param fallback: the name used when nothing usable is left
    :return: a bare file name, never empty
    """
    if filename is None:
        return fallback
    name = str(filename).replace("\\", "/").rsplit("/", 1)[-1]
    name = _UNSAFE_CHARACTERS.sub("_", name)
    while ".." in name:
        name = name.replace("..", "_")
    name = name.strip(" .")
    if _WINDOWS_DEVICE_NAME.fullmatch(name):
        name = "_" + name
    return name if name else fallback
