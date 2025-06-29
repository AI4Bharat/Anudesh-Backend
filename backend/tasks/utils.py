import base64
import io
import json
import os
import subprocess
from requests import RequestException
import requests
from dotenv import load_dotenv

Queued_Task_name = {
    "dataset.tasks.deduplicate_dataset_instance_items": "Deduplicate Dataset Instance Items",
    "dataset.tasks.upload_data_to_data_instance": "Upload Data to Dataset Instance",
    "functions.tasks.conversation_data_machine_translation": "Generate Machine Translations for Conversation Dataset",
    "functions.tasks.generate_asr_prediction_json": "Generate ASR Predictions for SpeechConversation Dataset",
    "functions.tasks.generate_ocr_prediction_json": "Generate OCR Prediction for OCR Document Dataset",
    "functions.tasks.populate_draft_data_json": "Populate Draft Data JSON",
    "functions.tasks.schedule_mail": "Mail Scheduled by User Profile",
    "functions.tasks.schedule_mail_for_project_reports": "Send Detailed Project Reports Mail",
    "functions.tasks.schedule_mail_to_download_all_projects": "Schedule Mail to Download All Projects",
    "functions.tasks.sentence_text_translate_and_save_translation_pairs": "Generate Machine Translations for Translation Pairs Dataset",
    "notifications.tasks.create_notification_handler": "Push Notification Created",
    "organizations.tasks.send_project_analytics_mail_org": "Send Project Analytics Mail At Organization Level",
    "organizations.tasks.send_user_analytics_mail_org": "Send User Analytics Mail At Organization Level",
    "organizations.tasks.send_user_reports_mail_org": "Send User Payment Reports Mail At Organization Level",
    "projects.tasks.add_new_data_items_into_project": "Add New Data Items into Project",
    "projects.tasks.create_parameters_for_task_creation": "Create Tasks for new Project",
    "projects.tasks.export_project_in_place": "Export Project In Place",
    "projects.tasks.export_project_new_record": "Export Project New Record",
    "send_mail_task": "Daily User Mails Scheduler",
    "send_user_reports_mail": "Send User Reports Mail ",
    "workspaces.tasks.send_project_analysis_reports_mail_ws": "Send Project Analysis Reports Mail At Workspace Level",
    "workspaces.tasks.send_user_analysis_reports_mail_ws": "Send User Analysis Reports Mail At Workspace Level",
    "workspaces.tasks.send_user_reports_mail_ws": "Send User Payment Reports Mail At Workspace Level",
}

import json


def compute_meta_stats_for_instruction_driven_chat(conversation_history):
    """
    Calculate meta stats for instruction-driven chat.

    Args:
        conversation_history (list or str): List of dicts or JSON string, each containing 'prompt' and 'output'.

    Returns:
        dict: Meta statistics JSON with 'prompts_word_count', 'number_of_turns',
              'avg_word_count_per_prompt', and 'avg_word_count_per_output'.
    """
    # Parse conversation history
    if isinstance(conversation_history, str):
        try:
            conversation_history = json.loads(conversation_history)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format"}
    elif not isinstance(conversation_history, list):
        return {"error": "Invalid input format"}

    total_prompt_words = 0
    total_output_words = 0
    number_of_turns = len(conversation_history)

    for entry in conversation_history:
        if "prompt" in entry:
            try:
                total_prompt_words += len(entry["prompt"].split())
            except:
                total_prompt_words = 0
        if "output" in entry:
            try:
                total_output_words += len(entry["output"].split())
            except:
                total_output_words = 0

    avg_word_count_per_prompt = (
        total_prompt_words / number_of_turns if number_of_turns else 0
    )
    avg_word_count_per_output = (
        total_output_words / number_of_turns if number_of_turns else 0
    )

    meta_stats = {
        "prompts_word_count": total_prompt_words,
        "number_of_turns": number_of_turns,
        "avg_word_count_per_prompt": avg_word_count_per_prompt,
        "avg_word_count_per_output": avg_word_count_per_output,
    }
    return meta_stats

def compute_meta_stats_for_multiple_llm_idc(conversation_history):
    meta_stats = {}

    for model_data in conversation_history:
        model_name = model_data.get("model_name")
        interactions = model_data.get("interaction_json", [])

        num_turns = len(interactions)
        total_prompt_len = sum(len(turn.get("prompt", "")) for turn in interactions)
        total_output_len = sum(len(turn.get("output", "")) for turn in interactions)
        average_prompt_len = total_prompt_len/num_turns if num_turns else 0
        average_output_len = total_output_len/num_turns if num_turns else 0

        meta_stats[model_name] = {
            "num_turns": num_turns,
            "total_prompt_length": total_prompt_len,
            "total_output_length": total_output_len,
            "average_prompt_length": round(average_prompt_len, 2),
            "average_output_length": round(average_output_len, 2),
        }

    return meta_stats

def query_flower(filters=None):
    try:
        load_dotenv()
        address = os.getenv("FLOWER_ADDRESS")
        port = int(os.getenv("FLOWER_PORT"))
        flower_url = f"{address}:{port}"
        tasks_url = f"http://{flower_url}/api/tasks"
        flower_username = os.getenv("FLOWER_USERNAME")
        flower_password = os.getenv("FLOWER_PASSWORD")
        response = requests.get(tasks_url, auth=(flower_username, flower_password))

        if response.status_code == 200:
            all_tasks = response.json()
            filtered_tasks = {}

            if filters:
                # Apply filtering based on the provided filters
                for task_id, task in all_tasks.items():
                    if all(task.get(key) == value for key, value in filters.items()):
                        filtered_tasks[task_id] = task
            else:
                filtered_tasks = all_tasks

            return filtered_tasks
        elif response.status_code == 503:
            return {"error": "Service temporarily unavailable, check Flower"}
        else:
            return {"error": "Failed to retrieve tasks from Flower"}
    except RequestException as e:
        return {"error": f" failed to connect to flower API, {str(e)}"}

def convert_audio_base64_to_mp3(input_base64):
        input_audio_bytes = base64.b64decode(input_base64)
        input_buffer = io.BytesIO(input_audio_bytes)

        ffmpeg_command = [
            'ffmpeg', '-i', 'pipe:0',
            '-f', 'mp3',
            'pipe:1'
        ]

        try:
            process = subprocess.Popen(
                ffmpeg_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            output_mp3_bytes, error = process.communicate(input=input_buffer.read())

            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {error.decode()}")

            output_base64_mp3 = base64.b64encode(output_mp3_bytes).decode('utf-8')
            return output_base64_mp3

        except Exception as e:
            print(f"Audio conversion error: {e}")
            return None
