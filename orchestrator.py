import json
import os
import google.generativeai as genai

# 1. Setup AI credentials from environment variables
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def load_file(filepath):
    """Helper function to read local files."""
    with open(filepath, 'r') as file:
        return file.read()

def generate_challenger_ad():
    print("Wake up Artie. Assembling data...")

    # 2. Read the core files
    try:
        template_data = load_file("template.json")
        baseline_rules = load_file("baseline.md")
        system_instructions = load_file("program.md")
    except FileNotFoundError as e:
        print(f"Error: Missing a core file. {e}")
        return

    # 3. Stitch them together into the final prompt
    full_prompt = f"""
    {system_instructions}

    --- BASELINE RULES ---
    {baseline_rules}

    --- CURRENT CHAMPION AD (JSON) ---
    {template_data}
    """

    print("Data assembled. Sending to the AI Brain...")

    # 4. Call the AI model
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Force the AI to return ONLY a JSON object
    response = model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json",
        )
    )

    # 5. Process and validate the AI's response
    try:
        challenger_ad = json.loads(response.text)

        # Validate required keys are present before saving
        required_keys = {"headline", "primary_text", "call_to_action", "image_hash"}
        if not required_keys.issubset(challenger_ad.keys()):
            print(f"Error: AI response is missing required keys. Got: {list(challenger_ad.keys())}")
            return

        # Validate character limits before saving
        if len(challenger_ad["headline"]) > 40:
            print(f"Error: AI-generated headline exceeds 40 characters ({len(challenger_ad['headline'])} chars). Retrying recommended.")
            return

        if len(challenger_ad["primary_text"]) > 125:
            print(f"Error: AI-generated primary_text exceeds 125 characters ({len(challenger_ad['primary_text'])} chars). Retrying recommended.")
            return

        # Save the validated challenger ad
        with open("challenger.json", "w") as outfile:
            json.dump(challenger_ad, outfile, indent=2)

        print("Success! Challenger Ad created and saved as challenger.json.")
        print(f"  Headline ({len(challenger_ad['headline'])} chars): {challenger_ad['headline']}")
        print(f"  Primary Text ({len(challenger_ad['primary_text'])} chars): {challenger_ad['primary_text']}")

    except json.JSONDecodeError:
        print("Error: The AI did not return a valid JSON format. Retrying recommended.")

# Run the script
if __name__ == "__main__":
    generate_challenger_ad()
