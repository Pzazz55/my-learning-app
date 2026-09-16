# Study Sprint

A Streamlit education app for grade-aware multiple-choice exams, timed student sessions, local result storage, and parent review.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run learning-home.py
```

The app uses SQLite in `education_app.db`, created automatically on first run. Open **Parent Results** from the Streamlit page navigation to review completed exams.

## LLM questions

Set `HF_TOKEN` before starting Streamlit to use the Hugging Face inference API with `google/flan-t5-base`. The app validates that the requested questions are unique, stores the generated set in SQLite before showing the first question, and links it to the completed result:

Runtime variables and provider keys are stored in the local `.env` file:

```env
HF_TOKEN=your-token
PARENT_USERNAME=parent
PARENT_PASSWORD=change-this-password
GOOGLE_API_KEY=your-google-key
OPENAI_API_KEY=your-openai-key
OPENROUTER_API_KEY=your-openrouter-key
```

The `.env` file is excluded from Git.

## Model configuration

Edit `models.json` to control which providers appear in the sidebar. Each enabled entry specifies its provider, provider model ID, and the environment variable containing its key. Supported providers are `google`, `openai`, `openrouter`, `groq`, and `huggingface`. Models are shown only when `enabled` is true and the configured API key exists. Disable a model with `"enabled": false` without changing Python code.

The selected model is routed through the matching provider automatically. An exam cannot start unless the selected model's configured API key is available.

## Parent results login

The Parent Results page requires a login. Credentials are stored in `.env` using `PARENT_USERNAME` and `PARENT_PASSWORD`.

Authenticated parents can delete saved tests after confirming the deletion.
