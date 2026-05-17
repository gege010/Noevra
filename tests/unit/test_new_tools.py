import pytest
from src.agents.tools import execute_code

def test_execute_code_success():
    code = "print('Hello from test')"
    result = execute_code(code)
    assert "Hello from test" in result

def test_execute_code_error():
    code = "print(1 / 0)"
    result = execute_code(code)
    assert "ZeroDivisionError" in result or "Execution Error" in result
