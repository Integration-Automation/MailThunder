import imaplib
import json
import pprint

imap_host = 'imap.gmail.com'

with open('detail.je', 'r+') as File:
    try:
        detailJson = json.loads(File.read())
        email = detailJson['email']
        password = detailJson['password']
    except Exception as e:
        print(e)

# connect to host using SSL
imap = imaplib.IMAP4_SSL(imap_host)

# login to server
imap.login(email, password)

imap.select('Inbox')

tmp, data = imap.search(None, 'ALL')
for num in data[0].split():
    tmp, data = imap.fetch(num, '(RFC822)')
    print('Message: {0}\n'.format(num))
    pprint.pprint(data[0][1])
    break
imap.close()
