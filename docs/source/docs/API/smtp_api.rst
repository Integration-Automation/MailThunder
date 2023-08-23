MailThunder SMTP API
----

.. code-block:: python

    def smtp_later_init(self):
        """
        Try to log in
        :return: None
        """

.. code-block:: python

    @staticmethod
    def smtp_create_message(message_content: str, message_setting_dict: dict, **kwargs):
        """
        Create new EmailMessage instance
        :param message_content: Mail content
        :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
        :param kwargs: EmailMessage setting
        :return: None
        """

.. code-block:: python

    @staticmethod
    def smtp_create_message_with_attach(message_content: str, message_setting_dict: dict,
                                        attach_file: str, use_html: bool = False):
        """
        Create new EmailMessage with attach file instance
        :param message_content: Mail content
        :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
        :param attach_file: File path as str
        :param use_html: Enable HTML format (If attach file is html)
        :return: None
        """

.. code-block:: python

    def smtp_try_to_login_with_env_or_content(self):
        """
        Try to find user and password on cwd /mail_thunder_content.json or env var
        :return: None
        """

.. code-block:: python

    def quit(self):
        """
        Quit service and close connect
        :return: None
        """

.. code-block:: python

    def smtp_create_message_with_attach_and_send(self, message_content: str, message_setting_dict: dict,
                                                 attach_file: str, use_html: bool = False):
        """
        Create new EmailMessage with attach file instance then send EmailMessage instance
        :param message_content: Mail content
        :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
        :param attach_file: File path as str
        :param use_html: Enable HTML format (If attach file is html)
        :return: None
        """

.. code-block:: python

    def smtp_create_message_and_send(self, message_content: str, message_setting_dict: dict, **kwargs):
        """
        Create new EmailMessage instance then send EmailMessage instance
        :param message_content: Mail content
        :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
        :return: None
        """
