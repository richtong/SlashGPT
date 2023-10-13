import sys
from typing import List

import openai
import tiktoken  # for counting tokens

from slashgpt.llms.engine.base import LLMEngineBase
from slashgpt.llms.engine.replicate import message_to_prompt
from slashgpt.manifest import Manifest
from slashgpt.utils.print import print_debug, print_error


class LLMEngineOpenAILegacy(LLMEngineBase):
    def __init__(self, llm_model):
        super().__init__(llm_model)
        key = llm_model.get_api_key_value()
        if key == "":
            print_error("OPENAI_API_KEY environment variable is missing from .env")
            sys.exit()
        openai.api_key = key

        # Override default openai endpoint for custom-hosted models
        api_base = llm_model.get_api_base()
        if api_base:
            openai.api_base = api_base

        return

    def chat_completion(self, messages: List[dict], manifest: Manifest, verbose: bool):
        model_name = self.llm_model.name()
        prompt = message_to_prompt(messages, manifest)
        temperature = manifest.temperature()
        stream = manifest.stream()
        num_completions = manifest.num_completions()
        logprobs = manifest.logprobs()
        params = dict(model=model_name, prompt=prompt, temperature=temperature, stream=stream, n=num_completions, logprobs=logprobs)
        response = openai.Completion.create(**params)

        if verbose:
            print_debug(f"model={response['model']}")
            print_debug(f"usage={response['usage']}")
        res = response["choices"][0]["text"]
        function_call = self._extract_function_call(messages[-1], manifest, res)
        role = "assistant"

        return (role, res, function_call)

    def num_tokens(self, text: str):
        model_name = self.llm_model.name()
        encoding = tiktoken.encoding_for_model(model_name)
        return len(encoding.encode(text))
