from agent.utils import apply_diff, generate_diff

if __name__ == "__main__":
    file_path = "/Users/tausif/grepo-main-env/grepo/src/agent/test1.py"
    old_code = """

    def merge(left: List[Any], right: List[Any]) -> List[Any]:
        \"\"\"
        Merge two sorted lists into a single sorted list.

        Args:
            left: First sorted list
            right: Second sorted list

        Returns:
            A new sorted list containing all elements from both input lists

        Time Complexity: O(n + m) where n and m are lengths of input lists
        Space Complexity: O(n + m) for the result list
        \"\"\"
        result = []

    """

    new_code = """

        def merge(left: List[Any], right: List[Any]) -> List[Any]:
            result = []
            if left[l_index] <= right[r_index]:
                result.append(left[l_index])
                l_index += 1
            else:
                result.append(right[r_index])
                r_index += 1
                print("oooooo")


    """
    from pprint import pprint

    import diff_match_patch as dmp_module
    from rich.console import Console

    console = Console()
    dmp = dmp_module.diff_match_patch()

    old, new = generate_diff(old_code, new_code, file_path, highlight=True)
    console.print(old)
    console.print("-------")
    console.print(new)

    diffs, patches = generate_diff(old_code, new_code, file_path)
    new_patched_text, _ = dmp.patch_apply(patches, old_code)
    console.print(f"[#E8B641]{new_patched_text}[/]")

    res = apply_diff(file_path, old_code, new_code)

    pprint(diffs)

    print(res)
