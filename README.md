# Icon Ad-Verifier (POC)

**Problem:** Enterprise clients fear AI hallucinations.
**Solution:** A programmatic guardrail that grades `AdGPT` output against the client's actual website before a human ever sees it.

**Tech Stack:**
* **Engine:** Google Gemini 1.5 Flash (Chosen for 1M+ token context window to scrape full documentation).
* **Frontend:** Streamlit.
* **Speed:** < 3 seconds per verification.

**How to run:**
1. Clone repo
2. `pip install -r requirements.txt`
3. `streamlit run ad_verifier_gemini.py`
