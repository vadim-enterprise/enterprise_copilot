from llama_cpp import Llama

def get_llama_response(prompt: str) -> str:
    try:
        llm = Llama(model_path="models/llama-2-7b-chat.gguf")
        output = llm(prompt, max_tokens=2048, temperature=0.7)
        return output['choices'][0]['text'].strip()
    except Exception as e:
        return f"Error generating Llama response: {str(e)}" 