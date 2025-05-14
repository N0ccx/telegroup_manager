import argparse
import json
import asyncio
from group_main import create_group_wizard, format_description_from_community

def parse_args():
    parser = argparse.ArgumentParser(description="Create and moderate a Telegram group via CLI")
    parser.add_argument('--config', type=str, required=True, help='Path to config JSON file')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    with open(args.config, 'r') as f:
        full_config = json.load(f)

    if "group_config" in full_config:
        config = full_config["group_config"]
    else:
        raise ValueError("Missing 'group_config' section in JSON.")

    if "community" in full_config:
            community = full_config["community"]
            description = format_description_from_community(community)
            config["group_description"] = description

    
    required_keys = [
        "group_title", "group_description", "photo_path",
        "user_usernames", "public_username_base", "welcome_message"
    ]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")

    asyncio.run(create_group_wizard(**config))
