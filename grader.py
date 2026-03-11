import json
import os
import requests
from datetime import datetime, timezone

# 1. Load credentials from environment variables
ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
API_VERSION = "v19.0"

def fetch_ad_data(ad_id):
    """Pulls the age of the ad and its performance metrics from Meta."""
    print(f"Retrieving data for Ad ID: {ad_id}...")

    if not ACCESS_TOKEN:
        print("Error: META_ACCESS_TOKEN not set in environment.")
        return None

    # Get the creation time to calculate hours_active
    time_url = f"https://graph.facebook.com/{API_VERSION}/{ad_id}"
    time_response = requests.get(time_url, params={"access_token": ACCESS_TOKEN, "fields": "created_time"})
    time_data = time_response.json()

    if "created_time" not in time_data:
        print(f"Error fetching ad creation time: {time_data}")
        return None

    created_time = datetime.strptime(time_data["created_time"], "%Y-%m-%dT%H:%M:%S%z")
    hours_active = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600

    # Get performance stats
    insights_url = f"https://graph.facebook.com/{API_VERSION}/{ad_id}/insights"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "spend,impressions,clicks,action_values",
        "date_preset": "maximum"
    }

    response = requests.get(insights_url, params=params)
    data = response.json()

    # If no data yet, return a zero-baseline
    if "data" not in data or len(data["data"]) == 0:
        return {
            "spend": 0.0,
            "clicks": 0,
            "impressions": 0,
            "revenue": 0.0,
            "hours_active": hours_active
        }

    report = data["data"][0]

    # Extract revenue from purchase events
    revenue = 0.0
    if "action_values" in report:
        for action in report["action_values"]:
            if action["action_type"] == "omni_purchase":
                revenue = float(action["value"])

    return {
        "spend": float(report.get("spend", 0)),
        "clicks": int(report.get("clicks", 0)),
        "impressions": int(report.get("impressions", 0)),
        "revenue": revenue,
        "hours_active": hours_active
    }

def log_experiment(ad_id, ad_data, verdict):
    """Appends the grading result to the experiment log for long-term memory."""
    print("Writing result to the experiment log...")

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "ad_id": ad_id,
        "metrics": ad_data,
        "verdict": verdict
    }

    try:
        with open("experiment_log.json", "r") as file:
            logs = json.load(file)
    except FileNotFoundError:
        logs = []

    logs.append(log_entry)

    with open("experiment_log.json", "w") as file:
        json.dump(logs, file, indent=2)

    print(f"Logged: {verdict}")

def execute_action(ad_id, action):
    """Pauses losing ads or flags winning ads for scaling."""
    if action == "KILL":
        url = f"https://graph.facebook.com/{API_VERSION}/{ad_id}"
        requests.post(url, json={"access_token": ACCESS_TOKEN, "status": "PAUSED"})
        print(f"Executed: Ad {ad_id} has been PAUSED.")
    elif action == "SCALE":
        print(f"Executed: Ad {ad_id} is a WINNER. Flag for budget scaling.")

def grade_and_execute():
    # 1. Read the CHALLENGER ad ID (not the champion template)
    #    publisher.py saves the live ad ID back into challenger.json
    try:
        with open("challenger.json", "r") as file:
            challenger_data = json.load(file)
            ad_to_grade = challenger_data.get("ad_id")
    except FileNotFoundError:
        print("Error: challenger.json not found. Run publisher.py first.")
        return

    if not ad_to_grade:
        print("Error: No ad_id found in challenger.json. Was publisher.py run successfully?")
        return

    # 2. Fetch the report card
    ad_data = fetch_ad_data(ad_to_grade)
    if ad_data is None:
        return

    hours = ad_data["hours_active"]

    if hours < 6:
        print(f"Ad is only {hours:.1f} hours old. Too early to grade. Let it run.")
        return

    print(f"\n--- GRADING AD {ad_to_grade} (Active: {hours:.1f} Hours) ---")
    print(f"Spend: ${ad_data['spend']:.2f} | Revenue: ${ad_data['revenue']:.2f}")

    # 3. STAGE 1: 6-Hour Vibe Check — catch obvious losers early
    if 6 <= hours < 24:
        if ad_data["impressions"] == 0:
            print("No impressions yet. Check ad approval status in Ads Manager.")
            return

        ctr = (ad_data["clicks"] / ad_data["impressions"]) * 100

        # FIX: Use infinity when clicks=0 so the threshold comparison is always valid
        cpc = (ad_data["spend"] / ad_data["clicks"]) if ad_data["clicks"] > 0 else float("inf")

        print(f"CTR: {ctr:.2f}% | CPC: ${cpc:.2f}")

        if ctr < 0.50 or cpc > 5.00:
            verdict = f"LOSER - Bad early signals. CTR: {ctr:.2f}%, CPC: ${cpc:.2f}"
            execute_action(ad_to_grade, "KILL")
            log_experiment(ad_to_grade, ad_data, verdict)
            return

        print("PASS - Early signals are healthy. Let it run.")
        return

    # 4. STAGE 2: 48-Hour Fatigue Check — baseline.md rule: kill if ROAS < 2.0 over 48h
    if 24 <= hours < 72:
        if ad_data["spend"] > 0:
            roas = ad_data["revenue"] / ad_data["spend"]
            print(f"48h ROAS Check: {roas:.2f}")

            if roas < 2.0:
                verdict = f"LOSER - ROAS {roas:.2f} fell below fatigue threshold of 2.0 at 48h."
                execute_action(ad_to_grade, "KILL")
                log_experiment(ad_to_grade, ad_data, verdict)
                return

            print(f"PASS - ROAS {roas:.2f} is above fatigue floor. Let it run to 72h.")
        else:
            print("No spend recorded yet at 48h. Check ad activation status.")
        return

    # 5. STAGE 3: 72-Hour Final Money Check — the definitive verdict
    if hours >= 72:
        roas = (ad_data["revenue"] / ad_data["spend"]) if ad_data["spend"] > 0 else 0.0
        print(f"Final 72h ROAS: {roas:.2f}")

        if roas >= 2.5:
            verdict = f"WINNER - Final ROAS {roas:.2f} beats the 2.5 target."
            execute_action(ad_to_grade, "SCALE")
            log_experiment(ad_to_grade, ad_data, verdict)
        else:
            verdict = f"LOSER - Final ROAS {roas:.2f} failed the 2.5 target."
            execute_action(ad_to_grade, "KILL")
            log_experiment(ad_to_grade, ad_data, verdict)

# Run the script
if __name__ == "__main__":
    grade_and_execute()
