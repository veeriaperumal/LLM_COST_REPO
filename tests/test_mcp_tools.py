# ---------------------------------------------------------------------------
# test_mcp_tools.py — Tests for MCP tool implementations
# ---------------------------------------------------------------------------

import pytest

from app.mcp.tools import calculate, get_customer, search_knowledge


# -- search_knowledge ---------------------------------------------------------


@pytest.mark.asyncio
async def test_search_knowledge_exact_title_match():
    result = await search_knowledge(query="Return Policy")
    assert result["total"] >= 1
    titles = [r["title"] for r in result["results"]]
    assert "Return Policy" in titles


@pytest.mark.asyncio
async def test_search_knowledge_content_match():
    result = await search_knowledge(query="warranty")
    assert result["total"] >= 1
    titles = [r["title"] for r in result["results"]]
    assert "Warranty Information" in titles


@pytest.mark.asyncio
async def test_search_knowledge_no_match():
    result = await search_knowledge(query="xyznonexistent")
    assert result["total"] == 0
    assert result["results"] == []


@pytest.mark.asyncio
async def test_search_knowledge_relevance_scores():
    result = await search_knowledge(query="shipping")
    assert result["total"] >= 1
    for r in result["results"]:
        assert 0.0 < r["relevance"] <= 1.0


@pytest.mark.asyncio
async def test_search_knowledge_case_insensitive():
    result = await search_knowledge(query="RETURN POLICY")
    assert result["total"] >= 1


# -- calculate ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_simple_addition():
    result = await calculate(expression="2 + 3")
    assert result["result"] == 5.0
    assert result["error"] is None


@pytest.mark.asyncio
async def test_calculate_complex_expression():
    result = await calculate(expression="(10 + 5) * 2 - 3")
    assert result["result"] == 27.0


@pytest.mark.asyncio
async def test_calculate_division():
    result = await calculate(expression="10 / 3")
    assert abs(result["result"] - 3.333333) < 0.001


@pytest.mark.asyncio
async def test_calculate_power():
    result = await calculate(expression="2 ** 10")
    assert result["result"] == 1024.0


@pytest.mark.asyncio
async def test_calculate_division_by_zero():
    result = await calculate(expression="1 / 0")
    assert result["result"] is None
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_calculate_invalid_expression():
    result = await calculate(expression="import os")
    assert result["result"] is None
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_calculate_empty_expression():
    result = await calculate(expression="")
    assert result["result"] is None


@pytest.mark.asyncio
async def test_calculate_negative_numbers():
    result = await calculate(expression="-5 + 3")
    assert result["result"] == -2.0


# -- get_customer -------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_customer_found():
    result = await get_customer(customer_id="C001")
    assert result["customer"] is not None
    assert result["customer"]["name"] == "Alice Johnson"
    assert result["customer"]["tier"] == "enterprise"


@pytest.mark.asyncio
async def test_get_customer_not_found():
    result = await get_customer(customer_id="C999")
    assert result["customer"] is None
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_get_customer_has_preferences():
    result = await get_customer(customer_id="C002")
    customer = result["customer"]
    assert "language" in customer["preferences"]
    assert customer["preferences"]["language"] == "en"


@pytest.mark.asyncio
async def test_get_customer_empty_id():
    result = await get_customer(customer_id="")
    assert result["customer"] is None
