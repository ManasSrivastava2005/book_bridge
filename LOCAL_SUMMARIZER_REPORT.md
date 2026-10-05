# Local FLAN-T5 Base implementation report

## Result

**The local integration and performance checks pass. Academic output quality does not pass.** FLAN-T5 Base remains the active model as requested; no alternative model was installed or selected. The UI identifies outputs as experimental and asks students to verify them against the source. It should not be relied on for exam preparation without source review.

## Files added

- `app/services/summarization_service.py`: lazy singleton, CPU generation, serialization, hierarchical reduction and error handling.
- `app/services/cloud_book_summarization.py`: preserved prior Gemini implementation, disconnected from active routes.
- `app/ml/__init__.py`, `app/ml/text_chunker.py`, `app/ml/summary_formatter.py`.
- `requirements-ml.txt`: compatible pinned CPU ML packages.
- `setup_local_summarizer.py`: explicit model download; no download during inference.
- `benchmark_local_summarizer.py`: synthetic academic fixtures, all-mode offline benchmark, RSS sampling and output capture.
- `probe_local_prompts.py`: reproducible comparison of four prompts on the same model.
- `LOCAL_SUMMARIZER_SETUP.md`, `LOCAL_SUMMARIZER_REPORT.md`.
- `benchmark_results/local_summary_benchmark.json`: final raw outputs and measurements.
- `benchmark_results/baseline_prefix_benchmark.json`, `benchmark_results/prompt_probe.json`: baseline and prompt-comparison evidence.
- `models/flan-t5-base/`: model/tokenizer/configuration files and exact revision record; excluded from version control.
- Original edited files copied into `backups/local-summarizer/`. Dependency resolution recorded in ignored `ml-dependency-plan.json`.

## Files modified

- `app/services/book_summarization.py`: local adapter, complete PDF extraction, explicit oversized-text rejection instead of truncation.
- `app/routers/book_summarization.py`: additive response metadata; original routes and JWT dependency preserved.
- `app/config.py`: local model path/name and resource bounds; existing cloud settings retained.
- `requirements.txt`, `.env.example`, `.gitignore`.
- `frontend/src/components/BookSummarizer.tsx`: local-processing notice, longer wait, metadata and experimental-quality warning. Existing layout, modes, Copy and Download preserved.
- `test_book_summarization.py`: local inference, tokenizer, chunking, locking, errors, authentication and compatibility tests.
- `verify_summarization_live.py`: real local-model browser workflow instead of provider simulation.
- Earlier Phase 3/Gemini reports marked historical.

No login, dashboard, borrowing, reservation, librarian, leaderboard, scanner, Notes permission, or existing AI Assistant code was changed. The private `.env` and API keys were not modified for this local implementation.

## Dependencies and Python compatibility

Existing environment: Windows x64, CPython 3.14.0. Binary-wheel resolution succeeded and actual PyTorch/Transformers imports and CPU tensor operations passed. A separate environment was therefore unnecessary. Installation added 19 packages; no existing package was uninstalled or downgraded. `pip check` reports no broken requirements.

Primary additions:

| Package | Version |
|---|---|
| torch | 2.11.0+cpu |
| transformers | 4.57.6 |
| sentencepiece | 0.2.1 |
| psutil | 7.2.2 |

Transitive additions: MarkupSafe 3.0.3, filelock 4.0.0, fsspec 2026.9.0, huggingface-hub 0.36.2, jinja2 3.1.6, mpmath 1.3.0, networkx 3.6.1, numpy 2.5.3, packaging 26.3, regex 2026.9.10, safetensors 0.8.0, setuptools 81.0.0, sympy 1.14.0, tokenizers 0.22.2, tqdm 4.70.1.

## Model and download

