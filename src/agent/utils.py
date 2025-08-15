import uuid
import sqlite3
import re
from collections import defaultdict
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
    start_pattern = re.compile(r"<START\b([^>]*)>(?s:(.*?))</START>")
    diff_pattern = re.compile(r"<DIFF\b([^>]*)>(?s:(.*?))</DIFF>")
    end_pattern = re.compile(r"<END\b([^>]*)>(?s:(.*?))</END>")

    start_block = b""
    diff_block = b""
    end_block = b""

    for m in start_pattern.finditer(generated_code):
        start_block += m.group(2).encode("utf-8")

    for m in diff_pattern.finditer(generated_code):
        diff_block += m.group(2).encode("utf-8")

    for m in end_pattern.finditer(generated_code):
        end_block += m.group(2).encode("utf-8")

    re_construct_block = start_block + diff_block + end_block

    # --- Open file to apply the code diff  ---
    with open(file_path, "rb+") as file:
        bytes_contents = file.read()

        find_indexes = {}

        if start_block:
            find_indexes["s_start"] = bytes_contents.find(start_block)
            find_indexes["s_end"] = find_indexes["s_start"] + len(start_block)

        if end_block:
            find_indexes["e_start"] = bytes_contents.find(end_block)
            find_indexes["e_end"] = find_indexes["e_start"] + len(end_block)

        # Find diff b/w old and new code
        old_block = bytes_contents[find_indexes["s_start"] : find_indexes["e_end"]]
        new_block = re_construct_block

        # Find diff objects
        dmp = dmp_module.diff_match_patch()
        diff_objs = dmp.diff_main(old_block, new_block)
        # dmp.diff_cleanupSemantic(diff_objs)
        dmp.diff_cleanupEfficiency(diff_objs)

        # Get patch objs
        patch_objs = dmp.patch_make(old_block, diff_objs)

        # Apply the patches
        edited_new_code_block, _ = dmp.patch_apply(patch_objs, old_block)

        # TODO: verify how to save the edited content in file
        # --- Make in-place edit in the file ---
        bytes_contents = (
            bytes_contents[: find_indexes["s_start"]]
            + edited_new_code_block
            + bytes_contents[find_indexes["s_end"] :]
        )

    return re_construct_block
