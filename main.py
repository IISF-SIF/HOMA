import asyncio
import json
import time
import logging
import utils.agent_prompts as agent_prompts
from utils.utils import UTILS


class ASYNC_HOME_AGENT:
    def __init__(self, max_retries=3, backoff_factor=2, max_concurrency=4):
        # Configuration
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_concurrency = max_concurrency
        
        # Device mapping
        self.dict_devices = {
            "dining_fan": "fan",
            "room_fan": "fan",
            "hall_tv": "tv",
            "room_ac": "ac",
            "fridge": "fridge",
            "washer": "washer",
            "dryer": "dryer",
            "kitchen_microwave": "microwave",
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize utilities
        self.utils_obj = UTILS()

    async def retry_with_backoff(self, coroutine_func, *args, **kwargs):
        """Execute a coroutine with exponential backoff retry logic."""
        retries = 0
        last_exception = None
        
        while retries <= self.max_retries:
            try:
                return await coroutine_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                wait_time = self.backoff_factor ** retries
                retries += 1
                
                if retries <= self.max_retries:
                    self.logger.warning(
                        f"Attempt {retries} failed with error: {str(e)}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"All {self.max_retries} retry attempts failed. "
                        f"Last error: {str(e)}"
                    )
        
        # If we've exhausted all retries, raise the last exception
        raise last_exception

    async def task_by_user(self, eval=False, user_query=None):
        """Process user input and classify the task."""
        try:
            if not eval:
                user_query = input()
            if user_query.strip().lower() == "/bye":
                return user_query, "STOP", time.time()
            
            system_message = self.utils_obj.create_message(
                "system", agent_prompts.CLASSIFICATION_PROMPT
            )
            
            user_query_formatted = (
                f"Input: {user_query}\n"
                f"List of Available Devices: {self.dict_devices}\n"
                f"Output: "
            )
            
            user_message = self.utils_obj.create_message("user", user_query_formatted)
            start_time = time.time()
            
            try:
                classification_response = await self.retry_with_backoff(
                    self.utils_obj.chat, [system_message, user_message]
                )
                self.logger.info(f"Classification response: {classification_response.message.content}")
                return user_query, classification_response, start_time
            except Exception as e:
                self.logger.error(f"Classification failed after retries: {str(e)}")
                return user_query, "ERROR", start_time
                
        except Exception as e:
            self.logger.error(f"Error in task_by_user: {str(e)}")
            return None, "ERROR", time.time()

    async def parse_json_response(self, response_text):
        """Safely parse JSON response, handling various formats."""
        if not response_text or response_text.strip() == "":
            self.logger.warning("Empty response received")
            return {"device": "", "function": "", "args": {}}
            
        try:
            # First attempt direct parsing
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks if present
            try:
                if "```json" in response_text or "```" in response_text:
                    # Extract content from code blocks
                    clean_text = response_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_text)
                else:
                    # Look for JSON-like patterns in the text
                    import re
                    json_pattern = r'({[\s\S]*})'
                    match = re.search(json_pattern, response_text)
                    if match:
                        potential_json = match.group(1)
                        return json.loads(potential_json)
                    else:
                        # Return a default structure when no JSON is found
                        self.logger.warning(f"No valid JSON found in response, returning empty structure")
                        return {"device": "", "function": "", "args": {}}
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON after cleaning: {str(e)}")
                self.logger.debug(f"Raw response: {response_text}")
                # Instead of raising an exception, return a default structure
                return {"device": "", "function": "", "args": {}}
            except Exception as e:
                self.logger.error(f"Unexpected error in parse_json_response: {str(e)}")
                return {"device": "", "function": "", "args": {}}

    async def get_agent_response(self, user_query, separated_query):
        """Get response from a specific device agent with retry logic."""
        device_name = separated_query.get("device_name", "Unknown Device")
        try:
            device = separated_query.get("device")
            decomposed_query = separated_query.get("Input", "Unknown Task")
            
            if not device:
                self.logger.error(f"Missing 'device' key in separated_query for user query: {user_query}")
                return None

            agent_prompt_value = self.utils_obj.query_by_device(device)

            system_message = self.utils_obj.create_message("system", agent_prompt_value)
            user_message = self.utils_obj.create_message(
                "user", f"Input: {decomposed_query}\nDevice Name: {device_name}\nOutput: "
            )
            
            self.logger.info(f"Sending query to {device_name} agent: {decomposed_query}")
            
            agent_response = await self.retry_with_backoff(
                self.utils_obj.chat, [system_message, user_message]
            )

            if agent_response is None:
                self.logger.error(f"Agent chat failed for {device_name} after retries.")
                return None
            
            self.logger.info(f"Response from {device_name} agent received")
            if agent_response.get('message') and agent_response['message'].get('content'):
                self.logger.debug(f"Response content: {agent_response['message']['content']}")
            else:
                self.logger.warning(f"Agent response for {device_name} missing expected message content.")
                return None

            completion_prompt = agent_prompts.COMPLETION_PROMPT.format(
                orignal_Input=user_query, task=decomposed_query
            )
            
            completion_response = await self.retry_with_backoff(
                self.utils_obj.chat,
                [self.utils_obj.create_message("user", completion_prompt)]
            )

            if completion_response is None or not completion_response.get('message') or not completion_response['message'].get('content'):
                self.logger.error(f"Completion chat failed or returned invalid response for {device_name} after retries.")
                return agent_response

            self.logger.info(
                f"Task completion for {device_name}: {completion_response['message']['content']}"
            )
            
            return agent_response
            
        except KeyError as e:
            self.logger.error(f"KeyError in get_agent_response for {device_name}: Missing key {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in get_agent_response for {device_name}: {str(e)}", exc_info=True)
            return None

    async def execute_tasks(self, tasks, user_query, semaphore=None):
        """Execute a list of tasks, either concurrently or sequentially."""
        results = []
        
        for task_data in tasks:
            try:
                if semaphore:
                    async with semaphore:
                        result = await self.get_agent_response(user_query, task_data)
                else:
                    result = await self.get_agent_response(user_query, task_data)
                
                results.append(result)
                
                if result is None:
                    task_device_name = task_data.get('device_name', 'Unknown Device in Task')
                    self.logger.warning(f"Task for {task_device_name} failed completely")
                    
            except Exception as e:
                task_device_name = task_data.get('device_name', 'Unknown Device in Task')
                self.logger.error(f"Task execution error for {task_device_name}: {str(e)}")
                results.append(None)
                
        return results

    async def orchestrator(self):
        """Main orchestration loop for processing user commands."""
        while True:
            try:
                user_query, task_to_perform, start_time = await self.task_by_user()
                
                if task_to_perform == "STOP":
                    self.logger.info("Received exit command, shutting down")
                    break
                    
                if task_to_perform == "ERROR":
                    self.logger.error("Could not classify the user query, please try again")
                    print("Sorry, I couldn't understand your request. Please try again.")
                    continue
                
                try:
                    if isinstance(task_to_perform.message.content, str):
                        task_content = task_to_perform.message.content
                        task_to_perform = await self.parse_json_response(task_content)
                    else:
                        self.logger.error("Unexpected response format from classification")
                        continue
                except Exception as e:
                    self.logger.error(f"Failed to parse classification response: {str(e)}")
                    print("Sorry, there was an issue processing your request. Please try again.")
                    continue
                
                concurrent_tasks = task_to_perform.get("tasks", {}).get("concurrent", [])
                sequential_tasks = task_to_perform.get("tasks", {}).get("sequential", [])
                
                semaphore = asyncio.Semaphore(self.max_concurrency)
                
                if concurrent_tasks:
                    self.logger.info(f"Executing {len(concurrent_tasks)} concurrent tasks")
                    await self.execute_tasks(concurrent_tasks, user_query, semaphore)
                
                if sequential_tasks:
                    self.logger.info(f"Executing {len(sequential_tasks)} sequential tasks")
                    await self.execute_tasks(sequential_tasks, user_query)
                
                elapsed_time = time.time() - start_time
                self.logger.info(f"Total execution time: {elapsed_time:.2f} seconds")
                
            except Exception as e:
                self.logger.error(f"Error in orchestrator: {str(e)}")
                print("Sorry, an error occurred. Please try again.")


if __name__ == "__main__":
    agent_obj = ASYNC_HOME_AGENT()
    asyncio.run(agent_obj.orchestrator())