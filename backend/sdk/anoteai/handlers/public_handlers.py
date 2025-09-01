import requests
import os
import re


def upload_public(API_url, headers, task_type, model_type, file_paths=None):
    if task_type == "documents": #Question-answering
        if file_paths is None:
            return {"error": "You are attempting to do question-answering. There are no files uploaded. Please upload at least one file."}
        else:
            url = f"{API_url}/public/upload"

            data = {
                "task_type": task_type,
                "model_type": model_type
            }

            files = []
            opened_files = []
            html_paths = []
            for path in file_paths:
                result = is_file_or_isHtml(path)
                if result == "file":
                    try:
                        file = open(path, 'rb')
                        opened_files.append(file)
                        files.append(("files[]", (path.split('/')[-1], file, "application/octet-stream")))
                    except Exception as e:
                        return {"error": f"Error opening file {path}: {e}"}
                elif result == "html":
                    html_paths.append(path)
                else:
                    return {"error": f"This file path {path} is not valid. Please enter a valid file path or URL."}

            data['html_paths'] = html_paths

            headers = {key: val for key, val in headers.items() if key.lower() != 'content-type'}

            try:
                response = requests.post(url, data=data, files=files, headers=headers)
                return response.json()
            except requests.exceptions.JSONDecodeError as e:
                return {"error": f"Failed to decode JSON response {e}"}
            finally:
                for file in opened_files:
                    file.close()
    else:
        return {"error": "Task type is not recognized. Please enter a valid task type."}

def is_file_or_isHtml(path):
    if os.path.isfile(path):
        return "file"
    if re.match(r'(https?://|www\.)', path):
        return "html"
    else:
        return "unknown"
