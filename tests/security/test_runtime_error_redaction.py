from services.agent_runtime.runtime import _fallback_response


def test_runtime_fallback_does_not_expose_internal_exception_details() -> None:
    secret_error = "postgresql://admin:password@internal-db/private"

    response = _fallback_response(
        "Analyze Tesla",
        "thread-1",
        secret_error,
        "trace-123",
    )

    assert secret_error not in response["answer"]
    assert "password" not in response["answer"]
    assert response["trace_id"] == "trace-123"
