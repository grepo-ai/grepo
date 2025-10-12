from rich.theme import Theme


color_palette = {
    "green": "#7CFCA7",
    "red": "#FC7C7C",
    "cyan": "#60FCF5",
    "pink": "#FA5CB3",
    "light-pink": "#F47AFF",
    "purple": "#4A4EFF",
    "orange": "#F27F4E",
    "grepo_logo": "#8FF4FF",
    "intro-text-pink": "#FC69FF",
    "light-purple": "#B6C8FA",
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
        "markdown.h6": f"bold {color_palette['green']}",
        # Inline emphasis
        "markdown.em": f"italic {color_palette['light-purple']}",
        "markdown.strong": f"bold {color_palette['orange']}",
        "markdown.code_inline": f"{color_palette['light-purple']}",
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
