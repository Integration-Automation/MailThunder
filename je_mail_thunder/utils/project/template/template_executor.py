executor_template_1: str = \
    """from file_automation import execute_action, read_action_json

execute_action(
    read_action_json(
        r"{temp}"
    )
)
"""

executor_template_2: str = \
    """from file_automation import execute_files, get_dir_files_as_list

execute_files(
    get_dir_files_as_list(
        r"{temp}"
    )
)
"""

bad_executor_template_1: str = \
    """
# This example is primarily intended to remind users of the importance of verifying input.
from file_automation import execute_action, read_action_json
    
execute_action(
    read_action_json(
        r"{temp}"
    )
)
"""