import os

# https://pypi.org/project/openai/
# import openai
# from django.http import JsonResponse
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


# def generate_response_from_gpt(gpt_prompt):
#     messages = []
#     for prompt in gpt_prompt:
#         messages.append({"role": "user", "content": prompt})
#     organisation_key = os.getenv("organisation_key")
#     openai.api_key = os.getenv("api_key_gpt_3.5")
#     client = OpenAI(api_key=openai.api_key, organization=organisation_key)
#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=messages
#     )
#     return response.choices[0].message.content.strip()


# import langdetect
#
# def check_language_consistency(texts, target_language):
#     """
#     Checks if all paragraphs/sentences in the given text are in the same language.
#
#     Args:
#         texts (list): A list of paragraphs or sentences to check.
#         target_language (str): The language code to check against (e.g., 'en', 'fr', 'es').
#
#     Returns:
#         bool: True if all texts are in the target language, False otherwise.
#     """
#     try:
#         detected_languages = set(langdetect.detect(text) for text in texts)
#         return len(detected_languages) == 1 and target_language in detected_languages
#     except langdetect.lang_detect_exception.LangDetectException:
#         return False


import re
from openai import OpenAI, AsyncOpenAI
import requests
from rest_framework import status
from rest_framework.response import Response
from dataset.models import GPT35, GPT4, LLAMA2, GPT4O, GPT4OMini, SARVAM_M


def process_history(history):
    messages = []
    for turn in history:
        user_side = {"role": "user", "content": turn["prompt"]}
        messages.append(user_side)
        system_side = {"role": "assistant", "content": turn["output"]}
        messages.append(system_side)
    return messages

# --- RETIRED LEGACY FUNCTIONS (kept as dead code for rollback) ---

# def get_gpt4_output(system_prompt, user_prompt, history, model):
#     if model == "GPT4":
#         deployment = os.getenv("LLM_INTERACTIONS_OPENAI_ENGINE_GPT_4")
#     elif model == "GPT4O":
#         deployment = os.getenv("LLM_INTERACTIONS_OPENAI_ENGINE_GPT_4O")
#     elif model == "GPT4OMini":
#         deployment = os.getenv("LLM_INTERACTIONS_OPENAI_ENGINE_GPT_4O_MINI")
#     else:
#         deployment = model
#     
#     client = OpenAI(
#         api_key=os.getenv("OPENAI_API_KEY"),
#         base_url=f"{os.getenv('LLM_INTERACTIONS_OPENAI_API_BASE')}openai/deployments/{deployment}"
#     )
#
#     history_messages = process_history(history)
#     messages = [{"role": "system", "content": system_prompt}]
#     messages.extend(history_messages)
#     messages.append({"role": "user", "content": user_prompt})
#
#     try:
#         response = client.chat.completions.create(
#             model=deployment,
#             messages=messages,
#             temperature=0.7,
#             max_tokens=2048,
#             top_p=0.95,
#             frequency_penalty=0,
#             presence_penalty=0,
#             extra_query={"api-version": os.getenv("LLM_INTERACTIONS_OPENAI_API_VERSION")},
#         )
#
#         return response.choices[0].message.content.strip()
#
#     except Exception as e:
#         err_msg = str(e)
#         if "InvalidRequestError" in err_msg:
#             message = "Prompt violates LLM policy. Please enter a new prompt."
#             st = status.HTTP_400_BAD_REQUEST
#         elif "KeyError" in err_msg:
#             message = "Invalid response from the LLM"
#             st = status.HTTP_500_INTERNAL_SERVER_ERROR
#         else:
#             message = f"An error occurred while interacting with LLM: {err_msg}"
#             st = status.HTTP_500_INTERNAL_SERVER_ERROR
#         return Response({"message": message}, status=st)
#
# def get_gpt3_output(system_prompt, user_prompt, history):
#     model = os.getenv("LLM_INTERACTIONS_OPENAI_ENGINE_GPT35")
#
#     client = OpenAI(
#         api_key=os.getenv("OPENAI_API_KEY"),
#         base_url=f"{os.getenv('LLM_INTERACTIONS_OPENAI_API_BASE')}openai/deployments/{model}"
#     )
#
#     history_messages = process_history(history)
#     messages = [{"role": "system", "content": system_prompt}]
#     messages.extend(history_messages)
#     messages.append({"role": "user", "content": user_prompt})
#
#     try:
#         response = client.chat.completions.create(
#             model=model,
#             messages=messages,
#             temperature=0.7,
#             max_tokens=2048,
#             top_p=0.95,
#             frequency_penalty=0,
#             presence_penalty=0,
#             extra_query={"api-version": os.getenv("LLM_INTERACTIONS_OPENAI_API_VERSION")},
#         )
#
#         return response.choices[0].message.content.strip()
#
#     except Exception as e:
#         err_msg = str(e)
#         if "InvalidRequestError" in err_msg:
#             message = "Prompt violates LLM policy. Please enter a new prompt."
#             st = status.HTTP_400_BAD_REQUEST
#         elif "KeyError" in err_msg:
#             message = "Invalid response from the LLM"
#             st = status.HTTP_500_INTERNAL_SERVER_ERROR
#         else:
#             message = f"An error occurred while interacting with LLM: {err_msg}"
#             st = status.HTTP_500_INTERNAL_SERVER_ERROR
#         return Response({"message": message}, status=st)
#
# def get_llama2_output(system_prompt, conv_history, user_prompt):
#     api_base = os.getenv("LLM_INTERACTION_LLAMA2_API_BASE")
#     token = os.getenv("LLM_INTERACTION_LLAMA2_API_TOKEN")
#     url = f"{api_base}/chat/completions"
#
#     history = process_history(conv_history)
#     messages = [{"role": "system", "content": system_prompt}]
#     messages.extend(history)
#     messages.append({"role": "user", "content": user_prompt})
#
#     body = {
#         "model": "meta-llama/Llama-2-70b-chat-hf",
#         "messages": messages,
#         "temperature": 0.2,
#         "max_new_tokens": 500,
#         "top_p": 1,
#     }
#     try:
#         s = requests.Session()
#         result = s.post(url, headers={"Authorization": f"Bearer {token}"}, json=body)
#         result.raise_for_status()
#         return result.json()["choices"][0]["message"]["content"].strip()
#     except Exception as e:
#         err_msg = str(e)
#         message = f"An error occurred while interacting with Llama2 API: {err_msg}"
#         st = status.HTTP_500_INTERNAL_SERVER_ERROR
#         return Response({"message": message}, status=st)
#
# def get_sarvam_m_output(system_prompt, conv_history, user_prompt):
#     api_base = os.getenv("SARVAM_M_API_BASE")
#     api_key = os.getenv("SARVAM_M_API_KEY") 
#     url = f"{api_base}/chat/completions"
#
#     headers = {
#         "api-subscription-key": api_key,
#         "Content-Type": "application/json"
#     }
#
#     history = process_history(conv_history)
#     messages = [{"role": "system", "content": system_prompt}]
#     messages.extend(history)
#     if type(user_prompt) == list:
#         messages.append({"role": "user", "content": user_prompt[0]['text']})
#     else:
#         messages.append({"role": "user", "content": user_prompt})
#
#     body = {
#         "model": "sarvam-m",
#         "messages": messages,
#         "temperature": 0.2,
#         "max_tokens": 2048,
#         "top_p": 1,
#         "reasoning_effort": None,
#     }
#     
#     try:
#         s = requests.Session()
#         response = s.post(url, headers=headers, json=body)
#         response.raise_for_status() 
#         response_data = response.json()
#         return response_data["choices"][0]["message"]["content"].strip()
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred during the API request: {e}")
#         raise
#     except (KeyError, IndexError) as e:
#         print(f"Error parsing the API response: {e}")
#         print(f"Full response data: {response_data}")
#         raise

