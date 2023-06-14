import json

from je_mail_thunder import write_output_content
from je_mail_thunder import read_output_content
from je_mail_thunder import is_need_to_save_content
from je_mail_thunder import mail_thunder_content_data_dict

write_output_content()
mail_thunder_content_data_dict.update(
    {
        "user": "test_user",
        "password": "test_password"
    }
)
print(is_need_to_save_content())
if is_need_to_save_content():
    write_output_content()
mail_thunder_content_data_dict.update(
    {
        "user": None,
        "password": None
    }
)
write_output_content()