from je_mail_thunder.utils.exception.exception_tags import (
    mail_thunder_cant_reformat_json_error,
    mail_thunder_wrong_json_data_error,
    mail_thunder_content_set_compiler_error,
    mail_thunder_content_file_error,
    mail_thunder_content_login_failed,
    mail_thunder_service_file_error,
    mail_thunder_login_error,
    mail_thunder_argparse_get_wrong_function,
    add_command_exception,
    executor_list_error,
    cant_execute_action_error,
    cant_generate_json_report,
    cant_find_json_error,
    cant_save_json_error,
    action_is_null_error,
)


def test_all_tags_are_non_empty_strings():
    tags = [
        mail_thunder_cant_reformat_json_error,
        mail_thunder_wrong_json_data_error,
        mail_thunder_content_set_compiler_error,
        mail_thunder_content_file_error,
        mail_thunder_content_login_failed,
        mail_thunder_service_file_error,
        mail_thunder_login_error,
        mail_thunder_argparse_get_wrong_function,
        add_command_exception,
        executor_list_error,
        cant_execute_action_error,
        cant_generate_json_report,
        cant_find_json_error,
        cant_save_json_error,
        action_is_null_error,
    ]
    for tag in tags:
        assert isinstance(tag, str)
        assert len(tag) > 0
