"""Small offline prompt comparison for the SAME model, not model selection."""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import json
from pathlib import Path
from time import perf_counter
from app.services.summarization_service import summarization_service as runtime
from benchmark_local_summarizer import CS

if __name__ == '__main__':
    runtime._load_model()
    templates = [
        '{text}\n\nWrite a summary of the above text.',
        'summarize: {text}',
        '{text}\n\nWhat are the main ideas in this text? Write a factual paragraph.',
        '{text}\n\nExplain the main ideas in simple language for a beginner.',
    ]
    results = []
    for template in templates:
        started = perf_counter()
        inputs = runtime.tokenizer(template.format(text=CS), return_tensors='pt')
        with runtime.torch.inference_mode():
            output = runtime.model.generate(**inputs, max_new_tokens=192, do_sample=False, num_beams=1, no_repeat_ngram_size=3)
        results.append({'template':template, 'output':runtime.tokenizer.decode(output[0], skip_special_tokens=True), 'seconds':perf_counter()-started})
    Path('benchmark_results/prompt_probe.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2),flush=True)