# --- END RETIRED LEGACY FUNCTIONS ---

# Google AI Studio models (via OpenAI-compatible endpoint)
GOOGLE_AI_STUDIO_MODELS = {
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite",
}

def get_google_ai_studio_output(system_prompt, user_prompt, history, model):
    try:
        client = OpenAI(
            api_key=os.getenv("GOOGLE_AI_STUDIO_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

        history_messages = process_history(history)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": user_prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        err_msg = str(e)
        if "InvalidRequestError" in err_msg:
            message = "Prompt violates LLM policy. Please enter a new prompt."
            st = status.HTTP_400_BAD_REQUEST
        elif "KeyError" in err_msg:
            message = "Invalid response from the LLM"
            st = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            message = f"An error occurred while interacting with LLM: {err_msg}"
            st = status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({"message": message}, status=st)

def get_deepinfra_output(system_prompt, user_prompt, history, model):
    try:
        client = OpenAI(
            api_key=os.getenv("DEEPINFRA_API_KEY"),
            base_url=os.getenv("DEEPINFRA_BASE_URL")
        )

        history_messages = process_history(history)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": user_prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )

        output = response.choices[0].message.content.strip()
        cleaned_response = re.sub(r'<think>.*?</think>\s*', '', output, flags=re.DOTALL)
        return cleaned_response

    except Exception as e:
        err_msg = str(e)
        if "InvalidRequestError" in err_msg:
            message = "Prompt violates LLM policy. Please enter a new prompt."
            st = status.HTTP_400_BAD_REQUEST
        elif "KeyError" in err_msg:
            message = "Invalid response from the LLM"
            st = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            message = f"An error occurred while interacting with LLM: {err_msg}"
            st = status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({"message": message}, status=st)
    
def get_model_output(system_prompt, user_prompt, history, model="google/gemma-4-26B-A4B-it"):
    # Assume that translation happens outside (and the prompt is already translated)
    out = ""
    if model in GOOGLE_AI_STUDIO_MODELS:
        out = get_google_ai_studio_output(system_prompt, user_prompt, history, model)
    else:
        out = get_deepinfra_output(system_prompt, user_prompt, history, model)
    return out

def get_all_model_output(system_prompt_data, user_prompt, history, models_to_run, default_system_prompt=""):
    results = {}

    for model in models_to_run:
        system_prompt = system_prompt_data.get(model) or system_prompt_data.get("default") or default_system_prompt if isinstance(system_prompt_data, dict) else system_prompt_data
        # print("history:", history)
        # model_history = next(
        #     (entry["interaction_json"] for entry in history if entry.get("model_name") == model),
        #     []
        # )
        model_history = next(
            (
                interaction["interaction_json"]
                for interaction in history.get("model_interactions", [])
                if interaction.get("model_name") == model
            ),
            []
        )
        if model in GOOGLE_AI_STUDIO_MODELS:
            results[model] = get_google_ai_studio_output(system_prompt, user_prompt, model_history, model)
        else:
            results[model] = get_deepinfra_output(system_prompt, user_prompt, model_history, model)

        if isinstance(results[model], Response):
            return results[model]
    
    return results

# ── Async streaming generators (Django 5 + ASGI) ────────────────────────────

_google_client = None
_deepinfra_client = None

def _get_google_client() -> AsyncOpenAI:
    global _google_client
    if _google_client is None:
        _google_client = AsyncOpenAI(
            api_key=os.getenv("GOOGLE_AI_STUDIO_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return _google_client

def _get_deepinfra_client() -> AsyncOpenAI:
    global _deepinfra_client
    if _deepinfra_client is None:
        _deepinfra_client = AsyncOpenAI(
            api_key=os.getenv("DEEPINFRA_API_KEY"),
            base_url=os.getenv("DEEPINFRA_BASE_URL"),
        )
    return _deepinfra_client

async def stream_google_ai_studio_output(system_prompt, user_prompt, history, model):
    client = _get_google_client()
    history_messages = process_history(history)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": user_prompt})

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"[ERROR] {e}"


async def stream_deepinfra_output(system_prompt, user_prompt, history, model):
    client = _get_deepinfra_client()
    history_messages = process_history(history)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": user_prompt})

    # State machine to strip <think>...</think> blocks that may span chunk boundaries
    pending = ""
    in_think = False

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            stream=True,
        )
        async for chunk in stream:
            if not (chunk.choices and chunk.choices[0].delta.content is not None):
                continue
            pending += chunk.choices[0].delta.content

            while True:
                if in_think:
                    end = pending.find("</think>")
                    if end != -1:
                        in_think = False
                        pending = pending[end + 8:].lstrip("\n")
                    else:
                        if len(pending) > 7:
                            pending = pending[-7:]
                        else:
                            pass
                        break
                else:
                    start = pending.find("<think>")
                    if start != -1:
                        if start > 0:
                            yield pending[:start]
                        in_think = True
                        pending = pending[start + 7:]
                    else:
                        # Keep last 7 chars to handle tags split across chunks
                        if len(pending) > 7:
                            yield pending[:-7]
                            pending = pending[-7:]
                        break

        if pending and not in_think:
            yield pending.lstrip("\n")
    except Exception as e:
        yield f"[ERROR] {e}"


async def stream_model_output(system_prompt, user_prompt, history, model="google/gemma-4-26B-A4B-it"):
    if model in GOOGLE_AI_STUDIO_MODELS:
        async for token in stream_google_ai_studio_output(system_prompt, user_prompt, history, model):
            yield token
    else:
        async for token in stream_deepinfra_output(system_prompt, user_prompt, history, model):
            yield token


async def stream_all_models_output(system_prompt_data, user_prompt, model_interactions, models_to_run, default_system_prompt=""):
    """
    Stream tokens from multiple models concurrently.
    Yields dicts like: {"model": "modelA", "token": "Hello"}
    and {"model": "modelA", "done": True} when a model finishes.
    """
    import asyncio

    queue = asyncio.Queue()

    async def _stream_single_model(model_name):
        """Collect tokens from one model and push them onto the shared queue."""
        system_prompt = (
            system_prompt_data.get(model_name)
            or system_prompt_data.get("default")
            or default_system_prompt
        ) if isinstance(system_prompt_data, dict) else system_prompt_data

        # Extract this model's conversation history from model_interactions
        model_history = next(
            (
                interaction["interaction_json"]
                for interaction in (model_interactions or [])
                if interaction.get("model_name") == model_name
            ),
            [],
        )

        try:
            async for token in stream_model_output(system_prompt, user_prompt, model_history, model_name):
                await queue.put({"model": model_name, "token": token})
        except Exception as e:
            await queue.put({"model": model_name, "error": str(e)})
        finally:
            await queue.put({"model": model_name, "done": True})

    # Launch all model streams concurrently
    tasks = [asyncio.create_task(_stream_single_model(m)) for m in models_to_run]

    models_remaining = len(models_to_run)
    while models_remaining > 0:
        item = await queue.get()
        if item.get("done"):
            models_remaining -= 1
        yield item

    # Ensure all tasks are cleaned up
    for t in tasks:
        if not t.done():
            t.cancel()

