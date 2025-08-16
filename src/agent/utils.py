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


def generate_diff(old_code, new_code, file_path, highlight=False):
    dmp = dmp_module.diff_match_patch()

    # Generate diff
    diffs = dmp.diff_main(old_code, new_code)

    # Diff cleanup
    dmp.diff_cleanupEfficiency(diffs)

    if not highlight:
        return diffs

    # Rich highlight the diff
    rich_old_text = ""
    rich_new_text = ""
    for diff in diffs:
        if diff[0] == -1:
            rich_old_text += f"[#FC7C7C]{diff[1]}[/]"
        elif diff[0] == 0:
            rich_old_text += diff[1]
            rich_new_text += diff[1]
        elif diff[0] == 1:
            rich_new_text += f"[#7CFCA7]{diff[1]}[/]"

    return rich_old_text, rich_new_text
