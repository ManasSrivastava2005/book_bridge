# Local Book Bridge summarization

The active summarization endpoints run FLAN-T5 Base locally. They never invoke a cloud provider or download a model during a request. The Gemini service is retained in `app/services/cloud_book_summarization.py` and original files are backed up under `backups/local-summarizer/`. Existing cloud settings and dependencies are retained but do not select the active provider.

## Environment and setup

Verified on Windows x64, Python 3.14, CPU-only PyTorch 2.11.0+cpu, Transformers 4.57.6, SentencePiece 0.2.1 and psutil 7.2.2. The installation added packages and did not uninstall or downgrade working backend packages. PyTorch provides a [Windows/Python 3.14 CPU wheel](https://download.pytorch.org/whl/cpu/torch/); compatibility was also checked through actual imports and CPU tensor execution.

```powershell
cd C:\Backend\bookbbbb
.\venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\venv\Scripts\python.exe setup_local_summarizer.py
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

The setup command makes an explicit one-time download from Hugging Face. It downloads only one model weight format and tokenizer/configuration files, records the repository revision, and does not run training. Inference uses `local_files_only=True`, `trust_remote_code=False`, safetensors and CPU float32. Model files are excluded by `.gitignore`.

## Configuration

- `LOCAL_SUMMARY_MODEL_NAME`: display/download identifier, initially `google/flan-t5-base`.
- `LOCAL_SUMMARY_MODEL_PATH`: absolute local model directory; default is `models/flan-t5-base` under this project.
- `LOCAL_SUMMARY_THREADS`: CPU inference threads, default 4, bounded 1–6.
- Existing `BOOKBRIDGE_SUMMARY_MODEL`, `GEMINI_API_KEY` and `OPENAI_API_KEY` belong to retained cloud code and do not activate it.

To later use a fine-tuned model, place compatible tokenizer/configuration/safetensors files under `models/bookbridge-summarizer/`, set the local path and display name, and restart. No frontend or endpoint changes are needed. Do not run the download script against a custom local-only model identifier. No training directory or training code is included.

## Runtime behavior

Use **AI Assistant → Book Summarizer**. The same JWT-protected POST `/ai/summarize/text` and `/ai/summarize/file` routes and original response fields are preserved. Additional response fields identify the model, local provider, time, chunk count, reduction passes and quality warning.

The model is loaded once on the first valid request and retained for the life of the API process. A lock serializes loading and generation. Concurrent requests receive a readable 429 busy message instead of queuing unbounded work. **Use a single API worker:** each additional worker would otherwise create its own model. The event loop stays responsive because generation runs in FastAPI's thread pool.

Text is cleaned without deleting formulas, then packed by paragraph/sentence within a 400-token source budget. Overlong sentences are split at word boundaries; only an individually overlong word requires character splitting. Each chunk is summarized, and the complete collection is hierarchically reduced until it fits a final consolidation. No chunk is silently dropped. Detailed/simple modes retain section outputs; key points are deduplicated, and detailed/exam modes retain verbatim source definitions, formulas and numbered steps where detected.

Limits: PDF/TXT only, 25 MiB upload, 1,000,000 extracted/input characters, 512 chunks, 600-second inference budget plus initial model load. Requests beyond these limits fail clearly and ask for smaller chapters. A 90-second individual generation bound also applies. Output cut off before EOS is rejected. These bounds mean arbitrarily large books are not guaranteed to finish in one request. The UI waits up to 12 minutes. Leaving the page does not cancel an already-running inference; its time budget still applies.

The first model load requires at least 2 GiB available RAM. CPU inference uses `torch.inference_mode()`, greedy decoding, batch size one, bounded output length, and four threads by default. PDF extraction is selectable text only; scanned files require OCR elsewhere. Uploaded content and generated results are not stored in the database. Copy and Download are retained; student Save to Notes is intentionally absent.

## Verification

```powershell
.\venv\Scripts\python.exe -m unittest -v test_book_summarization test_notes_upload
.\venv\Scripts\python.exe -X utf8 benchmark_local_summarizer.py
.\venv\Scripts\python.exe -X utf8 verify_summarization_live.py --browser-session SESSION
.\venv\Scripts\python.exe -m pip check
```

The benchmark uses synthetic CS, DBMS, OS, data-structure and machine-learning material in four fixtures across all five modes. It writes the actual outputs and measured process RSS to `benchmark_results/local_summary_benchmark.json`. Network connections are blocked during this benchmark. Run benchmarks separately from live inference to avoid keeping two model instances in RAM.

See `LOCAL_SUMMARIZER_REPORT.md` for measured results and quality limitations. A successful HTTP response proves execution, not factual correctness. FLAN-T5 Base is a small general instruction model; it is not an academically validated textbook summarizer. Generated text must be checked against the source.

### Generation-limit recovery
Incomplete sections are retried with the same full input and cached model, with output budgets increasing from the mode default to 256 and then 512 tokens. All three attempts share the request deadline and inference lock. EOS followed by padding is accepted. If all attempts fail, no partial summary is returned. Longer retries may increase latency.

### Empty-output recovery
Blank, punctuation-only, and very short fragment outputs are retried with a rephrased instruction using the full source section. Retries share the existing three-attempt bound, deadline, cached model, and inference lock. Minimum output length is not forced: testing showed that doing so could turn an empty response into punctuation. No source section is skipped and repeated failure returns an explicit error.

To verify a particular PDF through extraction and the real local model, stop the API first to avoid duplicate model copies, then run:

```powershell
.\venv\Scripts\python.exe -X utf8 verify_local_pdf.py "C:\path\to\notes.pdf" --mode detailed
```

This command prints progress and execution metrics without saving document text or summaries. Restart the API afterwards.
