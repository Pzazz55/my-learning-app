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

## Project structure

| Path | Purpose |
| --- | --- |
| `learning-home.py` | Student entry point — setup form, timed exam, celebration screen |
| `pages/parent-results.py` | Parent Results page (sign-in, filters, answer review, delete) |
| `llm_backend.py` | Config loading, subject/topic resolution, provider routing, question generation |
| `config/` | `config.json`, `locations.json`, `topics.json`, `models.json` |
| `requirements.txt` | Runtime dependencies installed by Streamlit Community Cloud |
| `_verify_changes.py` | End-to-end check driven by `streamlit.testing.v1.AppTest` |
| `.streamlit/secrets.toml.example` | Template for the secrets to paste into Community Cloud |

## Deploy to Streamlit Community Cloud

There is no build step: Community Cloud installs `requirements.txt` and runs the main file straight from GitHub.

1. Push the repository to GitHub.
2. Open <https://share.streamlit.io> and click **Create app** → **Yup, I have an app**.
3. Fill in the app details:

   | Field | Value |
   | --- | --- |
   | Repository | `<your-account>/my-learning-app` |
   | Branch | `master` |
   | Main file path | `learning-home.py` |

4. Click **Advanced settings**, set **Python version** to `3.12`, and paste your secrets into the **Secrets** box. Start from `.streamlit/secrets.toml.example`:

   ```toml
   GROQ_API_KEY = "..."
   OPENROUTER_API_KEY = "..."
   PARENT_USERNAME = "parent"
   PARENT_PASSWORD = "change-this-password"
   ```

   Streamlit exposes every root-level key through `st.secrets` **and** as an environment variable, and the app reads both, so the deployed names are identical to the local `.env` names.

5. Click **Deploy**. Most apps go live within a few minutes, and later pushes to `master` update it automatically. Changing `requirements.txt` triggers a full rebuild.

Points to keep in mind once deployed:

- **At least one provider key is required.** The sidebar lists only the models in `config/models.json` whose key is available, and the app stops with an explanatory message when none is.
- **`PARENT_USERNAME` and `PARENT_PASSWORD` are required** to open Parent Results; the page says so instead of failing silently.
- **Never commit `.env` or `.streamlit/secrets.toml`** — both are already excluded by `.gitignore`.
- Secrets can be edited later from the app's **Settings → Secrets** in your workspace.

### Data persistence on Community Cloud

`education_app.db` is written inside the app container. Community Cloud hibernates an app after 12 hours without traffic and rebuilds the container when you reboot or redeploy it, so saved results live only for the current container lifetime — they are **not** a permanent archive. Use the local install when the results history must be kept long term, or move storage to an external database before treating the hosted app as the system of record.

## LLM questions

Set `HF_TOKEN` before starting Streamlit to use the Hugging Face inference API with `google/flan-t5-base`. The app validates that the requested questions are unique, stores the generated set in SQLite before showing the first question, and links it to the completed result:

Runtime variables and provider keys are stored in the local `.env` file:

```env
HF_TOKEN=your-token
GROQ_API_KEY=your-groq-key
PARENT_USERNAME=parent
PARENT_PASSWORD=change-this-password
GOOGLE_API_KEY=your-google-key
OPENAI_API_KEY=your-openai-key
OPENROUTER_API_KEY=your-openrouter-key
```

The same names work in `.streamlit/secrets.toml` locally and in the **Secrets** box on Streamlit Community Cloud. The `.env` file is excluded from Git.

## Configuration directory (`config/`)

All application settings, location hierarchies, topics, and model provider configurations are organized in the `config/` folder:

- **`config/config.json`**: Timezone and initial setup page defaults.
- **`config/locations.json`**: Country, State, and School District hierarchy.
- **`config/models.json`**: Supported LLM model providers and API key environment variable mappings.
- **`config/topics.json`**: School-specific topic overrides and default grade/subject topics.

## Model configuration

Edit `config/models.json` to control which providers appear in the sidebar. Each enabled entry specifies its provider, provider model ID, and the environment variable containing its key. Supported providers are `google`, `openai`, `openrouter`, `groq`, and `huggingface`. Models are shown only when `enabled` is true and the configured API key exists. Disable a model with `"enabled": false` without changing Python code.

The selected model is routed through the matching provider automatically. An exam cannot start unless the selected model's configured API key is available.

## Location configuration

`config/locations.json` drives the **Country**, **State**, and **School District** dropdowns on the setup page using a hierarchical structure:

