import os
import sys
import json
from flask import Flask, render_template, request, jsonify
# We use the direct import for Render because Render has stable Python
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import google.generativeai as genai

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False 

# --- CONFIGURE AI ---
# Get key from Render Environment Variable
API_KEY = os.environ.get("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if not API_KEY:
        return jsonify({"error": "Server Error: API Key missing."}), 500

    url = request.json.get('url')
    print(f"🔹 Analyzing: {url}")
    
    try:
        # 1. Extract Video ID
        if "v=" in url:
            video_id = url.split('v=')[1].split('&')[0]
        elif "youtu.be/" in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
        else:
            return jsonify({"error": "Invalid URL"}), 400
        
        # 2. Get Transcript (The Native Way)
        # Check for cookies in Render's secret path OR local path
        cookie_path = None
        if os.path.exists('/etc/secrets/cookies.txt'):
            cookie_path = '/etc/secrets/cookies.txt'
        elif os.path.exists('cookies.txt'):
            cookie_path = 'cookies.txt'

        try:
            # Fetch using the library directly (Works on Render)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookie_path)
            
            try:
                # Try Manual English
                transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
            except:
                try:
                    # Try Auto English
                    transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
                except:
                    # Translate Fallback
                    transcript = transcript_list[0].translate('en')
            
            transcript_data = transcript.fetch()
            
        except Exception as e:
            print(f"Transcript Error: {e}")
            return jsonify({"error": "자막을 가져올 수 없습니다. (Cookies required?)"}), 400

        full_text = " ".join([t['text'] for t in transcript_data])
        
        # 3. AI Analysis
        prompt = f"""
        You are an English Tutor. Analyze this:
        "{full_text[:20000]}"
        
        OUTPUT JSON (No Markdown):
        {{
            "summary": "3 sentences in natural Korean (~해요).",
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
               {{"level": "초급", "text": "..."}},
               {{"level": "중급", "text": "..."}},
               {{"level": "고급", "text": "..."}}
            ]
        }}
        """
        
        response = model.generate_content(prompt)
        # Clean JSON
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        start = clean_json.find('{')
        end = clean_json.rfind('}') + 1
        return clean_json[start:end]

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5002)