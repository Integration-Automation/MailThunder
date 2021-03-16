import imaplib
import json

mail = imaplib.IMAP4_SSL('imap.gmail.com')
with open('detail.je', 'r+') as File:
    try:
        detailJson = json.loads(File.read())
        email = detailJson['email']
        password = detailJson['password']
    except Exception as e:
        print(e)
mail.login(email, password)
mail.list()
mail.select("inbox")
result, data = mail.search(None, "ALL")
ids = data[0]
id_list = ids.split()
latest_email_id = id_list[-1]
result, data = mail.fetch(latest_email_id, "(RFC822)")
raw_email = data[0][1]
print(raw_email)
