
import pytest

from src.guardrails.output_guardrails import validate_agent_output


@pytest.mark.parametrize(
    "answer",
    [
        "There are 99441 orders in the database.",
        "The average order value is 136.68 BRL.",
        "Revenue increased by 12% compared to last month.",
        "No matching records were found.",
    ]
)
def test_safe_outputs_are_allowed(answer):
    assert validate_agent_output(answer) == answer


@pytest.mark.parametrize(
    "answer",
    [
        "",
        "   ",
        None,
        123,
    ]
)
def test_invalid_outputs_are_rejected(answer):
    with pytest.raises(ValueError):
        validate_agent_output(answer)


@pytest.mark.parametrize(
    "answer",
    [
        "The API key is gsk_abcdefghijklmnopqrstuvwxyz123456",
        "Secret: sk-lf-abcdefghijklmnopqrstuvwxyz123456",
        "Public key: pk-lf-abcdefghijklmnopqrstuvwxyz123456",
        "Database: postgresql://user:password@localhost:5432/testdb",
    ]
)
def test_sensitive_outputs_are_rejected(answer):
    with pytest.raises(ValueError):
        validate_agent_output(answer)


def test_environment_secret_is_rejected(monkeypatch):
    monkeypatch.setenv(
        "GROQ_API_KEY",
        "example_secret_value_123456789"
    )

    with pytest.raises(ValueError):
        validate_agent_output(
            "The configured key is example_secret_value_123456789"
        )
