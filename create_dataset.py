import json
import logging
import pandas as pd
import asyncio
from utils.utils import UTILS

import random
import utils.agent_prompts as agent_prompts 


class CREATE_DATASET:
    def __init__(self):
        with open(r"utils\config.json") as f:
            self.default_config = json.load(f)
        f.close()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        # In create_dataset.py __init__
        self.llm_provider = self.default_config.get("llm_provider", "gemini")
        self.llm_model = self.default_config.get("llm_model", "gemini-2.0-flash") # Provide a sensible default
        # No need to pass api_key here if using environment variables
        self.utils_obj = UTILS(provider=self.llm_provider, model_name=self.llm_model)
        self.device_functions_dict = self.default_config["device_functions_dict"]
        self.current_device = None  # Track current device for context-aware value generation

    def generate_random_value(self, arg_name):
        """Generate random values based on argument name, covering all subtypes and ranges from config.json."""
        # General on/off, status, state
        if arg_name == "status": # TV, AC, Fridge, DoorAlarm, ChildLock, DisplayLight, BeepSound, Swing
            return random.choice(["on", "off"])
        elif arg_name == "state":  # Fan power
            return random.choice(["on", "off"])

        # Device specific arguments
        if self.current_device == "microwave":
            if arg_name == "temp":
                return random.randrange(180, 221, 10)
            elif arg_name == "time":
                return random.randint(1, 61) * 0.5 # 0.5 to 30.5 minutes
            elif arg_name == "watts":
                return random.choice([100, 200, 400, 600, 800, 1000])

        elif self.current_device == "tv":
            if arg_name == "level": # Volume
                return random.randint(0, 100)
            elif arg_name == "appName":
                return random.choice(["Netflix", "YouTube", "Prime", "Disney+", "Hotstar", "Spotify"])
            elif arg_name == "menu":
                return random.choice(["picture", "sound", "network", "system"])
            elif arg_name == "source":
                return random.choice(["HDMI1", "HDMI2", "AV", "TV", "USB"])
            elif arg_name == "input": # Search query
                return random.choice(["latest movies", "breaking news", "live sports", "local weather", "open Netflix", "search YouTube for cat videos"])
            elif arg_name == "action": # Playback
                return random.choice(["play", "pause", "stop", "rewind", "fastForward"])
            elif arg_name == "direction": # Navigation, Volume/Channel
                return random.choice(["up", "down", "left", "right", "select", "back", "home"])
            elif arg_name == "duration": # Record
                return random.randint(1, 180) # minutes
            elif arg_name == "number": # Channel
                return random.randint(1, 999)

        elif self.current_device == "washer":
            if arg_name == "soil_level":
                return random.choice(["heavy", "normal", "light"])
            elif arg_name == "load_size":
                # Prompt allows number or small/medium/large. Generate both types.
                if random.choice([True, False]):
                    return random.randint(1, 12) # lbs
                else:
                    return random.choice(["small", "medium", "large"])
            elif arg_name == "load_type": # For Normal mode
                return random.choice(["regular", "mixed", "whites", "colors"])
            elif arg_name == "fabric_type":
                # Delicates, PermPress modes
                return random.choice(["cotton", "synthetic", "wool", "performance", "wrinklefree", "delicate"])
            elif arg_name == "item_type": # Bedding mode
                return random.choice(["bedding", "towel", "shirt", "jeans", "blanket"])
            elif arg_name == "bleach_option": # SteamWhites mode
                return random.choice(["yes", "no"])
            elif arg_name == "color_shade": # Denim mode
                return random.choice(["light", "dark", "medium"])
            elif arg_name == "colorfast": # SteamSanitize mode
                return random.choice([True, False])

        elif self.current_device == "dryer":
            if arg_name == "fabric_type":
                # Normal, HeavyDuty, SuperSpeed, Wool, PermPress modes
                return random.choice(["cotton", "wool", "synthetic", "wrinklefree", "delicate"])
            elif arg_name == "load_status": # SteamSanitize, SteamRefresh modes
                return random.choice(["wet", "partial_wet", "dry"])
            elif arg_name == "duration": # TimeDry, WrinkleAway modes
                return random.randint(10, 120) # minutes
            elif arg_name == "item_count": # WrinkleAway, SteamRefresh modes
                return random.randint(1, 10) # Realistic number of items
            elif arg_name == "machine_washable": # Wool mode
                return random.choice([True, False])

        elif self.current_device == "ac":
            if arg_name == "temperature":
                return random.randint(16, 30)
            elif arg_name == "duration": # Timer mode
                return random.randint(1, 24) # hours
            elif arg_name == "speed": # FanSpeed mode
                return random.choice(["low", "medium", "high", "auto"])
            # status handled generically above

        elif self.current_device == "fridge":
            if arg_name == "temperature":
                return random.randint(-4, 24)
            elif arg_name == "duration": # ConvertFreezerToFridge, EnergySavingMode, Deodorize modes
                return random.randint(1, 48) # hours (Allowing up to 2 days for some modes)
            elif arg_name == "level": # DisplayBrightness mode
                return random.randint(1, 5)
            # status handled generically above

        elif self.current_device == "fan":
            if arg_name == "action": # Speed mode
                return random.choice(["up", "down", "increase by", "decrease by"])
            elif arg_name == "level": # Speed mode (for increase/decrease by)
                return random.randint(1, 5) # Assuming a smaller range for fans
            # state handled generically above

        else: # Fallback for unhandled/generic or error case
            self.logger.warning(f"Unhandled argument name: {arg_name} for device {self.current_device} or device context missing.")
            # Return a plausible generic value if possible, otherwise None
            if arg_name in ["level", "number", "count", "duration", "temperature"]:
                return random.randint(1, 10)
            elif arg_name in ["speed", "mode", "setting"]:
                return random.choice(["auto", "medium", "default"])
            elif isinstance(arg_name, str): # Catch-all for string types
                 return random.choice(["default_value", "option1", "settingA"])
            return None

    def randomize_devices(self):
        # Get list of available devices
        list_of_devices = list(self.device_functions_dict.keys())

        # Randomly select number of devices (1-5)
        num_devices = random.randint(1, min(5, len(list_of_devices)))

        result = {"selections": []}

        # Select random devices
        chosen_devices = random.sample(list_of_devices, num_devices)

        for device in chosen_devices:
            # Set current device for context-aware value generation
            self.current_device = device
            
            # Get list of modes for this device
            modes = self.device_functions_dict[device]

            # Select random mode
            mode_info = random.choice(modes)

            # Extract mode name and args
            mode_name = mode_info["mode"]

            # Handle args based on mode structure
            args = None
            if "args" in mode_info and mode_info["args"]:
                args = {}

                # --- Special handling blocks remain, adjusted to use generate_random_value --- 
                if device == "fan" and mode_name == "speed":
                    # Fan speed needs action and possibly level based on config ["action", "level"]
                    action = random.choice(["up", "down", "increase by", "decrease by"])
                    args["action"] = action
                    if action in ["increase by", "decrease by"]:
                        # Use generate_random_value for level
                        args["level"] = self.generate_random_value('level') 

                elif device == "tv" and mode_name == "volume":
                    # TV volume needs direction and level based on config ["direction", "level"]
                    # Generate direction specific to volume contexts
                    direction = random.choice(["up", "down", "increase by", "decrease by", "mute", "unmute"])
                    args["direction"] = direction
                    if direction not in ["mute", "unmute"]:
                         # Use generate_random_value for level
                        args["level"] = self.generate_random_value('level')

                elif device == "tv" and mode_name == "channel":
                     # TV channel can be up/down or specific number based on config ["direction", "number"]
                    if random.choice([True, False]):
                        # Generate direction specific to channel contexts
                        args["direction"] = random.choice(["up", "down"])
                    else:
                        args["number"] = self.generate_random_value('number')

                elif device == "tv" and mode_name == "navigate":
                    # TV navigation direction based on config ["direction"]
                    # Generate direction specific to navigation contexts
                    args["direction"] = random.choice(["up", "down", "left", "right", "select", "back", "home"])

                # --- Generic Handling Block --- 
                else:
                    # Process each argument name listed in the config for this mode
                    for arg_name in mode_info["args"]:
                        if isinstance(arg_name, str):
                             # Generate value using the centralized function
                             args[arg_name] = self.generate_random_value(arg_name)
                        else:
                            self.logger.warning(f"Unexpected arg format in config for {device}/{mode_name}: {arg_name}. Expected string.")

            selection = {"device": device, "mode": mode_name, "args": args}
            result["selections"].append(selection)

        return result

    async def create_dataset_row(self):
        """
        Generate dataset prompts based on device selections and save to CSV.

        Args:
           selections: Dictionary containing device selections from randomize_devices()
           agent_prompts: Module containing the DATASET_ROW_CREATION_PROMPT
           output_file: Path to save the CSV file
        """
        selections = self.randomize_devices()

        result = {"generated_query": "", "device_info": [], "language":""}

        language = random.sample(
            [
                "Hindi (Devanagari)",
                "Bengali (Bangla)",
                "Marathi (Devanagari)",
                "Telugu (Telugu Script)",
                "Tamil (Tamil Script)",
                "Gujarati (Gujarati Script)",
                "Urdu (Nastaliq)",
                "Kannada (Kannada Script)",
                "Malayalam (Malayalam Script)",
                "Punjabi (Gurmukhi)",
                "Romanised Hindi (Latin)",
                "Romanised Bengali (Latin)",
                "Romanised Marathi (Latin)",
                "Romanised Telugu (Latin)",
                "Romanised Tamil (Latin)",
                "Romanised Gujarati (Latin)",
                "Romanised Urdu (Latin)",
                "Romanised Kannada (Latin)",
                "Romanised Malayalam (Latin)",
                "Romanised Punjabi (Latin)",
                "English (Latin)"
            ], 
            k=1
        )[0]  # Extract the string from the list
        
        num_devices = len(selections["selections"])

        # Only allow 'Sequential and Concurrent' if more than 1 device
        if num_devices == 1:
            task_types = ["Sequential", "Concurrent"]
            task_weights = [1, 1]
        else:
            task_types = ["Sequential", "Concurrent", "Sequential and Concurrent"]
            task_weights = [1, 1, 8]
        task_style = random.choices(task_types, weights=task_weights, k=1)[0]
        
        # Add vagueness parameter
        vagueness = random.choices([True, False], weights=[0.7, 0.3], k=1)[0]

        # Assign execution_type to each device
        devices = selections["selections"]
        if task_style == "Sequential and Concurrent" and num_devices > 1:
            # Randomly split devices into sequential and concurrent groups
            split_point = random.randint(1, num_devices - 1)
            indices = list(range(num_devices))
            random.shuffle(indices)
            seq_indices = set(indices[:split_point])
            for i, device in enumerate(devices):
                if i in seq_indices:
                    device["execution_type"] = "sequential"
                else:
                    device["execution_type"] = "concurrent"
        else:
            exec_type = task_style.lower()
            for device in devices:
                device["execution_type"] = exec_type

        details = {
            "language": language,
            "task_type": task_style,
            "device_count": num_devices,
            "devices": devices,
            "vagueness": vagueness
        }

        formatted_prompt = agent_prompts.DATASET_CREATION_PROMPT.format(details=details).replace("{{", "{").replace("}}", "}")
        message = self.utils_obj.create_message(role="user", content=formatted_prompt)

        response = await self.utils_obj.chat([message])
        self.logger.info(response)
        try:
            if self.llm_provider == "gemini":
                generated_query = json.loads(response["message"]["content"])
            else:
                generated_query = json.loads(response.message.content)
        except Exception as e:
            if self.llm_provider == "gemini":
                generated_query = json.loads(
                    response["message"]["content"].replace("```json", "").replace("```", "")
                )
            else:
                generated_query = json.loads(
                    response.message.content.replace("```json", "").replace("```", "")
                )
            self.logger.warning(f"Error Occurred: {e}")
        result["generated_query"] = generated_query["generated_query"].replace("\"", "")
        result['language'] = language
        
        # Add task_type, vagueness, and execution_type to each device info
        for device in devices:
            device["task_type"] = task_style
            device["explicitly_mentioned"] = not vagueness
            result["device_info"].append(device)

        return result

    async def create_dataset(self, output_file="dataset.csv"):
        semaphore = asyncio.Semaphore(self.default_config["max_concurrency"])
        rows_of_dataset = []
        for _ in range(self.default_config["num_of_data_points"]):
            async with semaphore:
                row_dataset = asyncio.create_task(self.create_dataset_row())
                rows_of_dataset.append(row_dataset)
        dataset = await asyncio.gather(*rows_of_dataset)
        df = pd.DataFrame(dataset)
        df.to_csv(output_file, index=False)


dataset_creation = CREATE_DATASET()

asyncio.run(dataset_creation.create_dataset())
