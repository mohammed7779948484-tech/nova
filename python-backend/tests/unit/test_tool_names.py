"""T010: Test tool naming accuracy.

PDCA Called Shot:
- test_no_tool_named_send_product_image: verify no tool in ALL_TOOLS has
  name == 'send_product_image'.
  Expected RED: AssertionError 'send_product_image' found in tool names
- test_get_product_details_tool_exists: verify a tool named 'get_product_details'
  exists in ALL_TOOLS.
  Expected RED: AssertionError 'get_product_details' not found in tool names
"""


from src.tools import ALL_TOOLS


class TestToolNames:

    def test_no_tool_named_send_product_image(self):
        """No tool should be named 'send_product_image'."""
        tool_names = [t.name for t in ALL_TOOLS]
        assert "send_product_image" not in tool_names, (
            f"'send_product_image' found in tool names: {tool_names}"
        )

    def test_get_product_details_tool_exists(self):
        """A tool named 'get_product_details' must exist."""
        tool_names = [t.name for t in ALL_TOOLS]
        assert "get_product_details" in tool_names, (
            f"'get_product_details' not found in tool names: {tool_names}"
        )