from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def _call_openai_compatible(
    prompt: str,
    system_prompt: str | None = None,
    *,
    api_key_env: str = "OPENAI_API_KEY",
    model_env: str = "OPENAI_MODEL",
    default_model: str = "gpt-4o-mini",
    base_url_env: str = "OPENAI_BASE_URL",
    default_base_url: str | None = None,
) -> str:
    from openai import OpenAI

    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(f"{api_key_env} is not configured.")

    model = os.getenv(model_env, default_model).strip()
    base_url = os.getenv(base_url_env, "").strip() or default_base_url
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
    client = (
        OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        if base_url
        else OpenAI(api_key=api_key, timeout=timeout)
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt or "你是严谨的技术情报分析助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    return response.choices[0].message.content or ""


def _call_anthropic(prompt: str, system_prompt: str | None = None) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=800,
        temperature=0.2,
        system=system_prompt or "你是严谨的技术情报分析助手。",
        messages=[{"role": "user", "content": prompt}],
    )
    return "\n".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )


def _mock_response(prompt: str) -> str:
    lower_prompt = prompt.lower()
    if "manager" in lower_prompt or "总控" in prompt:
        return (
            "今日摘要：今日情报显示，AI Agent 工具链、机器人真实部署和产业基础设施正在同时推进。\n"
            "重点技术解读：应重点关注 Agent 工程化、机器人场景数据和部署安全，这些决定技术能否稳定落地。\n"
            "风险与趋势判断：多数信息仍处早期，需要核验开源活跃度、真实客户案例和成本边界。\n"
            "后续建议：优先复现一个小型 Agent 工作流，并持续跟踪机器人应用场景中的真实约束。"
        )
    if "risk" in lower_prompt or "风险" in prompt:
        return "主要风险在于信息粒度有限，真实落地前需要补充来源可信度、复现实验和成本评估。"
    if "value" in lower_prompt or "价值" in prompt:
        return "该信息具备技术跟踪价值，可用于判断近期工程方向、学习重点和产品化机会。"
    return "这是 Mock LLM 生成的演示分析结果，适合在无 API Key 的课堂场景中使用。"


def call_llm(prompt: str, provider: str = "mock", system_prompt: str | None = None) -> str:
    """Call an LLM provider or return a deterministic mock result."""
    if provider == "mock":
        return _mock_response(prompt)
    if provider == "openai":
        return _call_openai_compatible(prompt, system_prompt)
    if provider == "siliconflow":
        return _call_openai_compatible(
            prompt,
            system_prompt,
            api_key_env="SILICONFLOW_API_KEY",
            model_env="SILICONFLOW_MODEL",
            default_model="Qwen/Qwen2.5-7B-Instruct",
            base_url_env="SILICONFLOW_BASE_URL",
            default_base_url="https://api.siliconflow.cn/v1",
        )
    if provider == "deepseek":
        return _call_openai_compatible(
            prompt,
            system_prompt,
            api_key_env="DEEPSEEK_API_KEY",
            model_env="DEEPSEEK_MODEL",
            default_model="deepseek-chat",
            base_url_env="DEEPSEEK_BASE_URL",
            default_base_url="https://api.deepseek.com",
        )
    if provider == "anthropic":
        return _call_anthropic(prompt, system_prompt)

    raise ValueError(
        "Unsupported LLM provider: "
        f"{provider}. Supported providers: mock, openai, siliconflow, deepseek, anthropic."
    )


def call_llm_with_fallback(prompt: str, provider: str = "mock", system_prompt: str | None = None) -> str:
    """Call a real LLM when configured, falling back to mock text for deploy robustness."""
    try:
        return call_llm(prompt, provider=provider, system_prompt=system_prompt)
    except Exception as exc:
        return f"{_mock_response(prompt)}（真实 LLM 调用失败，已回退 mock：{exc}）"
