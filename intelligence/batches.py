"""Request-sized batches; limits never truncate the complete candidate pool."""
import json
import os
from config import MODEL_BATCH_CHARS, MODEL_BATCH_ITEMS


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


def generate_json(prompt, purpose):
    from google import genai
    from intelligence.gemini import GEMINI_MODEL, _strip_json_fence
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('Missing GEMINI_API_KEY environment variable.')
    try:
        response = genai.Client(api_key=api_key).models.generate_content(model=GEMINI_MODEL, contents=prompt)
        result = json.loads(_strip_json_fence(response.text or ''))
        if not isinstance(result, dict):
            raise ValueError('AI必须返回JSON对象。')
        return result
    except Exception as exc:
        detail = str(exc).replace(api_key, '[REDACTED]')
        raise RuntimeError(f'{purpose}失败，尚未发送邮件。{detail[:500]}') from None
