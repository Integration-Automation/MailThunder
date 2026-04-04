# MailThunder Documentation

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/je_mail_thunder)](https://pypi.org/project/je-mail-thunder/)
[![Read the Docs](https://readthedocs.org/projects/mailthunder/badge/?version=latest)](https://mailthunder.readthedocs.io/)
[![Main README](https://img.shields.io/badge/Main-README-green.svg)](../README.md)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black.svg)](https://github.com/Integration-Automation/MailThunder)

This directory contains the [Read the Docs](https://readthedocs.io/) Sphinx documentation source for **MailThunder**.

For the full project overview, see the [Main README](../README.md).

---

## Documentation Structure

```
docs/
  README.md                              # This file
  Makefile                               # Unix build script
  make.bat                               # Windows build script
  requirements.txt                       # Sphinx dependencies
  source/
    conf.py                              # Sphinx configuration
    index.rst                            # Root page (toctree entry point)
    docs/
      Eng/                               # English documentation
        eng_index.rst                    #   Overview & architecture
        installation.rst                 #   Installation guide
        authentication.rst               #   Authentication setup
        send_google_mail.rst             #   Sending emails (SMTP)
        read_google_mail.rst             #   Reading emails (IMAP)
        scripting_engine.rst             #   JSON scripting engine
        project_templates.rst            #   Project template scaffolding
        cli.rst                          #   Command-line interface
        socket_server.rst                #   TCP socket server
        package_manager.rst              #   Dynamic package loader
        logging.rst                      #   Logging system
        exceptions.rst                   #   Custom exceptions
      Zh/                                # 繁體中文文件
        zh_index.rst                     #   總覽與架構
        installation.rst                 #   安裝指南
        authentication.rst               #   認證設定
        send_google_mail.rst             #   寄送郵件 (SMTP)
        read_google_mail.rst             #   讀取郵件 (IMAP)
        scripting_engine.rst             #   JSON 腳本引擎
        project_templates.rst            #   專案模板
        cli.rst                          #   命令列介面
        socket_server.rst                #   Socket 伺服器
        package_manager.rst              #   套件管理器
        logging.rst                      #   日誌記錄
        exceptions.rst                   #   例外處理
      API/                               # API reference
        api_index.rst                    #   Public exports & module map
        smtp_api.rst                     #   SMTPWrapper API
        imap_api.rst                     #   IMAPWrapper API
        executor_api.rst                 #   Executor API
        utils_api.rst                    #   Utility functions API
```

---

## Building Locally

```bash
pip install -r docs/requirements.txt
cd docs
make html          # Linux / macOS
make.bat html      # Windows
```

Open `docs/build/html/index.html` in your browser.

---

## Read the Docs Configuration

Configured via `.readthedocs.yaml` in the project root:

| Setting | Value |
|---------|-------|
| Build OS | `ubuntu-22.04` |
| Python | `3.11` |
| Sphinx config | `docs/source/conf.py` |
| Theme | `sphinx-rtd-theme` |
