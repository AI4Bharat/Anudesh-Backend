import csv
import json
from datetime import datetime

def MultiModelInteractionValidator(file):
    required_fields = {
        "instance_id",
        "parent_interaction_ids",
        "multiple_interaction_json",
        "language",
        "datetime",
    }
    optional_fields = {
        "eval_form_json",
        "no_of_turns",
        "no_of_models",
    }
    valid_languages = [
        "English", "Assamese", "Bengali", "Bodo", "Dogri", "Gujarati",
        "Hindi", "Kannada", "Kashmiri", "Konkani", "Maithili",
        "Malayalam", "Manipuri", "Marathi", "Nepali", "Odia",
        "Punjabi", "Sanskrit", "Santali", "Sindhi", "Sinhala",
        "Tamil", "Telugu", "Urdu"
    ]

    errors = []

    # Open the file using the uploaded file object
    reader = csv.DictReader(file.read().decode("utf-8-sig").splitlines())

    for index, row in enumerate(reader, start=1):
        row_fields = set(row.keys())

        # Check required fields
        missing_required = required_fields - row_fields
        if missing_required:
            errors.append(f"Row {index} missing required fields: {missing_required}")

        # Check unexpected fields
        unexpected_fields = row_fields - (required_fields | optional_fields)
        if unexpected_fields:
            errors.append(f"Row {index} has unexpected fields: {unexpected_fields}")

        # Validate specific fields
        if row["instance_id"] is None:
            errors.append(f"Row {index} must have 'instance_id'")

        # Validate parent_interaction_ids
        if row["parent_interaction_ids"]:
            if not (row["parent_interaction_ids"].startswith("[") and row["parent_interaction_ids"].endswith("]")):
                errors.append(f"Row {index}: parent_interaction_ids should be a JSON array format")

        # Validate multiple_interaction_json
        try:
            interactions = json.loads(row["multiple_interaction_json"])
            for interaction in interactions:
                if "prompt" not in interaction:
                    errors.append(f"Row {index}: Each interaction must contain 'prompt'")
                if "prompt_output_pair_id" not in interaction:
                    errors.append(f"Row {index}: Each interaction must contain 'prompt_output_pair_id'")
                if "model_responses_json" not in interaction:
                    errors.append(f"Row {index}: Each interaction must contain 'model_responses_json'")
                for model_response in interaction["model_responses_json"]:
                    for response_key, response_value in model_response.items():
                        if "model_name" not in response_value:
                            errors.append(f"Row {index}: {response_key} should contain 'model_name'")
                        if "output" not in response_value:
                            errors.append(f"Row {index}: {response_key} should contain 'output'")
        except json.JSONDecodeError:
            errors.append(f"Row {index}: multiple_interaction_json must be valid JSON")

        # Validate language
        if row["language"] not in valid_languages:
            errors.append(f"Row {index}: Invalid language '{row['language']}'")

        # Validate datetime
        if row["datetime"]:
            try:
                datetime.fromisoformat(row["datetime"])
            except ValueError:
                errors.append(f"Row {index}: Invalid datetime format for '{row['datetime']}'")

        # Validate optional fields
        for field in optional_fields:
            if row[field]:
                if field in ["no_of_turns", "no_of_models"] and not row[field].isdigit():
                    errors.append(f"Row {index}: {field} should be an integer if provided")

    return errors
