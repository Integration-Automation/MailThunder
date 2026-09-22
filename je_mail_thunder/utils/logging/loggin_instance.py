"""The ``Mail Thunder`` logger and the file it writes to.

The log file is ``~/.je_mail_thunder/logs/Mail_Thunder.log`` unless ``MAIL_THUNDER_LOG_FILE`` names
another path (a relative one resolves against the cwd at import time; ``os.devnull`` turns the file
off). It used to be ``Mail_Thunder.log`` in the working directory, opened at import in ``w+`` mode
with the locale encoding, so every import left a file wherever the process started, wiped the
previous run's log, and dropped any record with characters outside the locale code page.

The file is opened on the first record, so importing writes nothing. It is shared by every process
on the account, so it is appended to, each line carries the process id, and it is rotated only when
a process opens it (Windows cannot rename a file another process holds open).
"""
import logging
import os
import sys
import warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path

#: Environment variable that overrides where the log file is written.
LOG_FILE_ENV = "MAIL_THUNDER_LOG_FILE"

#: A file past this size is moved to ``<name>.1`` when a process opens it.
ROTATE_AT_BYTES = 10 * 1024 * 1024


def default_log_file() -> Path:
    """Return the log file path: ``$MAIL_THUNDER_LOG_FILE``, else the home-directory default."""
    configured = os.environ.get(LOG_FILE_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".je_mail_thunder" / "logs" / "Mail_Thunder.log"


def _rotate_if_large(path: Path, limit: int) -> None:
    """Move ``path`` to ``<path>.1`` past ``limit`` bytes; best effort while another process holds it."""
    try:
        if limit <= 0 or not path.is_file() or path.stat().st_size <= limit:
            return
        os.replace(path, path.with_name(path.name + ".1"))
    except OSError:
        return


class MailThunderFileHandler(RotatingFileHandler):
    """Append-mode UTF-8 file handler; a file that cannot be opened becomes ``os.devnull`` with one warning."""

    def __init__(self, filename: str, delay: bool = True) -> None:
        super().__init__(filename=filename, mode="a", encoding="utf-8",
                         errors="backslashreplace", delay=delay)

    def _open(self):
        path = Path(self.baseFilename)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            _rotate_if_large(path, ROTATE_AT_BYTES)
            return super()._open()
        except OSError as error:
            warnings.warn(f"Mail Thunder log file {path} unavailable, file logging off: {error!r}",
                          RuntimeWarning, stacklevel=2)
            return open(os.devnull, self.mode, encoding=self.encoding, errors=self.errors)  # noqa: SIM115


mail_thunder_logger = logging.getLogger("Mail Thunder")
mail_thunder_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(message)s')
# Stream handler
stream_handler = logging.StreamHandler(stream=sys.stderr)
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.WARNING)
mail_thunder_logger.addHandler(stream_handler)
# File handler, opened on the first record
file_handler = MailThunderFileHandler(str(default_log_file()))
file_handler.setFormatter(formatter)
mail_thunder_logger.addHandler(file_handler)
