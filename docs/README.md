# MailThunder Documentation

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/je_mail_thunder)](https://pypi.org/project/je-mail-thunder/)
[![Read the Docs](https://readthedocs.org/projects/mailthunder/badge/?version=latest)](https://mailthunder.readthedocs.io/)
[![Main README](https://img.shields.io/badge/Main-README-green.svg)](../README.md)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black.svg)](https://github.com/Integration-Automation/MailThunder)

This directory contains the [Read the Docs](https://readthedocs.io/) documentation source for **MailThunder**.

For the full project overview, installation guide, quick start, and API reference, see the [Main README](../README.md).

---

## Documentation Structure

```
docs/
  README.md                         # This file
  Makefile                          # Unix build script for Sphinx
  make.bat                          # Windows build script for Sphinx
  requirements.txt                  # Python dependencies for building docs (sphinx-rtd-theme)
  source/
    conf.py                         # Sphinx configuration
    index.rst                       # Documentation root (toctree entry point)
    docs/
      Eng/                          # English documentation
        eng_index.rst               #   English index page
        send_google_mail.rst        #   Guide: Sending emails via SMTP
        read_google_mail.rst        #   Guide: Reading emails via IMAP
      Zh/                           # Traditional Chinese documentation (繁體中文)
        zh_index.rst                #   Chinese index page
        send_google_mail.rst        #   Guide: 使用 SMTP 寄送郵件
        read_google_mail.rst        #   Guide: 使用 IMAP 讀取郵件
      API/                          # API reference documentation
        api_index.rst               #   API index page
        smtp_api.rst                #   SMTP API reference
        imap_api.rst                #   IMAP API reference
```

---

## Building Locally

```bash
pip install -r docs/requirements.txt
cd docs
make html          # Linux / macOS
make.bat html      # Windows
```

Open `docs/build/html/index.html` in your browser to view.

---

## Read the Docs Configuration

Configured via `.readthedocs.yaml` in the project root:

| Setting | Value |
|---------|-------|
| Build OS | `ubuntu-22.04` |
| Python | `3.11` |
| Sphinx config | `docs/source/conf.py` |
| Theme | `sphinx-rtd-theme` |

---

## Contributing to Documentation

1. Create or edit `.rst` files under `docs/source/docs/`
2. Add new files to the relevant `toctree` in the index `.rst`
3. Build locally to verify rendering
4. Push to trigger a Read the Docs rebuild
