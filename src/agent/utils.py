import uuid
import sqlite3
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


# TODO: still not done need fixes and better ideas
def apply_diff(file_path, old_code, new_code):
    "Applies the code diff and makes in-place edits"

    # Get the diffs
    diffs, patches = generate_diff(old_code, new_code, file_path)

    # Create a map with score for each diff
    diff_map = {}
    for diff in diffs:
        for line in diff[1].splitlines():
            if line.strip():
                diff_map[line.strip()] = diff[0]

    # --- No edits to apply ---
    if not diff_map:
        return False

    with (
        open(file_path, "r") as src_file,
        tempfile.NamedTemporaryFile(
            "w", delete=False, dir=os.path.dirname(file_path), encoding="utf-8"
        ) as tmp_file,
    ):
        tmp_name = tmp_file.name
        # TODO: Comments (doc or in-line) are not being handled at all (IMP fix asap) run agent/tools/main.py
        # example to know also to track -> (Linear GREP-22)

        for line_no, line in enumerate(src_file, start=0):
            if line.strip() in diff_map.keys():
                score = diff_map.get(line.strip())

                if score is not None:
                    # Deleted line
                    if score == -1:
                        # (Partial hack for now for handling comments) (Linear GREP-22)
                        if line.strip() in ['"', '"""', "#"]:
                            tmp_file.write(f"{line}")
                        else:
                            del diff_map[line.strip()]
                            continue

                    # Added line (1), No-change in line (0)
                    elif score == 0:
                        tmp_file.write(f"{line}")
                        del diff_map[line.strip()]

            else:
                tmp_file.write(line)

        # Atomic replace operation and safe
        shutil.copystat(file_path, tmp_name, follow_symlinks=False)
        os.replace(tmp_name, file_path)

    return True


def generate_diff(old_code, new_code, file_path, highlight=False):
    "Generates the diff b/w exisiting code in file and generated code change"

    dmp = dmp_module.diff_match_patch()

    # Generate diff
    diffs = dmp.diff_main(old_code, new_code)

    # Diff cleanup human-readble form
    dmp.diff_cleanupSemantic(diffs)

    if not highlight:
        # dmp.diff_cleanupEfficiency(diffs)
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
