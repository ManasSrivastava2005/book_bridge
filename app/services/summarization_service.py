"""Local-only FLAN-T5 inference. One lazy model and serialized requests/process.

Run the API with one worker. No cloud provider imports, network model loading,
training, or automatic model substitutions are performed here.
"""
import logging
import re
from pathlib import Path
from threading import Lock
from time import perf_counter

from fastapi import HTTPException
from app import config
from app.ml.text_chunker import clean_text, chunk_text
from app.ml.summary_formatter import format_summary

logger = logging.getLogger(__name__)
MODES = {'short', 'detailed', 'key_points', 'exam_notes', 'simple'}


class SummarizationService:
    def __init__(self):
        self._lock = Lock()
        self.model = None
        self.tokenizer = None
        self.torch = None
        self.load_seconds = 0.0
        self.load_count = 0

    def _load_model(self):
        if self.model is not None:
            return
        started = perf_counter()
        try:
            import psutil
            if psutil.virtual_memory().available < 2 * 1024**3:
                raise HTTPException(503, 'Not enough free RAM to load the local model. Close other applications and retry.')
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            path = Path(config.LOCAL_SUMMARY_MODEL_PATH)
            if not path.is_dir():
                raise HTTPException(503, 'The local summarization model is not installed. Run the documented model setup command first.')
            torch.set_num_threads(config.LOCAL_SUMMARY_THREADS)
            tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                str(path), local_files_only=True, trust_remote_code=False,
                use_safetensors=True, dtype=torch.float32,
            )
            model.eval()
            self.torch, self.tokenizer, self.model = torch, tokenizer, model
            self.load_seconds = perf_counter() - started
            self.load_count += 1
        except HTTPException:
            raise
        except MemoryError:
            raise HTTPException(503, 'Not enough memory to load the local model. Close other applications and retry.') from None
        except Exception as exc:
            logger.error('Local model load failed (%s)', type(exc).__name__)
            raise HTTPException(503, 'The local model could not be loaded. Check the installed ML dependencies and model files.') from None

    def _generate(self, text, mode, deadline, *, reduce=False):
        remaining = deadline - perf_counter()
        if remaining <= 0:
            raise HTTPException(504, 'This document exceeded the local processing time limit. Submit smaller chapters; no partial summary was returned.')
        if mode == 'simple' and not reduce:
            instruction = 'Explain the main ideas in simple language for a beginner.'
        else:
            instruction = 'Write a summary of the above text.'
        def encode(prompt):
            try:
                inputs = self.tokenizer(prompt, return_tensors='pt', truncation=False)
                if inputs['input_ids'].shape[-1] > 512:
                    raise HTTPException(422, 'A section exceeds the local token budget. Please submit a shorter section.')
                return inputs
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(422, 'The local tokenizer could not process this text. Try a plain-text copy.') from None
        inputs = encode(text + '\n\n' + instruction)
        target = 96 if reduce else (160 if mode in {'detailed', 'exam_notes'} else 112)
        # Retry incomplete or empty generations, using the SAME full input and
        # cached model. All attempts share the request deadline and lock.
        # Greedy decoding keeps the increased output budget memory-bounded.
        empty_output = False
        for attempt, token_limit in enumerate((target, 256, 512)):
            remaining = deadline - perf_counter()
            if remaining <= 0:
                raise HTTPException(504, 'The local processing time limit was reached. Submit a shorter chapter; no partial summary was returned.')
            with self.torch.inference_mode():
                outputs = self.model.generate(
                    **inputs, max_new_tokens=token_limit, do_sample=False, num_beams=1,
                    no_repeat_ngram_size=3, max_time=min(remaining, 90.0),
                )
            if perf_counter() >= deadline:
                raise HTTPException(504, 'The local processing time limit was reached. Submit a shorter chapter; no partial summary was returned.')
            # Padding may follow EOS. Skip the decoder start token when checking.
            if self.tokenizer.eos_token_id not in outputs[0, 1:].tolist():
                continue
            result = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            words = re.findall(r'[^\W\d_]+', result)
            if len(words) < 2 or sum(map(len, words)) < 8:
                # Increasing the maximum cannot change an immediate EOS.
                # Rephrase the instruction, preserving the entire section.
                # Forcing minimum tokens can instead produce punctuation.
                empty_output = True
                if attempt == 0:
                    inputs = encode(text + '\n\nSummarize the main facts in complete sentences.')
                elif attempt == 1:
                    inputs = encode(text + '\n\nWhat is the above text about?')
                continue
            return result
        if empty_output:
            raise HTTPException(502, 'The local model could not produce a complete non-empty summary after three attempts. No source sections were skipped; try this chapter separately.')
        raise HTTPException(422, 'The local model could not complete this section after three attempts with increased output limits. Submit a smaller section; no partial summary was returned.')

    def summarize(self, text, title, mode):
        mode = getattr(mode, 'value', mode)
        if mode not in MODES:
            raise HTTPException(422, 'Unsupported summary mode.')
        if len(text) > config.LOCAL_SUMMARY_MAX_CHARS:
            raise HTTPException(413, 'This document exceeds the local text limit. Submit it as smaller chapters; nothing was truncated.')
        source = clean_text(text)
        if len(source) < 50:
            raise HTTPException(400, 'Provide at least 50 characters of readable content.')
        if not self._lock.acquire(blocking=False):
            raise HTTPException(429, 'The local summarizer is processing another document. Please retry when it finishes.', headers={'Retry-After': '10'})
        started = perf_counter()
        try:
            self._load_model()
            deadline = perf_counter() + config.LOCAL_SUMMARY_TIMEOUT_SECONDS
            try:
                chunks = chunk_text(source, self.tokenizer, config.LOCAL_SUMMARY_CHUNK_TOKENS, config.LOCAL_SUMMARY_MAX_CHUNKS)
            except ValueError:
                raise HTTPException(413, 'This document has too many sections for one local request. Submit smaller chapters; nothing was truncated.') from None
            except Exception:
                raise HTTPException(422, 'The local tokenizer could not split this document. Try a plain-text copy.') from None
            summaries = [self._generate(chunk.text, mode, deadline) for chunk in chunks]
            # Every map result participates in each reduction level. This is a
            # bounded tree reduction, not truncation of combined summaries.
            reduced = summaries
            levels = 0
            while len(reduced) > 1:
                groups = chunk_text('\n\n'.join(reduced), self.tokenizer, config.LOCAL_SUMMARY_CHUNK_TOKENS)
                next_level = [self._generate(group.text, mode, deadline, reduce=True) for group in groups]
                levels += 1
                if len(next_level) >= len(reduced) or levels > 12:
                    raise HTTPException(422, 'The local model could not consolidate this document. Submit smaller chapters.')
                reduced = next_level
            result = format_summary(mode, reduced[0], summaries, [chunk.text for chunk in chunks])
            return dict(
                title=title, mode=mode, summary=result, input_characters=len(text.strip()), truncated=False,
                model=config.LOCAL_SUMMARY_MODEL_NAME, provider='local',
                processing_time=round(perf_counter()-started, 3), model_load_time=round(self.load_seconds, 3),
                chunks=len(chunks), reduction_passes=levels,
                warnings=['Experimental local summaries can be very brief or inaccurate. Verify against the source before using them for exam preparation.'],
            )
        except HTTPException:
            raise
        except MemoryError:
            raise HTTPException(503, 'Local inference ran out of memory. Close other applications and use a shorter document.') from None
        except Exception as exc:
            logger.error('Local inference failed (%s)', type(exc).__name__)
            raise HTTPException(503, 'Local inference failed. Try a shorter document and check available memory. No cloud fallback was used.') from None
        finally:
            self._lock.release()


summarization_service = SummarizationService()
