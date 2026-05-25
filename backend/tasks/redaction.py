from typing import Any, List, Union
from tasks.model_registry import id_from_internal_name, internal_name_from_id

MODEL_VALUE_KEYS = {
    "model", "models", "models_set", "fixed_models",
    "modelsToRun", "models_to_run", "preferred_models",
}

def _is_model_id(s: Any) -> bool:
    return isinstance(s, str) and s.startswith("mdl_") and len(s) > 4

def _to_id(name: Any) -> Union[str, None]:
    if not isinstance(name, str):
        return None
    if _is_model_id(name):
        return name
    mid = id_from_internal_name(name.strip())
    return mid

def _to_ids(val: Union[str, List[str]]) -> List[str]:
    if isinstance(val, str):
        mid = _to_id(val)
        return [mid] if mid else []
    ids: List[str] = []
    if isinstance(val, list):
        for item in val:
            mid = _to_id(item)
            if mid:
                ids.append(mid)
    return ids

def convert_model_names_to_ids(payload: Any) -> Any:
    """
    Attach model_id siblings and (for single-project responses) convert name lists to id lists.
    """
    if isinstance(payload, dict):
        data_block = payload.get("data")
        if isinstance(data_block, dict) and "model" in data_block:
            if "model_ids" not in data_block:
                data_block["model_ids"] = _to_ids(data_block["model"])
            model_val = data_block.get("model")
            if model_val:
                if isinstance(model_val, list):
                    converted_models = []
                    for m in model_val:
                        if _is_model_id(m):
                            converted_models.append(m)
                        else:
                            mid = _to_id(m)
                            converted_models.append(mid if mid else m)
                    data_block["model"] = converted_models
                else:
                    if _is_model_id(model_val):
                        data_block["model"] = model_val
                    else:
                        mid = _to_id(model_val)
                        data_block["model"] = mid if mid else model_val

        meta = payload.get("metadata_json")
        if isinstance(meta, dict):
            is_single_project = ("id" in payload and "title" in payload) or meta.get("_single_project", False)
            
            if is_single_project:
                if "models_set" in meta:
                    meta["models_set"] = _to_ids(meta["models_set"])
                if "fixed_models" in meta:
                    meta["fixed_models"] = _to_ids(meta["fixed_models"])
                if "models_set_ids" in meta:
                    del meta["models_set_ids"]
                if "fixed_models_ids" in meta:
                    del meta["fixed_models_ids"]
                meta["_single_project"] = True
            else:
                if "models_set" in meta and "models_set_ids" not in meta:
                    meta["models_set_ids"] = _to_ids(meta["models_set"])
                if "fixed_models" in meta and "fixed_models_ids" not in meta:
                    meta["fixed_models_ids"] = _to_ids(meta["fixed_models"])

        res = payload.get("result")
        if isinstance(res, list):
            for entry in res:
                if isinstance(entry, dict):
                    mis = entry.get("model_interactions")
                    if isinstance(mis, list):
                        for item in mis:
                            if isinstance(item, dict):
                                if "model_id" not in item:
                                    name = item.get("model_name")
                                    mid = _to_id(name)
                                    if mid:
                                        item["model_id"] = mid
                                if "model_name" in item:
                                    item.pop("model_name")
                    
                    eval_form = entry.get("eval_form")
                    if isinstance(eval_form, list):
                        for eval_entry in eval_form:
                            if isinstance(eval_entry, dict):
                                mrj = eval_entry.get("model_responses_json")
                                if isinstance(mrj, list):
                                    for mrj_item in mrj:
                                        if isinstance(mrj_item, dict):
                                            if "model_name" in mrj_item:
                                                name = mrj_item.get("model_name")
                                                mid = _to_id(name)
                                                if mid:
                                                    mrj_item["model_id"] = mid
                                                mrj_item.pop("model_name")
                                            
                                            questions_response = mrj_item.get("questions_response")
                                            if isinstance(questions_response, list):
                                                for qr_item in questions_response:
                                                    if isinstance(qr_item, dict):
                                                        response = qr_item.get("response")
                                                        if isinstance(response, list):
                                                            converted_response = []
                                                            for resp_val in response:
                                                                if isinstance(resp_val, str):
                                                                    model_id = _to_id(resp_val)
                                                                    converted_response.append(model_id if model_id else resp_val)
                                                                else:
                                                                    converted_response.append(resp_val)
                                                            qr_item["response"] = converted_response
                                elif isinstance(mrj, dict):
                                    new_mrj = {}
                                    for key, value in mrj.items():
                                        model_id = _to_id(key)
                                        new_mrj[model_id if model_id else key] = value
                                    eval_entry["model_responses_json"] = new_mrj
        
        output_obj = payload.get("output")
        if isinstance(output_obj, dict):
            new_output = {}
            for key, value in output_obj.items():
                model_id = _to_id(key)
                if model_id:
                    new_output[model_id] = value
                else:
                    new_output[key] = value
            payload["output"] = new_output

        is_single_project = ("id" in payload and "title" in payload)
        if not is_single_project:
            for k, v in list(payload.items()):
                if isinstance(k, str) and k in MODEL_VALUE_KEYS:
                    sibling_key = f"{k}_ids"
                    if sibling_key not in payload:
                        ids = _to_ids(v)
                        if ids:
                            payload[sibling_key] = ids

        for v in list(payload.values()):
            convert_model_names_to_ids(v)
        
        if isinstance(payload, dict):
            meta = payload.get("metadata_json")
            if isinstance(meta, dict):
                if ("id" in payload and "title" in payload) or meta.get("_single_project"):
                    if "models_set_ids" in meta:
                        del meta["models_set_ids"]
                    if "fixed_models_ids" in meta:
                        del meta["fixed_models_ids"]
                if meta.get("_single_project"):
                    meta.pop("_single_project", None)

        if "result" in payload and isinstance(payload["result"], list):
            for item in payload["result"]:
                if isinstance(item, dict):
                    db = item.get("data")
                    if isinstance(db, dict) and "model" in db:
                        mval = db["model"]
                        if isinstance(mval, list):
                            db["model"] = _to_ids(mval)
                        else:
                            db["model"] = _to_ids(mval) if not _is_model_id(mval) else [mval]
                        db.pop("model_ids", None)

    elif isinstance(payload, list):
        for item in payload:
            convert_model_names_to_ids(item)

    return payload

