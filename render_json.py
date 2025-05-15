import json
import re

TEMPLATE_PATH = "tempconfig.json"
OUTPUT_PATH = "group_config.json"

def load_template(file_path):
    print(f"📥 Loading template from: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_output(data, file_path):
    print(f"💾 Saving final config to: {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def find_placeholders(obj, found=None):
    if found is None:
        found = set()
    if isinstance(obj, dict):
        for value in obj.values():
            find_placeholders(value, found)
    elif isinstance(obj, list):
        for item in obj:
            find_placeholders(item, found)
    elif isinstance(obj, str):
        found.update(re.findall(r"\{\{(.*?)\}\}", obj))
    return found

def prompt_placeholders(placeholders):
    print("\n🛠️  Please provide values for the following placeholders:\n")
    values = {}
    for key in placeholders:
        user_input = input(f"{key}: ").strip()
        values[f"{{{{{key}}}}}"] = user_input
    return values

def replace_placeholders(obj, mapping):
    if isinstance(obj, dict):
        return {k: replace_placeholders(v, mapping) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_placeholders(item, mapping) for item in obj]
    elif isinstance(obj, str):
        for placeholder, value in mapping.items():
            obj = obj.replace(placeholder, value)
        return obj
    else:
        return obj

def main():
    try:
        template = load_template(TEMPLATE_PATH)
        placeholders = find_placeholders(template)
        if not placeholders:
            print("⚠️  No placeholders found in the template.")
            return
        print(f"🔍 Found placeholders: {', '.join(placeholders)}")
        user_inputs = prompt_placeholders(placeholders)
        result = replace_placeholders(template, user_inputs)
        save_output(result, OUTPUT_PATH)
        print("\n✅ Done! Your config is ready in 'config.json'")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
