import os
import sys
import subprocess
import json
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False 

# --- CONFIGURE AI (SECURE METHOD) ---
# This looks for the key in the server's environment variables.
# Do NOT paste your actual key here anymore.
API_KEY = os.environ.get("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    print("⚠️ WARNING: GEMINI_API_KEY not found. App will fail if AI is called.")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    # Security Check
    if not API_KEY:
        return jsonify({"error": "Server Error: API Key not configured."}), 500

    url = request.json.get('url')
    
    try:
        # 1. Extract Video ID
        if "v=" in url:
            video_id = url.split('v=')[1].split('&')[0]
        elif "youtu.be/" in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
        else:
            return jsonify({"error": "Invalid URL"}), 400
        
        # 2. Run CLI Tool
        # We use the CLI method because it proved most reliable for you locally
        command = ['youtube_transcript_api', video_id, '--format', 'json']
        
        # Add cookies if the secret file exists on the server
        if os.path.exists('/etc/secrets/cookies.txt'):
             command.extend(['--cookies', '/etc/secrets/cookies.txt'])
        elif os.path.exists('cookies.txt'):
             command.extend(['--cookies', 'cookies.txt'])
            
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({"error": "Could not fetch subtitles."}), 400

        # Parse output - Handle the List of Lists [[...]] format
        transcript_data = json.loads(result.stdout)[0]
        full_text = " ".join([t['text'] for t in transcript_data])
        
        # 3. AI Analysis
        prompt = f"""
        You are an English Tutor for Koreans. Analyze this:
        "{full_text[:20000]}"
        
        OUTPUT JSON (No Markdown):
        {{
            "summary": "3 sentences in natural Korean (friendly tone ~해요).",
            "vocab": [
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}},
                {{"word": "Word", "meaning": "Meaning", "example": "Ex"}}
            ],
            "shadowing": [
               {{"level": "초급 (Short)", "text": "..."}},
               {{"level": "중급 (Medium)", "text": "..."}},
               {{"level": "고급 (Long)", "text": "..."}}
            ]
        }}
        """
        
        response = model.generate_content(prompt)
        # Clean JSON
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        # Find the first { and last }
        start = clean_json.find('{')
        end = clean_json.rfind('}') + 1
        return clean_json[start:end]

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5002)