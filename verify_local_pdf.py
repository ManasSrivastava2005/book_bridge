"""Opt-in real-model PDF check; run separately from the API to conserve RAM."""
import argparse
import json
from pathlib import Path

from app.services.book_summarization import extract_text
from app.services.summarization_service import SummarizationService, MODES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--mode', choices=sorted(MODES), default='detailed')
    args = parser.parse_args()
    source = extract_text(args.pdf.read_bytes(), '.pdf')
    runtime = SummarizationService()
    generate = runtime._generate
    completed = 0

    def traced(*positional, **kwargs):
        nonlocal completed
        result = generate(*positional, **kwargs)
        completed += 1
        print(f'Completed generation {completed}; reduction={kwargs.get("reduce", False)}', flush=True)
        return result

    runtime._generate = traced
    result = runtime.summarize(source, args.pdf.stem, args.mode)
    # Report execution metrics only: do not persist the uploaded text/summary.
    metrics = {key: result[key] for key in (
        'mode', 'input_characters', 'truncated', 'model', 'provider',
        'processing_time', 'model_load_time', 'chunks', 'reduction_passes')}
    metrics.update(load_count=runtime.load_count, summary_characters=len(result['summary']))
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
