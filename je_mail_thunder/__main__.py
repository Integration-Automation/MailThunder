# argparse
import argparse
import json

from je_mail_thunder.smtp.smtp_wrapper import SMTPWrapper
from je_mail_thunder.utils.exception.exception_tags import mail_thunder_login_error
from je_mail_thunder.utils.exception.exceptions import MailThunderArgparseException

if __name__ == "__main__":
    smtp_service = SMTPWrapper()

    argparse_service_function_dict = {
        "send_mail": smtp_service.create_message_and_send,
        "send_mail_with_attach": smtp_service.create_message_with_attach_and_send,
        "login_with_env_or_content": smtp_service.try_to_login_with_env_or_content
    }

    all_param_required_function_list = ["send_mail", "send_mail_with_attach"]

    only_function_param_function_list = [
        "login_with_env_or_content"
    ]

    parser = argparse.ArgumentParser()
    parser.add_argument("--user", help="set email user")
    parser.add_argument("--password", help="set email password")
    parser.add_argument("--function", help="service function", required=True)
    parser.add_argument("--setting", help="service function setting as json")
    args = parser.parse_args()
    args = vars(args)
    if args.get("function") in all_param_required_function_list:
        setting = args.get("setting")
        setting = setting.replace("\"", "").replace("'", '"')
        for param in args.values():
            if param is None:
                raise MailThunderArgparseException(mail_thunder_login_error)
        smtp_service.login(args.get("user"), args.get("password"))
        argparse_service_function_dict.get(args.get("function"))(**json.loads(setting))
    elif args.get("function") in only_function_param_function_list:
        argparse_service_function_dict.get(args.get("function"))()
