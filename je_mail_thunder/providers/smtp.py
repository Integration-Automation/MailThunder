"""
Sending through an SMTP server, with MailThunder's SMTP wrappers as the connection (always over TLS).
"""
import smtplib

from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.core.rfc822 import to_email_message
from je_mail_thunder.providers.base import MailSender
from je_mail_thunder.providers.session import WrapperProvider
from je_mail_thunder.smtp.smtp_wrapper import SMTPStartTLSWrapper, SMTPWrapper
from je_mail_thunder.utils.exception.exceptions import MailThunderProviderException, MailThunderSendException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

_NOOP_OK = 250


class SMTPProvider(WrapperProvider, MailSender):
    """Sends mail over SMTP: implicit TLS, or ``STARTTLS`` when the account's servers ask for it."""

    name = "smtp"

    def _connect(self):
        servers = self._account.resolved_servers
        if not servers.smtp_host:
            raise MailThunderProviderException("the account has no SMTP server")
        wrapper = SMTPStartTLSWrapper if servers.smtp_starttls else SMTPWrapper
        return wrapper(servers.smtp_host, servers.port)

    def _ping(self, client) -> None:
        status, _ = client.noop()
        if status != _NOOP_OK:
            raise smtplib.SMTPServerDisconnected(f"NOOP answered {status}")

    def _disconnect(self, client, alive: bool) -> None:
        if alive:
            client.quit()
        else:
            client.close()

    def _is_lost(self, error: Exception) -> bool:
        return isinstance(error, smtplib.SMTPServerDisconnected) or not isinstance(error, smtplib.SMTPException)

    def send(self, message: MailMessage) -> None:
        """
        Send a message. It is not sent twice: a failure while sending is reported, never retried.

        :param message: a message that passed :func:`~je_mail_thunder.core.message.check_outgoing`
        :return: None
        :raises MailThunderSendException: the server refused the message, or some of its recipients (``refused``)
        :raises MailThunderConnectionException: the server could not be reached, or the connection was lost
        :raises MailThunderAuthenticationException: there are no credentials, or the server refused them
        """
        mail_thunder_logger.info(
            f"smtp provider, send: {len(message.recipients)} recipients, {len(message.attachments)} attachments")
        email_message = to_email_message(message)
        client = self._live_client()
        try:
            refused = client.send_message(email_message)
        except smtplib.SMTPRecipientsRefused as error:
            raise MailThunderSendException("the smtp server refused every recipient", error.recipients) from error
        except self._server_errors as error:
            raise self._failure("the message", error, MailThunderSendException) from error
        if refused:
            raise MailThunderSendException(
                f"the message was sent, but the smtp server refused {len(refused)} of its recipients", refused)
