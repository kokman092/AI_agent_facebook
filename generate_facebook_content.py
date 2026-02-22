import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def generate_bulk_posts(num_posts=30):
    """
    Calls OpenRouter once to generate a batch of captions and image prompts to save API costs.
    """
    print(f"Generating {num_posts} posts with image ideas via OpenRouter...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Prompt designed to generate both the text caption and a description for the image generator
    prompt = (
        f"Generate {num_posts} highly engaging, viral Facebook posts that include an image. "
        "The content should be fascinating facts, 'would you rather' scenarios, or controversial "
        "technology opinions designed to force people to comment. "
        "For each post, provide: \n"
        "1. 'caption': The text to post (under 25 words).\n"
        "2. 'image_prompt': A highly detailed, descriptive prompt for an AI image generator to create the accompanying picture.\n\n"
        "Format the output strictly as a JSON array of objects, like this:\n"
        '[\n  {"caption": "Pineapple on pizza: Yes or No?", "image_prompt": "A cinematic, slightly dramatic close-up photo of a pepperoni pizza with large chunks of glowing yellow pineapple on it"}\n]'
    )
    
    data = {
        "model": "google/gemini-2.5-flash", # Cheap, fast model to maximize budget
        "messages": [
            {"role": "system", "content": "You are a social media expert whose only goal is to maximize comment count on Facebook posts."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content']
        
        # Clean up Markdown formatting if the AI returned it inside a code block
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
             content = content[3:-3].strip()
        
        posts_array = json.loads(content)
        
        # If the AI returned an object with a key containing the array, extract it
        if isinstance(posts_array, dict):
            for key in posts_array:
                if isinstance(posts_array[key], list):
                    posts_array = posts_array[key]
                    break

        if not isinstance(posts_array, list) or len(posts_array) == 0:
            print("Error: AI did not return a valid list of posts.")
            return False

        # Append to a local JSON Lines file so we can easily parse objects later
        with open("facebook_image_content_bank.jsonl", "a", encoding="utf-8") as f:
            for post in posts_array:
                if 'caption' in post and 'image_prompt' in post:
                    f.write(json.dumps(post) + "\n")
                
        print(f"✅ Successfully generated and saved {len(posts_array)} image posts to facebook_image_content_bank.jsonl")
        return True

    except Exception as e:
        print(f"❌ Error generating posts: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"API Response: {response.text}")
        return False

if __name__ == "__main__":
    print("🧠 Starting 'The Brain' (Image Content Generator)...")
    generate_bulk_posts(30)
