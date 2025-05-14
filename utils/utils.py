# utils.py
import logging
import os 
import utils.agent_prompts as agent_prompts
from ollama import AsyncClient
import google.generativeai as genai # Added for Gemini

from dotenv import load_dotenv

load_dotenv()

class UTILS:
    def __init__(self, provider='ollama', model_name='qwen2.5:32b', api_key=None):
        """
        Initializes the UTILS class with a specified LLM provider and model.

        Args:
            provider (str): The LLM provider to use ('ollama' or 'gemini'). Defaults to 'ollama'.
            model_name (str): The specific model name to use. Defaults to 'gemma2' for Ollama.
                                For Gemini, examples include 'gemini-pro'.
            api_key (str, optional): The API key required for the provider (e.g., Gemini).
                                     Defaults to None. It's recommended to use environment variables.
        """
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = api_key
        self.is_gemini_configured = False
        
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.is_gemini_configured = True
        else:
            # Handle the case where the API key is not found
            # You might want to log a warning or raise an error depending on your needs
            print("Warning: GEMINI_API_KEY environment variable not set. Gemini provider will not work.")

        # Provider-specific setup (example for Gemini if key is passed directly)
        # Note: Using environment variable configuration above is preferred.
        if self.provider == 'gemini' and self.api_key and not self.is_gemini_configured:
             self.logger.warning("API key passed directly to UTILS, but using environment variable is recommended.")
             genai.configure(api_key=self.api_key)
             self.is_gemini_configured = True
        elif self.provider == 'gemini' and not self.is_gemini_configured:
             self.logger.error("Gemini provider selected, but API key is not configured (checked env var and direct param).")
             # Optionally raise an error or prevent Gemini usage


    async def chat(self, messages):
        """
        Sends a chat message list to the configured LLM provider.

        Args:
            messages (list): A list of message dictionaries, e.g., [{'role': 'user', 'content': 'Hello'}]

        Returns:
            The response object from the LLM provider, or None if an error occurs.
        """
        try:
            if self.provider == 'ollama':
                response = await AsyncClient().chat(model=self.model_name, messages=messages)
                return response
            elif self.provider == 'gemini':
                if not self.is_gemini_configured:
                     self.logger.error("Cannot use Gemini provider: API key not configured.")
                     return None
                
                # Filter out system messages for Gemini
                filtered_messages = [msg for msg in messages if msg['role'] != 'system']
                if len(filtered_messages) < len(messages):
                    self.logger.warning("System messages were removed as Gemini doesn't support them")
                
                generation_config = genai.types.GenerationConfig(
                    temperature=0.9
                )
                model = genai.GenerativeModel(self.model_name)
                
                history = []
                for msg in filtered_messages[:-1]:
                    history.append({'role': msg['role'] if msg['role'] != 'assistant' else 'model', 'parts': [msg['content']]})

                last_message_content = filtered_messages[-1]['content']

                chat_session = model.start_chat(history=history)
                response = await chat_session.send_message_async(last_message_content, generation_config=generation_config)

                return {'message': {'content': response.text, 'role': 'assistant'}}
            else:
                self.logger.error(f"Unsupported LLM provider: {self.provider}")
                return None
        except Exception as e:
            self.logger.error(f"Error during chat with {self.provider} ({self.model_name}): {e}")
            return None

    def create_message(self, role, content):
        """Creates a message dictionary, ensuring the role is valid."""
        # Roles supported by Ollama; Gemini uses 'user' and 'model'
        # We might need to map roles in the chat function based on the provider
        valid_roles = ["user", "assistant", "system"] # Removed 'tool' as it's less standard across models
        if role not in valid_roles:
            self.logger.warning(f"Role '{role}' might not be standard. Using '{role}'.")
            # Keep the role for now, handle mapping in chat() if necessary
            # role = "user" # Or default to user
        return {"role": role, "content": content}

    def query_by_device(self, device_name):
        device_name = device_name.lower()
        if device_name == "microwave":
            return agent_prompts.MICROWAVE_PROMPT
        elif device_name == "washer":
            return agent_prompts.WASHER_PROMPT
        elif device_name == "dryer":
            return agent_prompts.DRYER_PROMPT
        elif device_name == "fridge":
            return agent_prompts.FRIDGE_PROMPT
        elif device_name == "tv":
            return agent_prompts.TV_PROMPT
        elif device_name == "ac":
            return agent_prompts.AC_PROMPT
        elif device_name == "fan":
            return agent_prompts.FAN_PROMPT
        else:
            return "This device cannot be controlled as of now. Kindly inform this to the user."