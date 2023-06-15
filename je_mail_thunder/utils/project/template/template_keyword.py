template_keyword_1: list = [
    ["smtp_later_init"],
    ["smtp_create_message_and_send", {
        "message_content": "test", "message_setting_dict": {
            "Subject": "test_subject",
            "To": "zenmailman@gmail.com",
            "From": "zenmailman@gmail.com"
        }}
     ],
    ["smtp_quit"]
]

template_keyword_2: list = [
    ["imap_later_init"],
    ["imap_select_mailbox"],
    ["imap_output_all_mail_as_file"]
]

bad_template_1 = [
    ["add_package_to_executor", ["os"]],
    ["os_system", ["python --version"]],
    ["os_system", ["python -m pip --version"]],
]
