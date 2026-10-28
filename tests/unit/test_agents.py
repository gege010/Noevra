import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.agents.planner import planner_node
from src.agents.state import default_state

@pytest.mark.asyncio
async def test_planner_output_schema():
    """Planner should return a list of subtasks."""
    state = default_state(query="AI in healthcare", job_id="test")
    
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content='{"tasks": []}'))
    with patch("src.agents.planner.create_llm", return_value=mock_llm):
        result = await planner_node(state)
    assert isinstance(result["plan"], list)
    assert result["status"] == "researching"
