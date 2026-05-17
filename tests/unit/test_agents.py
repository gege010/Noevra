import pytest
from unittest.mock import patch, MagicMock
from src.agents.planner import planner_node
from src.agents.state import default_state

@pytest.mark.asyncio
async def test_planner_output_schema():
    """Planner should return a list of subtasks."""
    state = default_state(query="AI in healthcare", job_id="test")
    
    mock_response = MagicMock()
    mock_response.tasks = ["Task 1", "Task 2"]
    
    with patch("src.agents.planner.ChatGroq") as mock_chat:
        mock_instance = MagicMock()
        mock_instance.with_structured_output.return_value.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_instance
        
        result = await planner_node(state)
        
        assert "plan" in result
        assert isinstance(result["plan"], list)
        assert len(result["plan"]) > 0
        assert result["status"] == "researching"
