from enum import Enum

class FileAction(Enum):
    SEND_FILE = "send_file"
    RENAME_FILE = "rename_file"
    DELETE_FILE = "delete_file"