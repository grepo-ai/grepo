import uuid
import sqlite3
import re
from langgraph.checkpoint.sqlite import SqliteSaver
import diff_match_patch as dmp_module


def get_checkpointer():
    checkpointer = SqliteSaver(sqlite3.connect("grepo.db", check_same_thread=False))
    return checkpointer


# Create chat sessions
def generate_session_uuid():
    thread_uuid = uuid.uuid4().hex
    print(f"------ New session created with uuid {thread_uuid} ----")
    return thread_uuid


def apply_generated_code(file_path, generated_code):
    # TODO: Complete file edit function
    with open(file_path, "rb+") as file:
        file.write(generated_code.encode("utf-8"))
    return
