from je_mail_thunder import execute_action

test_list = [
    ["MT_smtp_later_init"],
    ["MT_smtp_create_message_and_send",
        {"message_content": "HELLO",
         "message_setting_dict": {
             "SUBJECT": "TEST",
             "FROM": "zenmailman@gmail.com",
             "TO": "zenmailman@gmail.com"
         }}
     ]
]

execute_action(test_list)
