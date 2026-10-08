"""
The TLS context every mail connection is opened with.

``smtplib.SMTP_SSL`` and ``imaplib.IMAP4_SSL`` fall back to a context that checks neither the server's
certificate nor its host name when they are given none, so the wrappers always give them this one.
"""
import ssl


def verified_client_context() -> ssl.SSLContext:
    """
    A client context that checks the server's certificate chain and its host name against the system's trust
    store and accepts nothing older than TLS 1.2.

    A private certificate authority is trusted by naming it in the ``SSL_CERT_FILE`` or ``SSL_CERT_DIR``
    environment variable, never by turning the check off.

    :return: a new context
    """
    return ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
