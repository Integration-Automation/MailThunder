# MailThunder
MailThunder is a lightweight and flexible email automation tool. It supports SMTP and IMAP4, provides scripting and template features, and makes sending, receiving, and managing email content effortless.

## Notice
- By default, MailThunder uses Google Mail services. You can change the initialization settings to use other providers.
- A configuration file named mail_thunder_content.json must be placed in the current working directory:

``` json
{
  "user": "example@gmail.com",
  "password": "password"
}
```
- Set up an application-specific password:
  - https://support.google.com/accounts/answer/185833
- Enable IMAP:
  - https://support.google.com/mail/answer/7126229?hl=en

## Key features:
- Fast email automation
- SMTP support
- IMAP4 support
- MailThunder scripting
- Automatic export of all email content to files
- Automated email sending
- Automated file sending
- Socket server support
- Script project & template support

## Installation 

```
pip install je_mail_thunder
```

## Requires
- Python 3.9 or later