- Model: `google/flan-t5-base`, CPU float32, four Torch threads, greedy decoding, one sequence at a time.
- License: Apache-2.0 according to the [model card](https://huggingface.co/google/flan-t5-base).
- Revision: `7bcac572ce56db69c1ea7c8af255c5d7c9672fc2`.
- Model weights: **990,345,061 bytes**.
- Total downloaded model/tokenizer/configuration files plus revision record: **993,580,487 bytes**, approximately **994 MB / 948 MiB**. ML package storage is additional.
- Download took approximately 2 minutes 39 seconds in this run; this is network-dependent and is not inference latency.
- Cold load in final benchmark: **6.639 seconds**. **Exactly one load across all 20 requests** in the benchmark process.
- No training or fine-tuning was performed. No cloud fallback exists in the active service.

## Benchmark results

Synthetic author-written fixtures, all five modes, network connections blocked during inference. Times are measured wall-clock seconds and will vary with other laptop workloads.

| Input | Words | Chunks | Short | Detailed | Key points | Exam notes | Simple |
|---|---:|---:|---:|---:|---:|---:|---:|
| CS paragraph | 119 | 1 | 8.64* | 1.79 | 1.80 | 1.88 | 1.88 |
| DBMS page | 403 | 2 | 4.92 | 4.72 | 5.14 | 5.33 | 11.35 |
| OS section | 440 | 2 | 8.22 | 8.80 | 8.42 | 8.41 | 6.62 |
| Multi-page CS/DBMS/OS/data-structures/ML material | 1,579 | 7 | 18.48 | 17.73 | 16.90 | 16.55 | 24.54 |

*First short request includes the 6.639-second model load. Its remaining processing time was approximately 2.0 seconds. All multi-chunk fixtures required one consolidation level; tests separately exercise multiple reduction levels.

All 20 calls completed, but completion is **not** a quality pass. The raw JSON includes every generated summary so the weaknesses are reviewable.

### Human review of mode quality

- **Short — fails coverage/length target.** CS becomes one sentence about algorithms, omitting both search algorithms and complexity. DBMS becomes “Understand the basics of SQL.” Multi-page text becomes a single generic machine-learning statement. It does not reliably produce the requested 5–8 useful sentences.
- **Detailed — partly useful extracts, weak generated content.** Source definitions are retained verbatim, but generated section summaries omit concepts and contain unsupported statements. For example, the model describes denormalization as requiring a large number of database changes; that definition is not in the source.
- **Key points — formatting passes, content quality fails.** Bullets are distinct from paragraph formatting, but many are learning objectives such as “Understand SQL” rather than factual revision points. Incorrect/generated terms also occur.
- **Exam notes — source extraction is useful; generated notes are not reliable.** Precision/recall equations and numbered binary-search steps remain exact source extracts. Detected definitions are copied rather than reconstructed. Generated overview/concept bullets still contain omissions and errors, so this is not an exam-ready study aid.
- **Simple — fails correctness and simplification.** An OS output calls a mutex a “mute key.” The multi-page result invents processor claims and confuses cross-validation with the source's correlation/causation statement. These are material errors, not stylistic differences.

The four prompt probes improved the CS sample with a source-first template but did not solve the quality problem across subjects. No additional model was substituted. The five modes have different formatting and simple-mode instructions, but their generated factual content is not consistently differentiated enough.

## Memory observations

Machine: AMD Ryzen 5 5500U, 6 cores / 12 logical processors, integrated Radeon graphics, 15.3 GiB usable RAM. Before installation, approximately 3.8 GiB RAM and 360 GiB disk were free.

Final benchmark process baseline RSS: **46.4 MiB**; peak sampled RSS: **1,280.5 MiB (~1.25 GiB)**. Samples were collected every 100 ms, so extremely brief allocation peaks may be missed. After browser inference, the API working set was **1,271.3 MiB**, with Windows-reported peak **1,271.9 MiB**; system available memory was approximately **2.5 GiB**. These are process-level observations, not model-only allocations.

This laptop can run the model at acceptable demo speed. Run a single API worker. The first model load checks for at least 2 GiB free RAM; only one inference request runs per process, and a concurrent request gets a readable busy response.

## Test results

- **45 automated tests passed**, including existing Notes regressions.
- Lazy cached model load, local-files-only loader options, `torch.inference_mode()`, incomplete output rejection, word/token coverage, long unbroken strings, explicit oversize rejection, hierarchy including final source sections, multi-level reduction, serialized requests and lock release on failure.
- Missing model, memory/inference/tokenizer failures, invalid modes/text/uploads, scanned/corrupt/encrypted PDFs, real PDF extraction and TXT decoding.
- Actual JWT validation and existing AI routes. Local failures never call the retained cloud service.
- Frontend TypeScript check and production build passed.
- Actual browser using local FLAN-T5 Base: text/PDF/TXT requests, JWT header, loading and duplicate-submit prevention, results, invalid file error, Copy (verified clipboard text with Windows newline normalization), Download, tab/source state retention, 390px mobile layout, existing catalog assistant, and absence of student Save to Notes; no browser runtime errors.
- API starts successfully and remains running locally with one worker.
- No existing database records were changed by benchmarks or browser tests. Student Save to Notes remains absent.

## Known limitations

1. **Factual quality is inadequate for unsupervised academic use.** The model can invent claims. Source excerpts preserve selected original material but do not validate the generated text.
2. Short summaries over-compress. Hierarchical reduction can compound omissions even though every input chunk is processed.
3. Exactly five modes are exposed, but formatting alone does not guarantee five genuinely strong task behaviors.
4. The measured longest fixture is 1,579 words, not a complete textbook. Arbitrarily large books are not guaranteed to fit the 10-minute inference budget.
5. Limits are explicit: 25 MiB upload, one million extracted characters, 512 chunks, 600-second inference budget and bounded per-generation time. Oversized or unfinished work fails rather than returning a misleading partial-book summary.
6. This first version uses synchronous HTTP requests in the thread pool, not a durable background job queue. Navigating away does not cancel a running request; its timeout still applies.
7. PDF OCR, student note saving, model training, and cloud fallback are not implemented.
8. Raw source formulas are preserved in detailed/exam modes when detected; automatic semantic verification and complete formula detection are not provided.

## Next recommendation

Keep this implementation as a local inference prototype and retain its benchmark as a quality gate. Before relying on summaries for study, evaluate **`sshleifer/distilbart-cnn-12-6`** as the next candidate for core summarization, using the same fixtures and manual factual review. It is a summarization-trained model, but its suitability for textbook content and simple explanations still needs measurement; do not assume it resolves all five modes. See its [model card](https://huggingface.co/sshleifer/distilbart-cnn-12-6).

No switch, additional model download, or training was performed. A later single instruction-conditioned fine-tuned model could serve all five modes through the same service abstraction, but that requires an approved dataset and separate evaluation work.

## PDF empty-output fix
Reproduced an empty generation in section 33 of the supplied 58-page Operating System Notes PDF. MCQ sections also produced single-letter responses. Empty/punctuation/very short fragments now trigger bounded instruction rephrasing with the entire section preserved, sharing the existing request deadline and inference lock. No minimum generation length is forced.

The complete PDF passed in detailed mode: 95,254 input characters, 64 chunks, three reduction passes, 313.404 seconds including a 5.661-second model load, one model load, and no input truncation. All 46 summarization/notes regression tests passed. This verifies execution, not academic accuracy; topic-description retries can be generic. Full-file validation covered detailed mode. See `benchmark_results/os_pdf_verification.json`.