```json
{
  "United States": {
    "North Carolina": [
      "Charlotte-Mecklenburg Schools",
      "Wake County Public School System"
    ]
  },
  "Canada": {
    "Ontario": ["Toronto District School Board", "Peel District School Board"]
  },
  "Other": {}
}
```

- **Countries**: Top-level keys define the available countries in the dropdown.
- **States / Provinces**: Selecting a country dynamically populates the State dropdown with its associated states.
- **School Districts**: Selecting a state dynamically populates the School District dropdown with its associated school districts.
- **Countries without states**: If a country has no states configured (e.g. `"Other": {}`), the State and District fields are hidden automatically.

## Subject and topic configuration

`config/topics.json` drives the **Subject** and **Topic** dropdowns and the Parent Results filters. It is organized into school-specific overrides and explicit defaults:

```json
{
  "schools": {
    "Charlotte-Mecklenburg Schools": {
      "Grade 3": { "Maths": ["Place Value to 10,000", "Perimeter & Area"] }
    }
  },
  "default": {
    "Grade 1": { "Maths": ["Counting & Writing Numbers", "Addition within 20"] },
    "Grade 2": { "Maths": ["Place Value to 1000", "Telling Time"] },
    "General Knowledge": ["Geography", "History", "Current Affairs"],
    "Others": []
  }
}
```

Topics are resolved most-specific-first from the School → Grade → Subject selection:

1. `schools` → the chosen **School District** (e.g. `Charlotte-Mecklenburg Schools`) → `"Grade N"` → subject
2. `default` → `"Grade N"` → subject (used when a grade/subject is not defined in the school, or for schools outside the configured districts)
3. `default` → subject (used by subjects such as **General Knowledge** that do not vary by grade)

- The order of keys and topics in the file is the order shown in the app.
- A subject with no matching list (for example `Others`, which is deliberately empty) falls back to a free-text **Topic** box, so custom subjects keep working.
- When values are missing in `"Charlotte-Mecklenburg Schools"`, the app automatically falls back to `default`.
- Schools outside `"Charlotte-Mecklenburg Schools"` automatically take `default` values.
- A missing `config/topics.json` leaves the built-in subject list with free-text topics, while an unknown section name raises a clear error instead of being silently ignored.

Because the Topic list depends on the school and the grade, **School District** and **Grade** are placed above **Subject** and **Topic** on the setup page.

The selected topic is saved with the exam, focuses the generated questions, and is used to revisit the student's earlier mistakes in that same topic.

## Application configuration

`config/config.json` sets the display timezone and the starting value of every field on the setup page:

```json
{
  "timezone": "America/New_York",
  "timezone_label": "Eastern Time",
  "defaults": {
    "country": "United States",
    "state": "North Carolina",
    "school_district": "Charlotte-Mecklenburg Schools",
    "grade": "Grade 1",
    "subject": "Maths",
    "topic": "",
    "question_count": 5,
    "time_limit": 10,
    "include_images": false,
    "practice_mode": false,
    "appearance": "Dark"
  }
}
```

- `timezone` accepts any IANA name, for example `America/New_York` (EST/EDT), `Europe/London` (GMT/BST) or `Asia/Kolkata` (IST). The clock in every student screen header and the `Completed` timestamps in Parent Results are shown in this zone, and the zone abbreviation follows that region's own daylight saving rules.
- `timezone_label` is the caption shown under the clock.
- `defaults` pre-selects the Country, State, School District, Grade, Subject, Topic, question count, time limit, both toggles and the appearance theme. `"topic": ""` means the first topic in the resolved list, and `time_limit` is clamped to 1–180 minutes.
- Anything unusable never breaks the app: unknown keys, an unknown timezone or a wrong value type are reported as a warning in the sidebar and the built-in default is used instead.
- `tzdata` supplies the IANA database on Windows and is listed in both `requirements.txt` and `pyproject.toml`.

## Parent results login

The Parent Results page requires a login. Credentials are stored in `.env` using `PARENT_USERNAME` and `PARENT_PASSWORD`.

Authenticated parents can delete saved tests after confirming the deletion.

Each saved test expands into a metric row (grade, score, correct, wrong, question count and overall time) plus an answer review table. The review table lists every question with its `A)`–`D)` options next to the student's answer, the correct answer, the time taken and the status, so a parent can see exactly what was asked.

The filter row covers student name, grade, subject and topic. The topic choices come from the saved results that match the other three filters, so a topic filter can never select something with no results.
