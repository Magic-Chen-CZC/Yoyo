MODEL_METADATA: dict[tuple[str, str], dict[str, str | float]] = {
    ("openrouter", "openai/gpt-5.4"): {
        "parameter_size": "not_public",
        "estimated_input_cost_per_1k": 0.0025,
        "estimated_output_cost_per_1k": 0.015,
    },
    ("openrouter", "openai/gpt-5.4-mini"): {
        "parameter_size": "not_public",
        "estimated_input_cost_per_1k": 0.00075,
        "estimated_output_cost_per_1k": 0.0045,
    },
    ("openrouter", "qwen/qwen3.6-plus"): {
        "parameter_size": "not_public",
        "estimated_input_cost_per_1k": 0.000325,
        "estimated_output_cost_per_1k": 0.00195,
    },
    ("openrouter", "google/gemini-3.1-pro-preview"): {
        "parameter_size": "not_public",
        "estimated_input_cost_per_1k": 0.002,
        "estimated_output_cost_per_1k": 0.012,
    },
    ("openrouter", "google/gemini-3.1-flash-lite-preview"): {
        "parameter_size": "not_public",
        "estimated_input_cost_per_1k": 0.00025,
        "estimated_output_cost_per_1k": 0.0015,
    },
    ("openrouter", "anthropic/claude-sonnet-4.6"): {
        "parameter_size": "not_public",
        "estimated_input_cost_per_1k": 0.003,
        "estimated_output_cost_per_1k": 0.015,
    },
}


def estimate_cost(provider: str, model: str, prompt: str, response_text: str) -> tuple[float | None, float | None, str | None]:
    metadata = MODEL_METADATA.get((provider, model))
    if metadata is None:
        return None, None, None

    input_tokens = max(len(prompt) / 4, 1)
    output_tokens = max(len(response_text) / 4, 1)
    input_cost = float(metadata["estimated_input_cost_per_1k"]) * (input_tokens / 1000)
    output_cost = float(metadata["estimated_output_cost_per_1k"]) * (output_tokens / 1000)
    return input_cost, output_cost, str(metadata["parameter_size"])
