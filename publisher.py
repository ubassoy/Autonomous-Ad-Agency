import json
import os
import requests

# 1. Load credentials from environment variables (never hardcode these)
ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID")  # Format: act_XXXXXXXXX
PAGE_ID = os.environ.get("META_PAGE_ID")
API_VERSION = "v19.0"

def publish_challenger_to_facebook():
    # Guard: Make sure credentials are loaded before doing anything
    if not all([ACCESS_TOKEN, AD_ACCOUNT_ID, PAGE_ID]):
        print("Error: Missing Meta credentials. Check your .env file.")
        return

    print("Artie is logging into Facebook...")

    # 2. Read the challenger ad and the original template
    try:
        with open("challenger.json", "r") as file:
            challenger_ad = json.load(file)

        with open("template.json", "r") as file:
            template_data = json.load(file)
    except FileNotFoundError as e:
        print(f"Error: Could not find the ad files. {e}")
        return

    # 3. STEP ONE: Create the Ad Creative (the visual poster)
    print("Building the visual creative...")
    creative_url = f"https://graph.facebook.com/{API_VERSION}/{AD_ACCOUNT_ID}/adcreatives"

    creative_payload = {
        "access_token": ACCESS_TOKEN,
        "name": f"AI_Challenger_{challenger_ad['headline'][:15]}",
        "object_story_spec": {
            "page_id": PAGE_ID,
            "link_data": {
                "image_hash": challenger_ad["image_hash"],
                "link": "https://yourwebsite.com/offer",
                "message": challenger_ad["primary_text"],
                "name": challenger_ad["headline"],
                "call_to_action": {
                    "type": challenger_ad["call_to_action"]
                }
            }
        }
    }

    creative_response = requests.post(creative_url, json=creative_payload)
    creative_result = creative_response.json()

    if "id" not in creative_result:
        print("Error creating the visual ad:", creative_result)
        return

    creative_id = creative_result["id"]
    print(f"Success! Visual poster created. ID: {creative_id}")

    # 4. STEP TWO: Launch the Ad (attach the creative to the budget)
    print("Publishing the ad to the Ad Set...")
    ad_url = f"https://graph.facebook.com/{API_VERSION}/{AD_ACCOUNT_ID}/ads"

    ad_payload = {
        "access_token": ACCESS_TOKEN,
        "name": "AI_Challenger_Live_Test",
        "adset_id": template_data["metadata"]["ad_set_id"],
        "creative": {"creative_id": creative_id},
        "status": "PAUSED"  # CRITICAL SAFETY MEASURE: review before activating
    }

    ad_response = requests.post(ad_url, json=ad_payload)
    ad_result = ad_response.json()

    if "id" in ad_result:
        # Save the live challenger ad ID so grader.py can find it
        challenger_ad["ad_id"] = ad_result["id"]
        with open("challenger.json", "w") as file:
            json.dump(challenger_ad, file, indent=2)

        print(f"Boom! Ad successfully pushed to Facebook. Ad ID: {ad_result['id']}")
        print("Ad is PAUSED. Review it in Ads Manager before activating.")
    else:
        print("Error launching the ad:", ad_result)

# Run the script
if __name__ == "__main__":
    publish_challenger_to_facebook()
