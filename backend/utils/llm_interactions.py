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


import os
import openai
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


def get_gpt4_output(system_prompt, user_prompt, history, model):
    openai.api_type = os.getenv("LLM_INTERACTIONS_OPENAI_API_TYPE")
    openai.api_base = os.getenv("LLM_INTERACTIONS_OPENAI_API_BASE")
    openai.api_version = os.getenv("LLM_INTERACTIONS_OPENAI_API_VERSION")
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if model == GPT4:
        engine = os.getenv("LLM_INTERACTIONS_OPENAI_ENGINE_GPT_4")
    elif model == GPT4O:
        engine = os.getenv("LLM_INTERACTIONS_OPENAI_ENGINE_GPT_4O")
    elif model == GPT4OMini:
        engine = os.getenv("LLM_INTERACTIONS_OPENAI_ENGINE_GPT_4O_MINI")

    history = process_history(history)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    try:
        response = openai.ChatCompletion.create(
            engine=engine,
            messages=messages,
            temperature=0.7,
            max_tokens=700,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
        )
        return response["choices"][0]["message"]["content"].strip()
    except openai.InvalidRequestError as e:
        message = "Prompt violates LLM policy. Please enter a new prompt."
        st = status.HTTP_400_BAD_REQUEST
    except KeyError as e:
        message = "Invalid response from the LLM"
        st = status.HTTP_500_INTERNAL_SERVER_ERROR
    except Exception as e:
        message = "An error occurred while interacting with LLM."
        st = status.HTTP_500_INTERNAL_SERVER_ERROR
    return Response(
        {"message": message},
        status=st,
    )


def get_gpt3_output(system_prompt, user_prompt, history):
    openai.api_type = os.getenv("LLM_INTERACTIONS_OPENAI_API_TYPE")
    openai.api_base = os.getenv("LLM_INTERACTIONS_OPENAI_API_BASE")
    openai.api_version = os.getenv("LLM_INTERACTIONS_OPENAI_API_VERSION")
    openai.api_key = os.getenv("OPENAI_API_KEY")
    engine = os.getenv("LLM_INTERACTIONS_OPENAI_ENGINE_GPT35")

    history = process_history(history)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})
    try:
        response = openai.ChatCompletion.create(
            engine=engine,
            messages=messages,
            temperature=0.7,
            max_tokens=700,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
        )
        return response["choices"][0]["message"]["content"].strip()
    except openai.InvalidRequestError as e:
        message = "Prompt violates LLM policy. Please enter a new prompt."
        st = status.HTTP_400_BAD_REQUEST
    except KeyError as e:
        message = "Invalid response from the LLM"
        st = status.HTTP_500_INTERNAL_SERVER_ERROR
    except Exception as e:
        message = "An error occurred while interacting with LLM."
        st = status.HTTP_500_INTERNAL_SERVER_ERROR
    return Response(
        {"message": message},
        status=st,
    )


def get_llama2_output(system_prompt, conv_history, user_prompt):
    api_base = os.getenv("LLM_INTERACTION_LLAMA2_API_BASE")
    token = os.getenv("LLM_INTERACTION_LLAMA2_API_TOKEN")
    url = f"{api_base}/chat/completions"

    history = process_history(conv_history)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    body = {
        "model": "meta-llama/Llama-2-70b-chat-hf",
        "messages": messages,
        "temperature": 0.2,
        "max_new_tokens": 500,
        "top_p": 1,
    }
    s = requests.Session()
    result = s.post(url, headers={"Authorization": f"Bearer {token}"}, json=body)
    return result.json()["choices"][0]["message"]["content"].strip()

def get_sarvam_m_output(system_prompt, conv_history, user_prompt):
    api_base = os.getenv("SARVAM_M_API_BASE")
    api_key = os.getenv("SARVAM_M_API_KEY") 
    url = f"{api_base}/chat/completions"

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    history = process_history(conv_history)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    body = {
        "model": "sarvam-m",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 500,
        "top_p": 1,
    }
    
    try:
        s = requests.Session()
        response = s.post(url, headers=headers, json=body)
        response.raise_for_status() 
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        raise
    except (KeyError, IndexError) as e:
        print(f"Error parsing the API response: {e}")
        print(f"Full response data: {response_data}")
        raise

def get_deepinfra_output(system_prompt, user_prompt, history, model):
    try:
        openai.api_key = os.getenv("DEEPINFRA_API_KEY")
        openai.api_base = os.getenv("DEEPINFRA_BASE_URL")

        history_messages = process_history(history)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": user_prompt})

        response = openai.ChatCompletion.create(
            model=model, 
            messages=messages,
            temperature=0.7,
            max_tokens=700,
        )
        
        return response["choices"][0]["message"]["content"].strip()

    except openai.InvalidRequestError as e:
        message = "Prompt violates LLM policy. Please enter a new prompt."
        st = status.HTTP_400_BAD_REQUEST
    except KeyError as e:
        message = "Invalid response from the LLM"
        st = status.HTTP_500_INTERNAL_SERVER_ERROR
    except Exception as e:
        message = "An error occurred while interacting with LLM."
        st = status.HTTP_500_INTERNAL_SERVER_ERROR
    return Response(
        {"message": message},
        status=st,
    )

def get_model_output(system_prompt, user_prompt, history, model=GPT4OMini):
    # Assume that translation happens outside (and the prompt is already translated)
    out = ""
    if model == GPT35:
        out = get_gpt3_output(system_prompt, user_prompt, history)
    elif model in [GPT4, GPT4O, GPT4OMini]:
        out = get_gpt4_output(system_prompt, user_prompt, history, model)
    elif model == LLAMA2:
        out = get_llama2_output(system_prompt, history, user_prompt)
    elif model == SARVAM_M:
        out = get_sarvam_m_output(system_prompt, history, user_prompt)
    else:
        out = get_deepinfra_output(system_prompt, user_prompt, history, model)
    return out
