import pytest
from fable5_api.config import Settings
from pydantic import ValidationError


def test_paper_is_the_only_execution_mode() -> None:
    assert Settings(_env_file=None, execution_mode="paper").execution_mode == "paper"

    with pytest.raises(ValidationError):
        Settings(_env_file=None, execution_mode="live")  # type: ignore[arg-type]


def test_code_version_git_sha_is_optional_but_strict_when_supplied() -> None:
    assert Settings(_env_file=None).code_version_git_sha is None
    assert Settings(_env_file=None, code_version_git_sha="").code_version_git_sha is None
    assert Settings(_env_file=None, code_version_git_sha="a" * 40).code_version_git_sha == "a" * 40

    for invalid in ("a" * 39, "a" * 41, "A" * 40, "not-a-git-sha"):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, code_version_git_sha=invalid)
