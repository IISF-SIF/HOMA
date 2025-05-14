import asyncio
import csv
import json
import ast
from typing import List, Dict
from main import ASYNC_HOME_AGENT

class SmartHomeEvaluator:
    def __init__(self):
        self.agent = ASYNC_HOME_AGENT()
        self.device_map = {
            "refrigerator": "fridge",
            "fridge": "fridge",
            "ac": "ac",
            "tv": "tv",
            "microwave": "microwave",
            "fan": "fan",
            "washer": "washer",
            "dryer": "dryer"
        }
        for device_name, device_type in self.agent.dict_devices.items():
            self.device_map[device_name] = device_type

    async def _full_agent_workflow(self, query: str) -> Dict:
        try:
            user_query, classification_response, start_time = await self.agent.task_by_user(eval=True, user_query=query)
            if hasattr(classification_response, 'message'):
                classification_content = classification_response.message.content
                parsed_classification = await self.agent.parse_json_response(classification_content)
            else:
                parsed_classification = {"tasks": {"concurrent": [], "sequential": []}}
            concurrent_tasks = parsed_classification.get("tasks", {}).get("concurrent", [])
            concurrent_results = []
            for task in concurrent_tasks:
                if "Input" not in task:
                    print(f"Warning: Task missing 'Input' key: {task}")
                    continue
                response = await self.agent.get_agent_response(query, task)
                if response:
                    raw_response = response.message.content if hasattr(response, 'message') else str(response)
                    parsed_response = await self.agent.parse_json_response(raw_response)
                    concurrent_results.append({
                        "device_name": task["device_name"],
                        "device_type": task["device"],
                        "task": task["Input"],
                        "raw_response": raw_response,
                        "parsed_response": parsed_response
                    })
            sequential_tasks = parsed_classification.get("tasks", {}).get("sequential", [])
            sequential_results = []
            for task in sequential_tasks:
                if "Input" not in task:
                    print(f"Warning: Task missing 'Input' key: {task}")
                    continue
                response = await self.agent.get_agent_response(query, task)
                if response:
                    raw_response = response.message.content if hasattr(response, 'message') else str(response)
                    parsed_response = await self.agent.parse_json_response(raw_response)
                    sequential_results.append({
                        "device_name": task["device_name"],
                        "device_type": task["device"],
                        "task": task["Input"],
                        "raw_response": raw_response,
                        "parsed_response": parsed_response
                    })
            return {
                "query": query,
                "classification": parsed_classification,
                "concurrent_results": concurrent_results,
                "sequential_results": sequential_results
            }
        except Exception as e:
            print(f"Error in _full_agent_workflow: {e}")
            raise

# --- Simple Evaluation Functions ---
def device_score(expected, predicted):
    # Device name match
    device_match = int(expected['device'].lower() == predicted.get('device_type', '').lower())
    # Task type match
    expected_type = expected.get('execution_type', 'concurrent').lower()
    predicted_type = predicted.get('task_type', 'concurrent').lower() if 'task_type' in predicted else (
        'sequential' if predicted.get('from') == 'sequential_results' else 'concurrent')
    task_type_match = int(expected_type == predicted_type)
    # Mode match
    expected_mode = str(expected.get('mode', '')).lower()
    actual_mode = ''
    parsed = predicted.get('parsed_response', {})
    if isinstance(parsed, dict):
        if 'mode' in parsed:
            actual_mode = str(parsed['mode']).lower()
        else:
            for v in parsed.values():
                if isinstance(v, dict) and 'mode' in v:
                    actual_mode = str(v['mode']).lower()
    mode_match = int(expected_mode == actual_mode)
    # Args match
    expected_args = expected.get('args', {})
    actual_args = {}
    if isinstance(parsed, dict):
        if 'mode' in parsed:
            actual_args = {k: v for k, v in parsed.items() if k != 'mode'}
        else:
            for v in parsed.values():
                if isinstance(v, dict) and 'mode' in v:
                    actual_args = {k: v for k, v in v.items() if k != 'mode'}
    if not expected_args and not actual_args:
        args_match = 1
    elif expected_args and actual_args:
        match = True
        for k, v in expected_args.items():
            if k not in actual_args or str(actual_args[k]).lower() != str(v).lower():
                match = False
        args_match = int(match)
    else:
        args_match = 0
    # Weighted total
    weighted = 0.4 * device_match + 0.25 * mode_match + 0.25 * args_match + 0.1 * task_type_match
    return {
        'weighted_total': weighted,
        'device_score': device_match,
        'task_type_score': task_type_match,
        'mode_score': mode_match,
        'args_score': args_match
    }

