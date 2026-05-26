from email_agent.agent import MockEmailAgent, OpenAIEmailAgent
from email_agent.agents import MockEmailAgent as SplitMockEmailAgent
from email_agent.agents import OpenAIEmailAgent as SplitOpenAIEmailAgent


def test_agent_module_reexports_public_agent_classes():
    """Backward-compatible imports should point to the split implementation classes."""
    assert MockEmailAgent is SplitMockEmailAgent
    assert OpenAIEmailAgent is SplitOpenAIEmailAgent
