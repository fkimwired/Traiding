import pytest
from fable5_api.config import Settings
from pydantic import ValidationError


def test_paper_is_the_only_execution_mode() -> None:
    assert Settings(_env_file=None, execution_mode="paper").execution_mode == "paper"

    with pytest.raises(ValidationError):
        Settings(_env_file=None, execution_mode="live")  # type: ignore[arg-type]
