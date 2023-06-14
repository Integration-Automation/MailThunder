import logging
import sys

mail_thunder_logger = logging.getLogger("Mail Thunder")
mail_thunder_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
# Stream handler
stream_handler = logging.StreamHandler(stream=sys.stderr)
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.WARNING)
mail_thunder_logger.addHandler(stream_handler)
# File handler
file_handler = logging.FileHandler(filename="Mail_Thunder.log", mode="w+")
file_handler.setFormatter(formatter)
mail_thunder_logger.addHandler(file_handler)

