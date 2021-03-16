import email
import imaplib
import json

imap_host = 'imap.gmail.com'

with open('detail.je', 'r+') as File:
    try:
        detailJson = json.loads(File.read())
        user = detailJson['user']
        password = detailJson['password']
    except Exception as e:
        print(e)

# connect to host using SSL
imap = imaplib.IMAP4_SSL(imap_host)

# login to server
imap.login(user, password)

imap.select('Inbox')

tmp, data = imap.search(None, 'ALL')
for num in data[0].split():
    tmp, data = imap.fetch(num, '(RFC822)')
    msg = email.message_from_string(data[0][1].decode('utf-8'))
    sub = msg.get('subject')
    sub_decode = email.header.decode_header(sub)[0][0]
    if type(sub_decode) is not str:
        print("subject:", sub_decode.decode('utf-8'))
    else:
        print("subject:", sub_decode)

imap.close()
