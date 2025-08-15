from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage


class LLMInterface:
    def __init__(
        self,
        llm_provider="anthropic",
        model="claude-sonnet-4-20250514",
        thinking_mode: bool = True,
        max_tokens: int = 64000,
    ):
        self.llm_provider = llm_provider
        self.max_tokens = max_tokens
        self.thinking_mode = (
            {"type": "enabled", "budget_tokens": 2000} if thinking_mode else None
        )
        self.model = model

    def client(self):
        if self.llm_provider == "anthropic":
            llm_client = ChatAnthropic(
                model=self.model,
                max_tokens=self.max_tokens,
                thinking=self.thinking_mode,
            )

        return llm_client

    def get_system_prompt(self, prompt):
        if self.llm_provider == "anthropic":
            system_prompt = SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            )

        return system_prompt
