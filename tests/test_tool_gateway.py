from agentos.infra.tool_gateway import Tool, ToolGateway


def _gateway():
    gateway = ToolGateway()
    gateway.register(Tool("add", "Add two numbers", lambda a, b: a + b, ("a", "b")))
    return gateway


def test_describe_lists_registered_tools():
    described = _gateway().describe()
    assert described == [{"name": "add", "description": "Add two numbers", "parameters": ["a", "b"]}]


def test_call_runs_handler_and_logs():
    gateway = _gateway()
    call = gateway.call("add", {"a": 2, "b": 3})
    assert call.ok and call.result == 5
    assert gateway.calls == [call]


def test_unknown_tool_is_reported_not_raised():
    call = ToolGateway().call("missing", {})
    assert not call.ok and call.error == "unknown tool"


def test_missing_arguments_are_reported():
    call = _gateway().call("add", {"a": 1})
    assert not call.ok and "missing arguments: b" == call.error


def test_handler_error_is_captured():
    gateway = ToolGateway()
    gateway.register(Tool("boom", "Always fails", lambda: (_ for _ in ()).throw(ValueError("nope"))))
    call = gateway.call("boom")
    assert not call.ok and call.error == "nope"
