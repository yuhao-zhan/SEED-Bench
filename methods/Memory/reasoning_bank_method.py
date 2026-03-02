"""
ReasoningBank (parallel MaTTS) for 2D_exploration.
Paper: ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory (arXiv:2509.25140).
Memory: structured items (title, description, content) from success and failure;
retrieve by embedding similarity; parallel = K solutions per iteration, self-contrast then distill.
"""
import os
import sys
import json
from typing import Optional, Tuple, Any, List, Dict

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DAVINCI_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))
_MEMENTO_ROOT = os.path.join(_DAVINCI_ROOT, "baseline", "Memory", "Memento")
if os.path.isdir(_MEMENTO_ROOT) and _MEMENTO_ROOT not in sys.path:
    sys.path.insert(0, _MEMENTO_ROOT)

MEMORY_TOP_K = int(os.environ.get("REASONING_BANK_TOP_K", "5"))
DEFAULT_EMBEDDING_PATH = "/home/test/testdata/models/sup-simcse-bert-base-uncased"
_embedding_tokenizer = None
_embedding_model = None


def _get_embedding_model(device_str: str = "auto"):
    """Lazy load Sup-SimCSE (same as Memento) for retrieval."""
    global _embedding_tokenizer, _embedding_model
    if _embedding_tokenizer is not None and _embedding_model is not None:
        return _embedding_tokenizer, _embedding_model
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
        local_path = os.environ.get("REASONING_BANK_EMBEDDING_PATH", DEFAULT_EMBEDDING_PATH)
        if local_path and os.path.isdir(local_path):
            _embedding_tokenizer = AutoTokenizer.from_pretrained(local_path, local_files_only=True)
            _embedding_model = AutoModel.from_pretrained(local_path, local_files_only=True)
        else:
            _embedding_tokenizer = AutoTokenizer.from_pretrained("princeton-nlp/sup-simcse-bert-base-uncased")
            _embedding_model = AutoModel.from_pretrained("princeton-nlp/sup-simcse-bert-base-uncased")
        if device_str != "cpu" and torch.cuda.is_available():
            _embedding_model = _embedding_model.to("cuda")
        else:
            _embedding_model = _embedding_model.to("cpu")
        return _embedding_tokenizer, _embedding_model
    except Exception as e:
        raise RuntimeError(f"ReasoningBank: failed to load embedding model: {e}") from e


def get_memory_path(
    output_dir: str,
    task_name: str,
    model_identifier: str,
    run_number: Optional[int] = None,
) -> str:
    """Path to ReasoningBank JSONL for this (task, model, run)."""
    base = os.path.join(output_dir, task_name, model_identifier, "reasoning_bank")
    os.makedirs(base, exist_ok=True)
    run = run_number if run_number is not None else 1
    return os.path.join(base, f"memory_{run}.jsonl")


def _item_to_text(item: dict) -> str:
    """Concatenate title, description, content for embedding."""
    t = item.get("title") or ""
    d = item.get("description") or ""
    c = item.get("content") or ""
    return (t + "\n" + d + "\n" + c).strip()


