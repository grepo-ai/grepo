import os
import json
from pathlib import Path
import copy
import requests


from rich.theme import Theme
from agent.utils import ProviderMappingAPI
from cli import __version__


color_palette = {
    "green": "#7CFCA7",
    "red": "#FC7C7C",
    "cyan": "#60FCF5",
    "pink": "#FA5CB3",
    "light-pink": "#F47AFF",
    "purple": "#4A4EFF",
    "orange": "#F27F4E",
    "grepo_logo": "#60FCF5",
    "intro-text-pink": "#FC69FF",
    "light-purple": "#B6C8FA",
    "white": "#FCFCFC",
    "input-bar-green": "#69FFB4",
    "landing-page-green": "#86F071",
    "grey": "#969696",
}


grepo_md_theme = Theme(
    {
        # Headings
        "markdown.h1": f"bold {color_palette['purple']}",
        "markdown.h1.border": color_palette["light-purple"],
        "markdown.h2": f"bold {color_palette['light-pink']}",
        "markdown.h3": f"bold {color_palette['pink']}",
        "markdown.h4": f"bold {color_palette['orange']}",
        "markdown.h5": f"bold {color_palette['cyan']}",
        "markdown.h6": f"bold {color_palette['light-purple']}",
        # Inline emphasis
        "markdown.em": f"italic {color_palette['white']}",
        "markdown.strong": f"bold {color_palette['intro-text-pink']}",
        "markdown.code": f"{color_palette['white']}",
        # Links
        "markdown.link": color_palette["light-purple"],
        "markdown.link_url": color_palette["light-purple"],
        # Lists
        "markdown.item.bullet": color_palette["intro-text-pink"],
        "markdown.item.number": color_palette["intro-text-pink"],
        # Block elements
        "markdown.block_quote": f"italic {color_palette['intro-text-pink']}",
        "markdown.hr": color_palette["light-purple"],
    }
)


code_block_md_theme = "github-dark"


def get_env_vars():
    return dict(os.environ)


def check_models_api_key(env_vars: dict, settings_json: dict, root_dir: str):
    api_keys = []
    settings_changed = False

    # Check settings.json to see if we already saved any API key from previous session runs
    if settings_json:
        for key, val in settings_json.items():
            if key in ProviderMappingAPI.__members__:
                api_keys.append({key: val})

    # Now check current env vars for any API key for the models supported
    for key, val in env_vars.items():
        if key in ProviderMappingAPI.__members__ and val.strip():
            if key not in api_keys:
                api_keys.append({key: val})
                settings_json.update({key: val})
                settings_changed = True

    # Update the settings file with model API keys that are present in current env and also supported by Grepo
    if settings_changed:
        update_settings(root_dir, data=settings_json)
    return api_keys


def update_env_var_api_keys(
    model_api_keys: list[dict], settings_json: dict, root_dir: str
):
    old_settings = copy.deepcopy(settings_json)
    for model_key_mapping in model_api_keys:
        key = next(iter(model_key_mapping))

        # Update env vars
        os.environ[key] = model_key_mapping[key]
        settings_json.update({key: model_key_mapping[key]})

    # Write to settings.json with data
    if model_api_keys:
        file_path = Path(f"{root_dir}/.grepo/settings.json")

        if old_settings != settings_json:
            with open(file_path, "w") as file:
                json.dump(
                    settings_json, file, indent=2, ensure_ascii=False, sort_keys=True
                )


def get_or_create_settings(root_dir: str):
    # Read settings.json file in .grepo dir else create it
    settings_file = Path(f"{root_dir}/.grepo/settings.json")

    if settings_file.exists():
        # Read settings.json file
        try:
            with open(settings_file, "r") as file:
                settings_json_dump = json.load(file)
                return settings_json_dump

        except json.JSONDecodeError:
            # TODO: File could be empty or has faulty JSON need to check that precisely and handle
            return {}

    else:
        # Create a settings.json file
        settings_file.touch()
        return {}


def update_settings(root_dir: str, data: dict):
    # Read settings.json file in .grepo dir else create it
    settings_file = Path(f"{root_dir}/.grepo/settings.json")

    # TODO: Make sure to first check existing settings and merge with new incoming settings
    with settings_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False, sort_keys=True)


def check_version_updates():
    grepo_gh_url = "https://api.github.com/repos/grepo-ai/grepo/tags"

    # TODO: Replace url with Grepo's post open-sourcing
    grepo_releases = requests.get("https://api.github.com/repos/certbot/certbot/tags")

    if grepo_releases.status_code == 200:
        latest_version = grepo_releases.json()[0]["name"]
        return latest_version

    return __version__
