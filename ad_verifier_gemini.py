import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import os

# --- Page Config ---
st.set_page_config(
    page_title="Ad Verifier - Gemini Powered",
    page_icon="🛡️",
    layout="wide"
)

# --- Sidebar ---
with st.sidebar:
    st.header("About")
    st.info("Powered by **Gemini 2.5 Flash**")
    st.markdown("""
    **Why Gemini 2.5 Flash?**
    - **Speed:** Next-gen inference speed for instant verification.
    - **Context Window:** Massive context window allows us to read full documentation without truncation.
    """)

# --- Main Interface ---
st.title("🛡️ AI Ad Script Verifier")
st.markdown("Ensure your ad copy is grounded in reality and consistent with your brand voice.")

# --- Inputs ---
col1, col2 = st.columns(2)
with col1:
    gemini_key = st.text_input("Google Gemini API Key", type="password", help="Get yours at aistudio.google.com")
with col2:
    target_url = st.text_input("Target URL", placeholder="https://www.example.com")

ad_script = st.text_area("Generated Ad Script", height=150, placeholder="Paste the AI-generated ad copy here...")

verify_btn = st.button("Verify Script", type="primary")

# --- Logic ---

def scrape_website(url):
    """Scrapes all visible text from the target URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        return f"ERROR: {str(e)}"

if verify_btn:
    if not gemini_key:
        st.error("Please enter your Google Gemini API Key.")
    elif not target_url:
        st.error("Please enter a Target URL.")
    elif not ad_script:
        st.error("Please enter the Ad Script.")
    else:
        with st.spinner("Scraping website..."):
            site_text = scrape_website(target_url)
        
        if site_text.startswith("ERROR:"):
            st.error(f"Failed to scrape website: {site_text}")
        else:
            with st.spinner("Analyzing with Gemini 2.5 Flash..."):
                try:
                    # Configure Gemini
                    genai.configure(api_key=gemini_key)
                    
                    def get_best_model():
                        """Dynamically finds the best available model supporting generateContent."""
                        try:
                            models = list(genai.list_models())
                            # Filter for generateContent support
                            valid_models = [m for m in models if 'generateContent' in m.supported_generation_methods]
                            
                            if not valid_models:
                                return None, "No models found that support generateContent."
                            
                            # Priority: Flash -> Pro -> Any
                            flash_model = next((m for m in valid_models if "flash" in m.name.lower()), None)
                            if flash_model:
                                return flash_model.name, [m.name for m in valid_models]
                                
                            pro_model = next((m for m in valid_models if "pro" in m.name.lower()), None)
                            if pro_model:
                                return pro_model.name, [m.name for m in valid_models]
                                
                            return valid_models[0].name, [m.name for m in valid_models]
                        except Exception as e:
                            return None, f"Error listing models: {str(e)}"

                    model_name, debug_info = get_best_model()
                    
                    if not model_name:
                        st.error(f"Could not find a valid model. Debug info: {debug_info}")
                    else:
                        st.info(f"Using model: **{model_name}**")
                        model = genai.GenerativeModel(model_name)
                    
                        # Construction Prompt
                        prompt = f"""
                        You are a strict compliance and quality control officer for advertising.
                        
                        Your task is to verify an 'Ad Script' against the ground truth text from a 'Source Website'.
                        
                        Step 1: Analyize the 'Source Website Text' to understand the facts, features, and tone.
                        Step 2: Check the 'Ad Script' for any factual hallucinations (claims not supported by the website).
                        Step 3: Analyze if the tone of the ad matches the website's voice.
                        Step 4: Assign a quality score from 0-100.
                        
                        Return a valid JSON object ONLY. Do not use Markdown code blocks.
                        Structure:
                        {{
                            "score": (integer 0-100),
                            "hallucinations": ["string list of specific claims in the ad that exist nowhere on the site"],
                            "tone_consistency": "Brief analysis of whether the ad voice matches the site voice",
                            "verdict": "PASS" (if score > 80 and no major hallucinations) or "FAIL"
                        }}
                        
                        ---
                        Source Website Text:
                        {site_text[:30000]} 
                        
                        ---
                        Ad Script:
                        {ad_script}
                        """
                        # Truncate site text to avoid token limits if extremely large, though Flash has ~1M context. Safe guard at 30k chars for now for speed/safety.
                        
                        response = model.generate_content(prompt)
                        
                        # Clean response if necessary (Gemini sometimes adds ```json ... ```)
                        text_resp = response.text.strip()
                        if text_resp.startswith("```"):
                            parts = text_resp.split("```")
                            if len(parts) >= 2:
                                text_resp = parts[1]
                                if text_resp.startswith("json"):
                                     text_resp = text_resp[4:]
                        text_resp = text_resp.strip()
                        
                        result = json.loads(text_resp)
                        
                        # --- Results Display ---
                        
                        # Score
                        st.metric(label="Quality Score", value=result.get("score", 0))
                        
                        # Verdict
                        verdict = result.get("verdict", "FAIL").upper()
                        if verdict == "PASS":
                            st.success(f"Verdict: {verdict}")
                        else:
                            st.error(f"Verdict: {verdict}")
                        
                        # Tone
                        st.markdown("### Tone Analysis")
                        st.write(result.get("tone_consistency", "N/A"))
                        
                        # Hallucinations
                        hallucinations = result.get("hallucinations", [])
                        if hallucinations:
                            st.error("### ⚠️ Potential Hallucinations Detected")
                            for h in hallucinations:
                                st.write(f"- {h}")
                        elif verdict == "PASS":
                             st.success("No factual hallucinations detected.")

                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    st.write("Raw response (for debugging):")
                    if 'response' in locals():
                        st.code(response.text)
