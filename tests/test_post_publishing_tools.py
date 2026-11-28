"""MCP registration contracts for personal-post publishing."""

from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP

from linkedin_mcp_server.error_handler import CodedToolError, ErrorCode
from linkedin_mcp_server.server import create_mcp_server
from linkedin_mcp_server.tools import post_publishing


async def test_the_server_registers_preview_and_publish_with_the_call_timeout():
    server = create_mcp_server(tool_timeout=17)
    tools = {tool.name: tool for tool in await server.list_tools()}

    for name in [
        "prepare_post",
        "publish_post",
    ]:
        assert name in tools
        assert tools[name].timeout == 17
    preview = tools["prepare_post"].annotations
    assert preview is not None
    assert preview.read_only_hint is True
    publishing = tools["publish_post"].annotations
    assert publishing is not None
    assert publishing.read_only_hint is False
    assert publishing.idempotent_hint is False


@pytest.mark.parametrize(
    ("draft_id", "approved_text", "message"),
    [("", "A post", "draft_id"), ("a-preview-id", " ", "Post text")],
)
async def test_publish_rejects_malformed_input_before_browser_readiness(
    monkeypatch, draft_id, approved_text, message
):
    server = FastMCP("test")
    post_publishing.register_post_publishing_tools(server)
    ready = AsyncMock(side_effect=AssertionError("the browser was requested"))
    monkeypatch.setattr(post_publishing, "get_ready_extractor", ready)

    with pytest.raises(CodedToolError, match=message) as caught:
        await server.call_tool(
            "publish_post",
            {"draft_id": draft_id, "approved_text": approved_text, "confirmed": True},
        )

    assert caught.value.code is ErrorCode.INVALID_ARGUMENT
    ready.assert_not_awaited()
