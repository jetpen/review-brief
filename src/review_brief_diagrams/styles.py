from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any


@dataclass(frozen=True)
class StyleProfile:
    name: str
    version: str
    background: str = "#ffffff"
    font_family: str = "DejaVu Sans"
    font_size: int = 11
    edge_font_size: int = 10
    node_fill: str = "#dbeafe"
    node_border: str = "#334155"
    text_color: str = "#0f172a"
    edge_color: str = "#475569"
    line_width: float = 1.4
    arrow_size: float = 0.8
    node_margin: str = "0.16,0.10"
    max_width: int = 2400
    max_height: int = 1800
    min_font_size: int = 9
    label_wrap_width: int = 32
    transparent: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_STYLE = StyleProfile(name="review-brief-default", version="1")


def resolve_style(request: dict[str, Any]) -> StyleProfile:
    rendering = request.get("rendering", {})
    if not isinstance(rendering, dict):
        raise ValueError("rendering must be an object")
    profile = rendering.get("style_profile", "review-brief-default")
    if isinstance(profile, dict):
        name = profile.get("name", DEFAULT_STYLE.name)
        version = profile.get("version", DEFAULT_STYLE.version)
        overrides = {key: value for key, value in profile.items() if key not in {"name", "version"}}
        return replace(DEFAULT_STYLE, name=name, version=version, **overrides)
    if profile != DEFAULT_STYLE.name:
        raise ValueError(f"unknown style profile: {profile}")
    return DEFAULT_STYLE


def contrast_ratio(foreground: str, background: str) -> float:
    def channel(value: int) -> float:
        normalized = value / 255
        return normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4

    def luminance(color: str) -> float:
        color = color.lstrip("#")
        if len(color) != 6:
            raise ValueError(f"expected six-digit color: {color}")
        channels = [channel(int(color[index : index + 2], 16)) for index in (0, 2, 4)]
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)
