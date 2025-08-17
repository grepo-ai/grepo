import uuid
import sqlite3
import re
import os
import tempfile
import shutil


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


def apply_diff(file_path, old_code, new_code):
    "Applies the code diff to the file"

    old_code = old_code.strip()
    new_code = new_code.strip()

    # Get the diffs
    diffs, patches = generate_diff(old_code, new_code, file_path)

    # Apply diff to old code
    dmp = dmp_module.diff_match_patch()
    patched_code, _ = dmp.patch_apply(patches, old_code)

    # Write the code to new file and replace with old file
    patched_code_lines = patched_code.splitlines()
    old_code_lines = old_code.splitlines()

    write_new_line_count = 0
    skip_lines = 0
    with (
        open(file_path, "r") as src_file,
        tempfile.NamedTemporaryFile(
            "w", delete=False, dir=os.path.dirname(file_path), encoding="utf-8"
        ) as tmp_file,
    ):
        tmp_name = tmp_file.name

        for line_no, line in enumerate(src_file, start=0):
            new_line = "\n" if line.endswith("\n") else ""
            stripped_line = line[:-1] if new_line else line

            if stripped_line == old_code_lines[0]:
                while write_new_line_count < len(patched_code_lines):
                    tmp_file.write(f"{patched_code_lines[write_new_line_count]}\n")
                    write_new_line_count += 1

                # Skip lines for maximum length b/w old_code and patched code
                # as we have already written the patched code so we need to skip lines from exisitng file
                # to avoid inconsistency in data
                skip_lines = max(len(old_code_lines), write_new_line_count) + line_no

            elif skip_lines and line_no < skip_lines:
                continue

            else:
                tmp_file.write(stripped_line + new_line)

        if write_new_line_count > 0:
            # Atomic replace operation and safe
            shutil.copystat(file_path, tmp_name, follow_symlinks=False)
            os.replace(tmp_name, file_path)
        else:
            os.unlink(tmp_name)

    return True if write_new_line_count > 0 else False


def generate_diff(old_code, new_code, file_path, highlight=False):
    "Generates the diff b/w exisiting code in file and generated code change"

    dmp = dmp_module.diff_match_patch()

    # Generate diff
    diffs = dmp.diff_main(old_code, new_code)

    # Diff cleanup
    dmp.diff_cleanupEfficiency(diffs)

    if not highlight:
        patches = dmp.patch_make(old_code, diffs)
        return diffs, patches

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
