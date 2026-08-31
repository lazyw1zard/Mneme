from pathlib import Path
import tomllib


def test_distribution_name_is_global_mneme():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    name = metadata["project"]["name"]

    assert name == "mneme"
    assert "-" not in name
