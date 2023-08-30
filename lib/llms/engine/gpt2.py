
from lib.function.function_call import FunctionCall
from lib.llms.engine.base import LLMEngineBase
from lib.manifest import Manifest
from lib.utils.print import print_debug

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM



def get_prompt_data(messages: [dict]):
    text = []
    for message in messages:
        content = message["content"]
        if content:
            text.append(content)
    return "\n".join(text)
    # return text
    
class LLMEngineGPT2(LLMEngineBase):
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("rinna/japanese-gpt2-xsmall", use_fast=False)
        self.tokenizer.do_lower_case = True

        self.type = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = AutoModelForCausalLM.from_pretrained("rinna/japanese-gpt2-xsmall")
        self.model = self.model.to(self.type)

        return

    def chat_completion(self, messages: [dict], manifest: Manifest, llm_model, verbose: bool):
        prompt = get_prompt_data(messages)
        return_num = 1 

        input_ids = self.tokenizer.encode(prompt, return_tensors="pt",add_special_tokens=False).to(self.type)
        with torch.no_grad():
            output = self.model.generate(
                input_ids,
                max_length=400,
                min_length=100,
                do_sample=True,
                top_k=500,
                top_p=0.95,
                pad_token_id=self.tokenizer.pad_token_id,
                bos_token_id=self.tokenizer.bos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                num_return_sequences=return_num
            )
        decoded = self.tokenizer.batch_decode(output,skip_special_tokens=True)
        #for i in range(return_num):
        #print(decoded[i])

        res = "\n".join(decoded)
        role = "assistant"
        return (role, res, None)

