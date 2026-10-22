# Hindi script package generator setup

This is the first optional live-AI step in the cinematic pipeline. It creates a Hindi
script and scene-prompt JSON package. It does **not** perform web research, generate
images/video/audio, render the final video, or upload to YouTube.

## Requirements

- Python 3.10+
- An account with an OpenAI-compatible chat-completions API provider
- A model that supports JSON-object responses
- HTTPS API base URL and an API key

The API provider may charge for requests. Check its current pricing and model support
before running this command. The repository does not choose a provider or create an API
key for you.

## Configure environment variables

Set these in your own terminal or secret manager. Do not commit them to GitHub, paste
them into issues/PR comments, or put them directly in command-line arguments.

- `CINEMATIC_LLM_BASE_URL`: provider's documented HTTPS base URL (not the secret key)
- `CINEMATIC_LLM_API_KEY`: API key
- `CINEMATIC_LLM_MODEL`: model identifier available to your account

Example for a local shell (replace the values with the provider's documented values):

```bash
export CINEMATIC_LLM_BASE_URL="https://YOUR-PROVIDER-API-BASE"
export CINEMATIC_LLM_API_KEY="set-this-in-your-local-shell"
export CINEMATIC_LLM_MODEL="YOUR-AVAILABLE-MODEL"
python scripts/generate_hindi_script_package.py \
  --topic "प्राचीन भारत के रहस्य" \
  --target-minutes 9 \
  --output-dir dist-cinematic
```

Do not run the placeholder values as-is. The URL is expected to expose a compatible
`/chat/completions` endpoint. The generator makes a request only when explicitly run.

## Outputs

- `script-package.json`: title, description, narration, scene plan and review flags
- `script-hi.txt`: Hindi narration draft
- `scene-prompts.json`: scene prompts for the existing asset-generation adapter

Generated facts are not independently verified by this step. Fact-check the script
against reliable sources before recording or publishing it. Review generated prompts
and output files before proceeding to paid image/video generation.

## Privacy and upload safety

- Do not store API keys in source files, workflow YAML, config JSON, or logs.
- This script does not upload to YouTube.
- Public publishing remains disabled in the project workflow.
- The intended eventual YouTube upload mode is Private, subject to owner review.
