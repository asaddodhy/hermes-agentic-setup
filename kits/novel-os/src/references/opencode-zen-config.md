# OpenCode Zen Provider Configuration for Novel-OS

## Working configuration

Add these lines to `/Users/dodhya/novel-os/.env`:

```
NOVEL_OS_LLM_PROVIDER=openai_compatible
NOVEL_OS_BASE_URL=https://opencode.ai/zen/v1
NOVEL_OS_API_KEY=<your-key-here>
NOVEL_OS_MODEL=deepseek-v4-flash-free
NOVEL_OS_MAX_TOKENS=8192
```

## Key sourcing

**Do NOT rely on Hermes credential pool injection.** Novel-OS reads `.env` via `python-dotenv` or its own minimal parser — it's a subprocess that does NOT have access to Hermes-injected environment variables. You must write the key directly into the `.env` file.

## Connection test

```bash
cd /Users/dodhya/novel-os && source .venv/bin/activate
python -c "
from core.llm_client import LLMClient
client = LLMClient()
reply = client.complete(system='Reply with OK.', user='Single word:')
print(reply.strip())
"
```

Expected output: `OK`

## Available models (free tier)

- `deepseek-v4-flash-free` — good default, fast inference
- Check https://opencode.ai for current free model list

## OpenCode Go (subscription alternative)

Base URL: `https://opencode.ai/zen/go/v1`
$10/month subscription. Access to open models (GLM-5, Kimi K2.5, MiniMax M2.5, etc.).
Same `openai_compatible` provider, just change the base URL.
