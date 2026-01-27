"""Tests unitaires pour MyCustomTool."""

import pytest

from company_url_analysis_automation.tools.custom_tool import MyCustomTool, MyCustomToolInput


class TestCustomToolInstantiation:
    def test_tool_name(self):
        tool = MyCustomTool()
        assert tool.name == "Name of my tool"

    def test_tool_has_description(self):
        tool = MyCustomTool()
        assert len(tool.description) > 0

    def test_tool_args_schema(self):
        tool = MyCustomTool()
        assert tool.args_schema is MyCustomToolInput


class TestCustomToolInput:
    def test_valid_input(self):
        inp = MyCustomToolInput(argument="test value")
        assert inp.argument == "test value"

    def test_missing_argument_raises(self):
        with pytest.raises(Exception):
            MyCustomToolInput()


class TestCustomToolRun:
    def test_returns_string(self):
        tool = MyCustomTool()
        result = tool._run(argument="test")
        assert isinstance(result, str)

    def test_returns_example_output(self):
        tool = MyCustomTool()
        result = tool._run(argument="anything")
        assert "example" in result
