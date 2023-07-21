template_keyword_1: list = [
    ["MT_smtp_later_init"],
    ["MT_smtp_create_message_and_send", {
        "message_content": "test", "message_setting_dict": {
            "Subject": "test_subject",
            "To": "example@gmail.com",
            "From": "example@gmail.com"
        }}
     ],
    ["smtp_quit"]
]

template_keyword_2: list = [
    ["MT_imap_later_init"],
    ["MT_imap_select_mailbox"],
    ["MT_imap_output_all_mail_as_file"]
]

bad_template_1 = [
    ["MT_add_package_to_executor", ["os"]],
    ["os_system", ["python --version"]],
    ["os_system", ["python -m pip --version"]],
]
