from flask import Flask, request, jsonify, Response, render_template
from functools import wraps
import json
import cloudscraper
import time
import uuid

# ---------------------------------------------------
# CloudflareRequester
# ---------------------------------------------------
class CloudflareRequester:
    def __init__(
        self,
        model="@cf/meta/llama-3.1-8b-instruct",
        # Additional parameters to tweak CloudScraper
        interpreter="native",  # Or 'nodejs', 'js2py', 'chakra', etc.
        ecdhCurve="secp384r1", # Another ECDH curve might help with TLS handshake
        debug=False
    ):
        # Example usage of advanced parameters:
        self.scraper = cloudscraper.create_scraper(
            interpreter=interpreter,
            ecdhCurve=ecdhCurve,
            debug=debug,
            # Force a custom or random "browser" user agent:
            browser={"browser": "chrome", "platform": "windows", "desktop": True, "mobile": False},
            # If you'd like to specify a custom user-agent or cipher suite, you could do:
            # cipherSuite="ECDHE-ECDSA-AES128-GCM-SHA256",
            # user_agent="MyCustomAgent/1.0"
        )

        # Warm up by hitting the root domain—so CloudScraper attempts to solve any challenge
        # This may store cookies in the scraper before calling /api/inference
        try:
            self.scraper.get("https://playground.ai.cloudflare.com")
        except Exception as e:
            print(f"[Warm Up] Error warming up Cloudscraper: {e}")

        # Endpoints
        self.chat_endpoint = "https://playground.ai.cloudflare.com/api/inference"
        self.models_endpoint = "https://playground.ai.cloudflare.com/api/models"

        self.headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            # The user agent is often overridden by CloudScraper’s internal logic
            # but we can keep a fallback here.
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        self.model = model

    def create_payload(self, system_prompt, messages, temperature, max_tokens, stream):
        """
        Construct the payload for the Cloudflare Playground API.
        """
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        payload = {
            "messages": formatted_messages,
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            "lora": None,
        }
        return payload

    def send_request(self, system_prompt, messages, temperature=0.7, max_tokens=2048, stream=False):
        """
        Send the Chat request to Cloudflare's Playground API.
        """
        payload = self.create_payload(system_prompt, messages, temperature, max_tokens, stream)

        # Optional: re-warm the domain each request, in case ephemeral serverless resets cookies
        # self.scraper.get("https://playground.ai.cloudflare.com")

        response = self.scraper.post(
            self.chat_endpoint,
            headers=self.headers,
            data=json.dumps(payload),
            stream=True
        )

        if not response.ok:
            # Raise an exception showing status code and text
            # This will bubble up to your Flask route
            raise Exception(f"Request failed: {response.status_code} {response.reason}")

        return self._process_stream(response) if stream else self._process_full(response)

    def _process_stream(self, response):
        """
        Processes SSE stream and yields lines as they come.
        """
        def stream_generator():
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: ") and line != "data: [DONE]":
                    yield line + "\n"
                elif line == "data: [DONE]":
                    yield "data: [DONE]\n"
        return stream_generator()

    def _process_full(self, response):
        """
        Reads the full response line by line and concatenates the content.
        """
        result = ""
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data: ") and line != "data: [DONE]":
                data = json.loads(line[6:])
                result += data.get("response", "")
        return result

    def get_models(self):
        """
        Fetch the list of models from the Cloudflare Playground.
        """
        # Optional: warm up again before calling /api/models
        # self.scraper.get("https://playground.ai.cloudflare.com")

        response = self.scraper.get(self.models_endpoint, headers=self.headers)
        if not response.ok:
            raise Exception(f"Model fetch failed: {response.status_code} {response.reason}")
        return response.json()

# ---------------------------------------------------
# Flask App
# ---------------------------------------------------
app = Flask(__name__)

API_KEYS = {
    "ish_ajl27Qo8pHgq5jZzIdoC178MpOk0oKWExGkn": "active",
    "ish_XD8IdgDTbMPPQI9AaBfiX0E1JjKjxswU4pfL": "active",
    "ish_i7YkVQ44OkF3v0BfHCb30JZhTaxPIl65EDlW": "active",
    "ish_0Ewk07qYGzxQaU1wpiYcW5NqkzmUxvm6IgJo": "active",
    "ish_QjH1M2SXsryBMm6kz4gdllJwgGFfnreTRhhX": "active",
    "ish_WhpU08xPDt8g9Riusgjxt2G9q1TwG4VOiHly": "active",
    "ish_hU92QWtYUWQZz37Z7BudJK3L8QDP0mLjmxWG": "active",
    "ish_ULFSj8kj6h1HPd6xVBJwY0Rq6jzNr0m3X5rX": "active",
    "ish_05cRwco4SRdOldAkCTWdNlMizzA95pyOARFR": "active",
    "ish_YUJRIxzCouub5R4rmmC8mD6kj6C0JxJx3WQM": "active",
}

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-KEY")
        if not api_key or API_KEYS.get(api_key) != "active":
            return jsonify({"error": "Invalid or missing API key"}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def documentation():
    return render_template("index.html")

@app.route("/chat/v1/completions", methods=["POST"])
@require_api_key
def chat_completions():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        model         = data.get("model", "@cf/meta/llama-3.1-8b-instruct")
        system_prompt = data.get("system_prompt", "")
        messages      = data.get("messages", [])
        temperature   = data.get("temperature", 0.7)
        max_tokens    = data.get("max_tokens", 2048)
        stream        = data.get("stream", False)

        if not messages:
            return jsonify({"error": "At least one message is required."}), 400

        # Example of passing advanced arguments:
        requester = CloudflareRequester(
            model=model,
            interpreter="native",   # or "nodejs", "js2py", "chakra", etc.
            ecdhCurve="secp384r1",  # or "prime256v1"
            debug=False             # turn on if you want verbose debugging
        )

        if stream:
            generator = requester.send_request(
                system_prompt=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            return Response(generator, content_type="text/event-stream")

        response_text = requester.send_request(
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        response_id = f"ish-{uuid.uuid4()}"
        created_timestamp = int(time.time())

        return jsonify({
            "id": response_id,
            "object": "chat.completion",
            "created": created_timestamp,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models", methods=["GET"])
@require_api_key
def list_models():
    try:
        # Example: pass advanced arguments if desired
        requester = CloudflareRequester(
            model="@cf/meta/llama-3.1-8b-instruct",
            interpreter="native",
            ecdhCurve="secp384r1",
            debug=False
        )
        models_data = requester.get_models()
        return jsonify(models_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate_api_key", methods=["POST"])
def generate_api_key():
    return jsonify({"message": "API key generated successfully", "api_key": "Wtf are you doing here?, it's free lol!"})

@app.route("/revoke_api_key", methods=["POST"])
def revoke_api_key():
    return jsonify({"message": "API key revoked successfully", "api_key": "Wtf are you doing here?, it's free lol!"})

if __name__ == "__main__":
    app.run(debug=True, port=8000)