def load_bank(path: str) -> List[dict]:
    """Load ReasoningBank items from JSONL. Each line: {title, description, content, success (optional)}."""
    if not path or not os.path.exists(path):
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def save_bank(path: str, items: List[dict]) -> None:
    """Write all items to JSONL."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _embed(text: str, tokenizer, model, device: str = "cpu", max_length: int = 256):
    """Get embedding vector for text (CLS or mean pool)."""
    import torch
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
    if device.startswith("cuda") and torch.cuda.is_available():
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
    with torch.no_grad():
        out = model(**inputs)
    # mean pooling
    last_hidden = out.last_hidden_state
    mask = inputs.get("attention_mask", None)
    if mask is not None:
        mask = mask.unsqueeze(-1).float()
        return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
    return last_hidden.mean(1)


def retrieve_for_prompt(
    task_prompt: Any,
    last_feedback: Optional[str],
    bank_items: List[dict],
    top_k: int = MEMORY_TOP_K,
    device_str: str = "auto",
) -> str:
    """Retrieve top-k relevant memory items by embedding similarity. Return formatted string.
    Query is task_description + last_feedback only (NOT the full prompt), so ICL examples
    and other task text are not used as query and do not add noise to retrieval."""
    if not bank_items:
        return "(No relevant memories yet.)"
    if task_prompt is None:
        query = ""
    elif isinstance(task_prompt, dict):
        query = (task_prompt.get("task_description") or "").strip()
    else:
        query = str(task_prompt).strip()
    if last_feedback and last_feedback.strip():
        query = (query + "\n" + last_feedback.strip()).strip()
    if not query:
        query = "task and feedback"

    try:
        tokenizer, model = _get_embedding_model(device_str)
        dev = next(model.parameters()).device
        q_emb = _embed(query, tokenizer, model, str(dev))
        q_emb = q_emb / q_emb.norm(dim=1, keepdim=True)
        scores = []
        for i, item in enumerate(bank_items):
            text = _item_to_text(item)
            if not text:
                scores.append((i, 0.0))
                continue
            emb = _embed(text, tokenizer, model, str(dev))
            emb = emb / emb.norm(dim=1, keepdim=True)
            sc = (q_emb @ emb.T).item()
            scores.append((i, sc))
        scores.sort(key=lambda x: -x[1])
        top_indices = [idx for idx, _ in scores[:top_k]]
    except Exception as e:
        print(f"[WARN] ReasoningBank retrieve failed: {e}", flush=True)
        top_indices = list(range(min(top_k, len(bank_items))))

    parts = []
    for idx in top_indices:
        item = bank_items[idx]
        t = item.get("title") or "Strategy"
        d = item.get("description") or ""
        c = item.get("content") or ""
        parts.append(f"## {t}\n{d}\n\n{c}")
    return "\n\n---\n\n".join(parts) if parts else "(No relevant memories yet.)"


def judge_success(score: float, success: bool) -> bool:
    """Use verifier outcome as judge (no LLM). Paper uses LLM-as-judge; we use task success for simplicity."""
    return success or (score >= 99.0)


def extract_memory_items_llm(
    task_description: str,
    code: str,
    feedback: str,
    score: float,
    success: bool,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "deepseek-v3.2",
) -> List[Dict[str, str]]:
    """Use LLM to extract 1-3 (title, description, content) memory items from one trajectory."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"), base_url=base_url)
    except Exception as e:
        print(f"[WARN] ReasoningBank extract LLM not available: {e}", flush=True)
        return _extract_memory_items_fallback(task_description, code, feedback, score, success)

    role = "success" if success else "failure"
    prompt = f"""You are distilling a reasoning strategy from one attempt at a physics/code task.

Task (summary): {task_description}

Attempt outcome: {role}. Score: {score:.1f}/100.
Code: {code if code else "(none)"}
Feedback: {feedback if feedback else "(none)"}

Output 1 to 3 memory items. Each item must have exactly:
- title: short phrase (e.g. "Use pivot for launcher")
- description: one sentence summary
- content: 2-4 sentences with reasoning steps or pitfalls to avoid

Format as JSON array of objects with keys title, description, content. No other text."""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=65536,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Parse JSON array
        if "```" in text:
            for block in text.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("["):
                    items = json.loads(block)
                    break
        else:
            items = json.loads(text)
        if not isinstance(items, list):
            items = [items]
        out = []
        for it in items[:3]:
            if isinstance(it, dict) and ("title" in it or "content" in it):
                out.append({
                    "title": str(it.get("title", "")).strip() or "Strategy",
                    "description": str(it.get("description", "")).strip(),
                    "content": str(it.get("content", "")).strip(),
                    "success": success,
                })
        return out if out else _extract_memory_items_fallback(task_description, code, feedback, score, success)
    except Exception as e:
        print(f"[WARN] ReasoningBank extract parse failed: {e}", flush=True)
        return _extract_memory_items_fallback(task_description, code, feedback, score, success)


def _extract_memory_items_fallback(
    task_description: str,
    code: str,
    feedback: str,
    score: float,
    success: bool,
) -> List[Dict[str, str]]:
    """Fallback when LLM not available: one item from template."""
    role = "Success" if success else "Failure"
    title = f"{role} (score {score:.0f})"
    desc = f"Attempt scored {score:.1f}; feedback: {(feedback or '')}"
    content = f"Outcome: {role}. Feedback: {(feedback or '')}"
    return [{"title": title, "description": desc, "content": content, "success": success}]


def contrast_and_distill(
    trajectories: List[Dict[str, Any]],
    task_description: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    judge_model: str = "deepseek-v3.2",
) -> List[Dict[str, str]]:
    """
    Self-contrast across K trajectories and distill consolidated memory items.
    trajectories: list of {code, feedback, score, success}.
    Returns list of (title, description, content) items to add to bank.
    """
    if not trajectories:
        return []
    # Option A: extract from each trajectory and merge (no extra contrast LLM)
    all_items = []
    for t in trajectories:
        success = judge_success(t.get("score", 0), t.get("success", False))
        items = extract_memory_items_llm(
            task_description,
            t.get("code") or "",
            t.get("feedback") or "",
            t.get("score", 0),
            success,
            api_key=api_key,
            base_url=base_url,
            model=judge_model,
        )
        all_items.extend(items)
    return all_items


def consolidate_and_save(bank_path: str, current_items: List[dict], new_items: List[dict]) -> List[dict]:
    """Append new_items to current_items, save to bank_path, return updated list."""
    updated = list(current_items) + list(new_items)
    save_bank(bank_path, updated)
    return updated


def store_after_iteration(
    bank_path: str,
    current_items: List[dict],
    new_items: List[dict],
) -> List[dict]:
    """Convenience: consolidate and return updated items."""
    return consolidate_and_save(bank_path, current_items, new_items)


def restore_memory_from_base_log(base_log: Any, bank_path: str) -> List[dict]:
    """Replay base task's ReasoningBank items into bank_path (for mutated tasks). Returns loaded items."""
    if not base_log or not bank_path:
        return []
    history = base_log.get("iteration_history") or []
    items = []
    for item in history:
        for stored in item.get("reasoning_bank_stored_items") or []:
            if isinstance(stored, dict) and (stored.get("title") is not None or stored.get("content")):
                items.append(stored)
    if not items:
        return []
    # Append to existing or create
    existing = load_bank(bank_path)
    all_items = existing + items
    save_bank(bank_path, all_items)
    return all_items
