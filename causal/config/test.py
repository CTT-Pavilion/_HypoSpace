import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("Config:", config)
print("LLM type:", config.get('llm', {}).get('type'))
print("API keys:", config.get('llm', {}).get('api_keys'))
print("OpenRouter key:", config.get('llm', {}).get('api_keys', {}).get('openrouter'))