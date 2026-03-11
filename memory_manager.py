import os
import re
import json
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def update_long_term_memory():
    print("Artie is doing his weekly review...")

    # 1. Read the full experiment log
    try:
        with open("experiment_log.json", "r") as file:
            all_data = file.read()
    except FileNotFoundError:
        print("Error: experiment_log.json not found. Run some experiments first.")
        return

    # Guard: Don't run the analysis on an empty log
    logs = json.loads(all_data)
    if len(logs) == 0:
        print("No experiments in the log yet. Nothing to analyze.")
        return

    # 2. Ask the AI to identify patterns from all past experiments
    analyst_prompt = f"""
    You are an elite Performance Marketing Analyst. Review these past ad experiments:
    {all_data}

    Identify the 3 most important headline or copy patterns that consistently produced a high ROAS.
    Output ONLY 3 concise bullet points. No intro, no outro, no extra commentary.
    """

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(analyst_prompt)
    new_insights = response.text.strip()

    # 3. Read the current baseline.md content
    with open("baseline.md", "r") as file:
        current_content = file.read()

    # FIX: Remove any previously written AI insights section before appending
    # This prevents duplicate sections accumulating on every run
    current_content = re.sub(
        r"\n\n## 4\. AI-Discovered Insights.*",
        "",
        current_content,
        flags=re.DOTALL
    ).rstrip()

    # 4. Write the cleaned content + fresh insights back to baseline.md
    with open("baseline.md", "w") as file:
        file.write(current_content)
        file.write("\n\n## 4. AI-Discovered Insights (Long-Term Memory)\n")
        file.write(f"*Last updated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        file.write(new_insights)
        file.write("\n")

    print("baseline.md has been updated with the latest AI insights.")
    print("Insights written:")
    print(new_insights)

if __name__ == "__main__":
    update_long_term_memory()