def find_predicted_device(expected, agent_results):
    # Try to find the predicted device in both concurrent and sequential results
    device = expected['device'].lower()
    for r in agent_results['concurrent_results']:
        if r['device_type'].lower() == device:
            r = dict(r)
            r['task_type'] = 'concurrent'
            r['from'] = 'concurrent_results'
            return r
    for r in agent_results['sequential_results']:
        if r['device_type'].lower() == device:
            r = dict(r)
            r['task_type'] = 'sequential'
            r['from'] = 'sequential_results'
            return r
    # If not found, return an empty prediction
    return {
        'device_type': '',
        'task_type': '',
        'parsed_response': {},
        'from': '',
    }

def extract_predicted_fields(predicted):
    # Extract device, task_type, mode, args from predicted result
    device = predicted.get('device_type', '')
    task_type = predicted.get('task_type', '')
    parsed = predicted.get('parsed_response', {})
    mode = ''
    args = {}
    if isinstance(parsed, dict):
        if 'mode' in parsed:
            mode = str(parsed['mode'])
            args = {k: v for k, v in parsed.items() if k != 'mode'}
        else:
            for v in parsed.values():
                if isinstance(v, dict) and 'mode' in v:
                    mode = str(v['mode'])
                    args = {k: v for k, v in v.items() if k != 'mode'}
    return {
        'device': device,
        'task_type': task_type,
        'mode': mode,
        'args': args
    }

def extract_actual_fields(expected):
    return {
        'device': expected.get('device', ''),
        'task_type': expected.get('execution_type', 'concurrent'),
        'mode': expected.get('mode', ''),
        'args': expected.get('args', {})
    }

async def evaluate_query(evaluator, query: str, language:str, expected_devices: List[Dict]) -> Dict:
    print(f"\n{'='*60}\nEvaluating Query: {query}\n{'='*60}")
    agent_results = await evaluator._full_agent_workflow(query)
    device_entries = []
    device_scores = []
    for expected in expected_devices:
        predicted = find_predicted_device(expected, agent_results)
        actual_fields = extract_actual_fields(expected)
        predicted_fields = extract_predicted_fields(predicted)
        score = device_score(expected, predicted)
        device_entries.append({
            'actual': actual_fields,
            'predicted': predicted_fields,
            'score': score
        })
        device_scores.append(score)
    # Aggregate per-query scores
    if device_scores:
        query_device_score = sum(s['device_score'] for s in device_scores) / len(device_scores)
        query_task_type_score = sum(s['task_type_score'] for s in device_scores) / len(device_scores)
        query_mode_score = sum(s['mode_score'] for s in device_scores) / len(device_scores)
        query_args_score = sum(s['args_score'] for s in device_scores) / len(device_scores)
        query_weighted_total = sum(s['weighted_total'] for s in device_scores) / len(device_scores)
    else:
        query_device_score = query_task_type_score = query_mode_score = query_args_score = query_weighted_total = 1.0
    print(f"{'-'*60}\nEvaluation Complete for Query\n{'-'*60}\n")
    return {
        'query': query,
        'language': language,
        'devices': device_entries,
        'query_score': {
            'query_weighted_total': query_weighted_total,
            'query_device_score': query_device_score,
            'query_task_type_score': query_task_type_score,
            'query_mode_score': query_mode_score,
            'query_args_score': query_args_score
        }
    }

async def evaluate_csv(csv_path: str, output_path: str):
    evaluator = SmartHomeEvaluator()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    results = []
    for idx, row in enumerate(rows):
        print(f"\n{'#'*40}\nEvaluating Query {idx+1}/{len(rows)}\n{'#'*40}")
        query = row['generated_query']
        language = row['language']
        expected_devices = ast.literal_eval(row['device_info'])
        for device in expected_devices:
            if 'device' in device:
                device['device'] = device['device'].lower()
        evaluation = await evaluate_query(evaluator, query, language, expected_devices)
        results.append(evaluation)
    with open(output_path.replace('.csv', '.json'), 'w', encoding='utf-8') as f:
        summary = {
            'overall_average': sum(r['query_score']['query_weighted_total'] for r in results) / len(results) if results else 0,
            'query_scores': results
        }
        json.dump(summary, f, indent=2)
    print(f"\nAll queries evaluated. Results written to {output_path}")

async def main():
    await evaluate_csv('11_languages_200_points_dataset.csv', 'evaluation_report_qwen2.5:32b.json')

if __name__ == "__main__":
    asyncio.run(main())