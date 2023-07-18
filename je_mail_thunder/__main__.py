# argparse
import argparse
import json
import sys

from je_mail_thunder.utils.exception.exception_tags import mail_thunder_argparse_get_wrong_function
from je_mail_thunder.utils.exception.exceptions import MailThunderArgparseException
from je_mail_thunder.utils.executor.action_executor import execute_action, execute_files
from je_mail_thunder.utils.file_process.get_dir_file_list import get_dir_files_as_list
from je_mail_thunder.utils.json.json_file import read_action_json
from je_mail_thunder.utils.project.create_project_structure import create_project_dir

if __name__ == "__main__":
    try:
        def preprocess_execute_action(file_path: str):
            execute_action(read_action_json(file_path))


        def preprocess_execute_files(file_path: str):
            execute_files(get_dir_files_as_list(file_path))


        def preprocess_read_str_execute_action(execute_str: str):
            execute_str = json.loads(execute_str)
            execute_action(execute_str)


        argparse_event_dict = {
            "execute_file": preprocess_execute_action,
            "execute_dir": preprocess_execute_files,
            "execute_str": preprocess_read_str_execute_action,
            "create_project": create_project_dir,
        }
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-e", "--execute_file",
            type=str, help="choose action file to execute"
        )
        parser.add_argument(
            "-d", "--execute_dir",
            type=str, help="choose dir include action file to execute"
        )
        parser.add_argument(
            "-c", "--create_project",
            type=str, help="create project with template"
        )
        parser.add_argument(
            "--execute_str",
            type=str, help="execute json str"
        )
        args = parser.parse_args()
        args = vars(args)
        for key, value in args.items():
            if value is not None:
                argparse_event_dict.get(key)(value)
        if all(value is None for value in args.values()):
            raise MailThunderArgparseException(mail_thunder_argparse_get_wrong_function)
    except Exception as error:
        print(repr(error), file=sys.stderr)
        sys.exit(1)
