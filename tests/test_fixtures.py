import json
from pathlib import Path

from review_brief_diagrams.renderer import render_request


FAMILIES = ("logical", "deployment", "interaction")


def test_all_family_fixtures_render(tmp_path: Path) -> None:
    root = Path(__file__).parent / "fixtures"
    for family in FAMILIES:
        request = tmp_path / f"{family}.json"
        request.write_text(json.dumps({"source": {"path": str(root / f"{family}.mmd")}, "diagram": {"family": family}, "output": {"bundle_dir": str(tmp_path / family)}}))
        bundle = render_request(request)
        manifest = json.loads((bundle.path / "manifest.json").read_text())
        assert manifest["status"] == "succeeded"
        assert manifest["diagram"]["family"] == family
        assert (bundle.path / "diagram.png").is_file()