def _resolve_models_to_internal_names(task) -> List[str]:
    """
    Resolve the models configured for a task into internal model name strings
    suitable for the LLM layer.
    
    This function handles UUIDs (mdl_*) by converting them to internal names.
    For MultipleLLMInstructionDrivenChat projects, models may be stored as UUIDs
    in task.data["model"] (as a list) or in project metadata (models_set/fixed_models).
    
    Returns:
        List of internal model names (e.g., ["GPT35", "GPT4"]) ready for LLM layer.
    """
    resolved: List[str] = []

    def _resolve_one(s: str) -> Union[str, None]:
        if not isinstance(s, str):
            return None
        s = s.strip()
        if not s:
            return None
        if s.startswith("mdl_"):
            try:
                return internal_name_from_id(s)
            except Exception:
                return None
        return s

    try:
        models_field = task.data.get("model", []) if isinstance(task.data, dict) else []
    except Exception:
        models_field = []

    items = models_field if isinstance(models_field, list) else [models_field]
    for m in items:
        name = _resolve_one(m)
        if name:
            resolved.append(name)

    if not resolved:
        meta = getattr(task.project_id, "metadata_json", {}) or {}
        candidates: List[str] = []

        if isinstance(meta, dict):
            for key in ("fixed_models_ids", "models_set_ids"):
                v = meta.get(key)
                if isinstance(v, list):
                    candidates.extend(v)
                elif isinstance(v, str) and v:
                    candidates.append(v)

            for key in ("fixed_models", "models_set"):
                v = meta.get(key)
                if isinstance(v, list):
                    candidates.extend(v)
                elif isinstance(v, str) and v:
                    candidates.append(v)

        for cand in candidates:
            name = _resolve_one(cand)
            if name:
                resolved.append(name)

    seen = set()
    out: List[str] = []
    for r in resolved:
        if r and r not in seen:
            seen.add(r)
            out.append(r)

    return out

def _mask_eval_form_model_keys(eval_form_item: Any) -> None:
  
    if not isinstance(eval_form_item, dict):
        return

    mrj = eval_form_item.get("model_responses_json")
    if not isinstance(mrj, dict):
        return

    new_mrj: dict = {}
    for k, v in mrj.items():
        mid = _to_id(k) or k
        new_mrj[mid] = v

    eval_form_item["model_responses_json"] = new_mrj

mask_eval_form_model_keys = _mask_eval_form_model_keys