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
def generate_session_uuid(console):
    thread_uuid = uuid.uuid4().hex
    console.print(f"[#7CFCA7]session id - {thread_uuid}[/]")
    return thread_uuid


def apply_diff(file_path, old_code, new_code):
    "Applies the code diff by making in-place edits"

    dmp = dmp_module.diff_match_patch()

    # Get the diffs
    diffs, patches = generate_diff(old_code, new_code, file_path)

    # Removed lines
    removed_lines_count = 0

    # No-change lines
    no_changed_lines_count = 0
    for diff in diffs:
        if diff[0] == -1:
            for line in diff[1].splitlines():
                removed_lines_count += 1

        elif diff[0] == 0:
            for line in diff[1].splitlines():
                if line.strip():
                    no_changed_lines_count += 1

    # Old code lines
    old_code_lines = []
    for line in old_code.splitlines():
        if line.strip():
            old_code_lines.append(line.strip())

    # Patched code
    patched_code, _ = dmp.patch_apply(patches, old_code)
    patched_code_lines = []
    for line in patched_code.splitlines(keepends=True):
        patched_code_lines.append(line)

    applied_edit = False
    patched_lines_written = 0
    with (
        open(file_path, "r") as src_file,
        tempfile.NamedTemporaryFile(
            "w", delete=False, dir=os.path.dirname(file_path), encoding="utf-8"
        ) as tmp_file,
    ):
        tmp_name = tmp_file.name

        for line_no, line in enumerate(src_file, start=1):
            # Region in old file from where we start editing
            if not applied_edit and line.strip() == old_code_lines[0]:
                edit_from = line_no
                for patched_line in patched_code_lines:
                    tmp_file.write(patched_line)
                    patched_lines_written += 1

                applied_edit = True

            elif (
                applied_edit
                and line_no < edit_from + removed_lines_count + no_changed_lines_count
            ):
                continue

            else:
                tmp_file.write(line)

        # Copy file metadata (permissioons, last edited etc.) from src to dst
        shutil.copystat(file_path, tmp_name, follow_symlinks=False)
        # Atomic operation of replace to same old location (overrides if file already exists)
        os.replace(tmp_name, file_path)

        # print("------- Debugging print line in apply_diff func ------")
        # print(edit_from, patched_lines_written, no_changed_lines_count)
        # print("------- Debugging print line in apply_diff func ------")

    return True


def generate_diff(old_code, new_code, file_path, highlight=False):
    "Generates the diff b/w exisiting code in file and generated code change"

    dmp = dmp_module.diff_match_patch()

    # Generate diff
    diffs = dmp.diff_main(old_code, new_code)

    # Diff cleanup human-readble form
    dmp.diff_cleanupSemantic(diffs)

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


def construct_code(read_file_data, truncate=False):
    file_path = read_file_data[0]
    code_lines = read_file_data[1]

    code_block = ""
    for line in code_lines:
        code_block += line

    if truncate:
        code_length = len(code_block)
        if code_length > 300:
            return code_block[:300] + " ....", file_path

        return code_block[:code_length] + " ....", file_path

    return code_block + " ....", file_path


def format_grep_results(results_list):
    formatted_res = []

    for res in results_list:
        # slice_res = res[2][:10] if len(res[2]) > 10 else res[2]
        formatted_res.append((res[0], f":{res[1]}"))
    return formatted_res
