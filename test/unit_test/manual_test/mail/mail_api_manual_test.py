"""
The core mail API against a real mailbox. It is not collected by the test run: run it by hand, from a directory
that holds mail_thunder_content.json (or with the mail_thunder_* environment variables set):

    python test/unit_test/manual_test/mail/mail_api_manual_test.py                # Gmail, or the OAuth2 provider
    python test/unit_test/manual_test/mail/mail_api_manual_test.py microsoft_graph

It mails the account itself (or the address in MAIL_THUNDER_MANUAL_TEST_TO), stores and deletes one draft, reads
the three newest messages of the inbox and looks twice for new mail, MAIL_THUNDER_MANUAL_TEST_WAIT seconds apart
(20 by default). Every step prints what happened; a step that fails prints its error and the next one still runs.
"""
import os
import sys
import tempfile
import time

from je_mail_thunder import Mail, ProviderHealth

STEPS = []


def step(function):
    """Collect the checks in the order they are written."""
    STEPS.append(function)
    return function


@step
def check_the_connection(mail, _recipient):
    health = ProviderHealth()
    for status in health.probe(mail.providers):
        print("   ", status["provider"], status["state"], status["last_error"])


@step
def send_a_message_with_both_bodies_and_an_attachment(mail, recipient):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as attachment:
        attachment.write("MailThunder manual test 附件\n")
    try:
        sent = mail.send(to=recipient, subject="MailThunder manual test 測試", text="plain body 純文字",
                         html="<p><b>HTML</b> body 內文</p>", attachments=[attachment.name])
        print("    sent as", sent.sender, "to", sent.to)
    finally:
        os.unlink(attachment.name)


@step
def read_the_newest_messages(mail, _recipient):
    for message in mail.get_messages(limit=3):
        print("   ", message.message_id, message.date, message.sender, "|", message.subject,
              "|", [attachment.filename for attachment in message.attachments])


@step
def read_only_unread_messages(mail, _recipient):
    print("    unread:", [message.subject for message in mail.get_messages(limit=3, unread_only=True)])


@step
def store_and_delete_a_draft(mail, recipient):
    draft_id = mail.create_draft(to=recipient, subject="MailThunder manual test draft", text="delete me")
    print("    draft id:", draft_id)
    if draft_id is None:
        print("    the server did not report the draft's id; delete it by hand")
        return
    # The folder is the one the provider chose for drafts: name it when the delete says it is not in INBOX.
    drafts_folder = os.environ.get("MAIL_THUNDER_MANUAL_TEST_DRAFTS", "Drafts")
    mail.delete_message(draft_id, folder=drafts_folder)
    print("    deleted from", drafts_folder)


@step
def look_for_new_mail(mail, _recipient):
    arrived = []
    mail.on("message_received", lambda event: arrived.append(event.message.subject))
    mail.watch("INBOX", start=False)
    print("    first look (baseline):", mail.triggers.poll())
    time.sleep(float(os.environ.get("MAIL_THUNDER_MANUAL_TEST_WAIT", "20")))
    print("    second look:", mail.triggers.poll(), arrived)


def main():
    provider = sys.argv[1] if len(sys.argv) > 1 else None
    with Mail(provider=provider) as mail:
        recipient = os.environ.get("MAIL_THUNDER_MANUAL_TEST_TO") or mail.account.authentication().user
        print("provider:", mail.account.provider, "| recipient:", recipient)
        failed = 0
        for check in STEPS:
            print("-", check.__name__.replace("_", " "))
            try:
                check(mail, recipient)
            except Exception as error:  # pylint: disable=broad-exception-caught  # reason: report and go on
                failed += 1
                print("    FAILED:", repr(error))
    print(f"{len(STEPS) - failed} of {len(STEPS)} steps passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
