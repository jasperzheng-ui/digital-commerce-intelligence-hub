"""Bounded requests and recoverable JSON generation; never discard articles."""
import json
import os
import re
import time
from config import MODEL_BATCH_CHARS, MODEL_BATCH_ITEMS


class JsonGenerationError(RuntimeError):
    """Malformed/empty/truncated output; a source batch may be split safely."""


def batches(items, max_items=MODEL_BATCH_ITEMS, max_chars=MODEL_BATCH_CHARS):
    batch, size = [], 0
    for item in items:
        length = len(json.dumps(item, ensure_ascii=False))
        if batch and (len(batch) >= max_items or size + length > max_chars):
            yield batch
            batch, size = [], 0
        batch.append(item)
        size += length
    if batch:
        yield batch


def decode_json_object(raw):
    text = str(raw or '').strip().lstrip('\ufeff')
    text = re.sub(r'^\x60\x60\x60(?:json)?\s*', '', text, flags=re.I)
    text = re.sub(r'\s*\x60\x60\x60$', '', text).strip()
    if not text:
        raise ValueError('模型返回了空文本')
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Permit surrounding prose, but never salvage inner fragments of an
        # unfinished outer object or concatenate multiple independent objects.
        start = text.find('{')
        if start < 0:
            raise ValueError('模型未返回JSON对象') from None
        result, end = json.JSONDecoder().raw_decode(text, start)
        if any(c in text[end:] for c in '{}[]'):
            raise ValueError('模型返回了多个JSON对象或对象后有无效数据')
    if not isinstance(result, dict):
        raise ValueError('AI必须返回JSON对象')
    return result


def _diagnostic(response):
    candidates = getattr(response, 'candidates', None) or []
    reason = getattr(candidates[0], 'finish_reason', None) if candidates else None
    reason = getattr(reason, 'value', reason)
    reason = str(reason or 'unknown').split('.')[-1]
    usage = getattr(response, 'usage_metadata', None)
    return reason, (f'finish_reason={reason}; prompt_tokens={getattr(usage, "prompt_token_count", None)}; '
                    f'output_tokens={getattr(usage, "candidates_token_count", None)}')


def generate_json(prompt, purpose, response_schema=None, validator=None):
    from google import genai
    from intelligence.gemini import GEMINI_MODEL
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('Missing GEMINI_API_KEY environment variable.')
    client = genai.Client(api_key=api_key)
    config = {'response_mime_type': 'application/json', 'max_output_tokens': 16384}
    if response_schema is not None:
        config['response_schema'] = response_schema
    last = ''
    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=config)
        except Exception as exc:
            code = str(getattr(exc, 'code', None) or getattr(exc, 'status_code', None) or 'unknown')
            detail = str(exc).replace(api_key, '[REDACTED]')[:400]
            print(f'[gemini-api] purpose={purpose}; attempt={attempt}/3; code={code}; {detail}', flush=True)
            if code not in {'429', '500', '502', '503', '504'} or attempt == 3:
                raise RuntimeError(f'{purpose} API请求失败（code={code}），尚未发送邮件。{detail}') from None
            time.sleep(2 ** attempt)
            continue
        reason, diagnostic = _diagnostic(response)
        if reason in {'SAFETY', 'RECITATION', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'SPII'}:
            raise RuntimeError(f'{purpose}被模型阻止，尚未发送邮件。{diagnostic}')
        raw = ''
        try:
            if reason == 'MAX_TOKENS':
                raise ValueError('模型输出达到token上限，不能使用未完成的JSON')
            raw = response.text or ''
            result = decode_json_object(raw)
            if validator is not None:
                validator(result)
            return result
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            last = f'{diagnostic}; response_chars={len(raw)}; {str(exc).replace(api_key, "[REDACTED]")[:240]}'
            print(f'[gemini-json] purpose={purpose}; attempt={attempt}/3; {last}', flush=True)
            if attempt < 3:
                time.sleep(attempt)
    raise JsonGenerationError(f'{purpose}连续3次未返回完整有效JSON；尚未发送邮件。{last}')

