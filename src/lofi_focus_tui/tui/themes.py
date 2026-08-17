from dataclasses import dataclass

DEFAULT_THEME = "city_pop"


@dataclass(frozen=True)
class Theme:
    name: str
    description: str
    label: str
    value: str
    desc: str
    accent: str
    info: str
    ok: str
    error: str

    @property
    def state_styles(self) -> dict[str, str]:
        return {
            "idle": self.label,
            "planning": self.info,
            "generating": self.info,
            "ready": self.ok,
            "playing": self.ok,
            "paused": self.accent,
            "error": self.error,
        }


THEMES: dict[str, Theme] = {
    "city_pop": Theme(
        name="city_pop",
        description="warm amber, dusty keys and round bass",
        label="dim",
        value="#e8e2d2",
        desc="#8f8a80",
        accent="#d4a25c",
        info="#7fa8d7",
        ok="#86b57f",
        error="#d46a6a",
    ),
    "neon_tokyo": Theme(
        name="neon_tokyo",
        description="synthwave pink over a midnight city",
        label="#6b6b8a",
        value="#f0e6ff",
        desc="#8a7fa8",
        accent="#ff5fd2",
        info="#5fd2e8",
        ok="#5fe8a8",
        error="#ff6b6b",
    ),
    "vhs": Theme(
        name="vhs",
        description="tracking lines in magenta and teal",
        label="#7a6b8a",
        value="#e6e0f0",
        desc="#8a7f9a",
        accent="#d25fb8",
        info="#5fc8c8",
        ok="#7fd2a8",
        error="#d26b6b",
    ),
    "bubblegum": Theme(
        name="bubblegum",
        description="pastel pink, soft and sweet",
        label="#9a8a9a",
        value="#f5e8f0",
        desc="#a89aa8",
        accent="#f0a8d0",
        info="#a8c8f0",
        ok="#a8e0c0",
        error="#f0a8a8",
    ),
    "arcade": Theme(
        name="arcade",
        description="cabinet green under marquee yellow",
        label="#6b8a6b",
        value="#e8f0e0",
        desc="#8aa88a",
        accent="#e8d45c",
        info="#5ce8a8",
        ok="#5ce87f",
        error="#e86b5c",
    ),
    "avex_sunset": Theme(
        name="avex_sunset",
        description="coral sunset over the bay",
        label="#8a6b6b",
        value="#f0e6dc",
        desc="#a88a80",
        accent="#e88a5c",
        info="#7fa8d7",
        ok="#86b57f",
        error="#d46a6a",
    ),
    "midnight": Theme(
        name="midnight",
        description="indigo night, quiet and cool",
        label="#5c6b8a",
        value="#dce6f0",
        desc="#7a8aa8",
        accent="#7f9fd7",
        info="#5fd2e8",
        ok="#7fd2a8",
        error="#d77f7f",
    ),
    "harajuku": Theme(
        name="harajuku",
        description="purple-pink street style",
        label="#8a6b8a",
        value="#f0e6f5",
        desc="#a88aa8",
        accent="#c85fd2",
        info="#5fd2c8",
        ok="#a8e0a8",
        error="#f06b8a",
    ),
    "cassette": Theme(
        name="cassette",
        description="tape sepia, warm and worn",
        label="#8a7a6b",
        value="#f0e8dc",
        desc="#a89a8a",
        accent="#c89a5c",
        info="#7fa8a8",
        ok="#8aa87f",
        error="#c86b5c",
    ),
    "retro_futur": Theme(
        name="retro_futur",
        description="electric blue and cyan, 1984",
        label="#6b6b9a",
        value="#e6e6f5",
        desc="#8a8aa8",
        accent="#5c8ae8",
        info="#5fd2e8",
        ok="#7fd2a8",
        error="#e85c7f",
    ),
}
