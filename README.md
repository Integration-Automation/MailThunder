### MailThunder

[![Downloads](https://static.pepy.tech/badge/je-mail-thunder)](https://pepy.tech/project/je-mail-thunder)

[![MailThunder Stable Python3.8](https://github.com/Intergration-Automation-Testing/MailThunder/actions/workflows/mail_thunder_stable_python3_8.yml/badge.svg)](https://github.com/Intergration-Automation-Testing/MailThunder/actions/workflows/mail_thunder_stable_python3_8.yml)

[![MailThunder Stable Python3.9](https://github.com/Intergration-Automation-Testing/MailThunder/actions/workflows/mail_thunder_stable_python3_9.yml/badge.svg)](https://github.com/Intergration-Automation-Testing/MailThunder/actions/workflows/mail_thunder_stable_python3_9.yml)

[![MailThunder Stable Python3.10](https://github.com/Intergration-Automation-Testing/MailThunder/actions/workflows/mail_thunder_stable_python3_10.yml/badge.svg)](https://github.com/Intergration-Automation-Testing/MailThunder/actions/workflows/mail_thunder_stable_python3_10.yml)

[![MailThunder Stable Python3.11](https://github.com/Intergration-Automation-Testing/MailThunder/actions/workflows/mail_thunder_stable_python3_11.yml/badge.svg)](https://github.com/Intergration-Automation-Testing/MailThunder/actions/workflows/mail_thunder_stable_python3_11.yml)

### Documentation
 
Docs: <https://mailthunder.readthedocs.io/en/latest/>

### Notice
* Default is using Google service provide, but you can change init setting to choose what service provide you want to use.
* We need set the mail_thunder_content.json on current working dir.
``` json
{
  "user": "example@gmail.com",
  "password": "password"
}
```
* Set application password:
  * https://support.google.com/accounts/answer/185833
* Enable IMAP:
  * https://support.google.com/mail/answer/7126229?hl=en
---

> Project Kanban \
> https://github.com/orgs/Integration-Automation/projects/2/views/1
> * Quickly Mail automation.
> * SMTP support.
> * IMAP4 support.
> * Mail Thunder script.
> * Automatically output all mail content as a file.
> * Automatically send mail.
> * Automatically send file.
> * Socket server.
> * Script Project & Template support.

## install 

```
pip install je_mail_thunder
```

## Requires

```
python 3.9 or later
```