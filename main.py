"""Bootstraps services and runs the campaign generator."""

from pathlib import Path

from campaign import generate_campaign
from generation.google_genai import GoogleGenAIService

if __name__ == "__main__":
    # Load the example json data
    campaign_json_path = "assets/briefs/example_briefs.json"
    
    # Instantiate gen ai service
    google_session = GoogleGenAIService()

    # Generate campaign    
    generate_campaign(raw_json=campaign_json_path, gen_service=google_session, output_dir=Path("output"))
