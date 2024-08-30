MailThunder IMAP API
----

.. code-block:: python

    def later_init(self):
        """
        Try to log in
        :return: None
        """

.. code-block:: python

    def try_to_login_with_env_or_content(self):
        """
        Try to find user and password on cwd /mail_thunder_content.json or env var
        :return: None
        """

.. code-block:: python

    def select_mailbox(self, mailbox: str = "INBOX", readonly: bool = False):
        """
        :param mailbox: Mailbox we want to select like INBOX
        :param readonly: Readonly or not
        :return: None
        """

.. code-block:: python

    def search_mailbox(self, search_str: [str, list] = "ALL", charset: str = None) -> list:
        """
        Get all mail detail as list
        :param search_str: Search pattern
        :param charset: Charset pattern
        :return: All mail detail as list [mail_response, mail_decode, mail_content]
        """

.. code-block:: python

    def mail_content_list(
            self, search_str: [str, list] = "ALL", charset: str = None) -> List[Dict[str, Union[str, bytes]]]:
        mail_thunder_logger.info(f"imap_mail_content_list, search_str: {search_str}, charset: {charset}")
        """
        Get all mail content as list
        :param search_str: Search pattern
        :param charset: Charset pattern
        :return: All mail content as list [{"SUBJECT": "mail_subject", "FROM": "mail_from", "TO": "mail_to"}]
        """

.. code-block:: python

    def output_all_mail_as_file(
            self, search_str: [str, list] = "ALL", charset: str = None) -> List[Dict[str, Union[str, bytes]]]:
        mail_thunder_logger.info(f"imap_mail_content_list, search_str: {search_str}, charset: {charset}")
        """
        Get all mail content data and output as file
        :param search_str: Search pattern
        :param charset: Charset pattern
        :return: All mail content as list [{"SUBJECT": "mail_subject", "FROM": "mail_from", "TO": "mail_to"}]
        """

.. code-block:: python

    def quit(self):
        """
        Quit service and close connect
        :return: None
        """
