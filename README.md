# Kindlelator

Kindlelator is a local-first OCR + translation workflow for Kindle-style pages.

## What it does
- Captures a visible browser tab screenshot from the Chrome extension
- Sends the image to the backend OCR endpoint
- Translates the extracted text using DeepL and optional OpenAI refinement
- Shows the result in the extension sidebar

## Requirements
- Python 3.11+
- A Chrome/Edge browser
- API keys for OpenAI and DeepL in a .env file

## Setup
1. Create a virtual environment
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Create a .env file with:
   ```env
   OPENAI_API_KEY=your-openai-key
   DEEPL_API_KEY=your-deepl-key
   HOST=127.0.0.1
   PORT=8000
   ```
4. Start the backend
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```
5. Load the extension from the extension/ directory in Chrome.

## Usage
- Open the extension popup and set the backend URL (default: http://127.0.0.1:8000)
- Click Capture & Translate on the page you want to process

## Deployment note
For GitHub-based hosting, the backend can be deployed to any Python host that supports Uvicorn/FastAPI, and the extension can point to the hosted backend URL.
