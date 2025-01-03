from flask import Flask, request, jsonify, Response, render_template, send_from_directory
# from flask_cloudflared import run_with_cloudflared
import cloudscraper
import json
import time
import uuid

# ---------------------------------------------------
# CloudflareRequester
# ---------------------------------------------------
class CloudflareRequester:
    def __init__(self, model="@cf/meta/llama-3.1-8b-instruct"):
        self.scraper = cloudscraper.create_scraper()

        # Endpoints
        self.chat_endpoint = "https://playground.ai.cloudflare.com/api/inference"
        self.models_endpoint = "https://playground.ai.cloudflare.com/api/models"

        self.headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
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
        response = self.scraper.post(
            self.chat_endpoint,
            headers=self.headers,
            data=json.dumps(payload),
            stream=True  # We always open in streaming mode so we can parse SSE lines
        )

        if not response.ok:
            raise Exception(f"Request failed: {response.status_code} {response.reason}")

        if stream:
            return self._process_stream(response)
        else:
            return self._process_full(response)

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
        Fetch the list of models from Cloudflare Playground.
        """
        response = self.scraper.get(self.models_endpoint, headers=self.headers)
        if not response.ok:
            raise Exception(f"Model fetch failed: {response.status_code} {response.reason}")
        return response.json()


# ---------------------------------------------------
# Flask App
# ---------------------------------------------------
app = Flask(__name__)
# run_with_cloudflared(app)

# ---------------------------------------------------
# Serve index.html at the root
# ---------------------------------------------------

@app.route('/static/templates')
def static_files(path):
    return send_from_directory('static', path)

@app.route("/")
def home():
    """
    Render the Playground UI.
    """
    return render_template("index.html")

@app.route("/playground")
def playground():
    """
    Render the Playground UI.
    """
    return render_template("playground.html")

@app.route("/api")
def api_documentation():
    """
    Render the Playground UI.
    """
    return render_template("api.html")

# ---------------------------------------------------
# Chat Completions
# ---------------------------------------------------
@app.route("/chat/v1/completions", methods=["POST"])
def chat_completions():
    """
    POST /chat/v1/completions
    """
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

        requester = CloudflareRequester(model=model)

        # If stream=True, return SSE event stream
        if stream:
            generator = requester.send_request(
                system_prompt=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            return Response(generator, content_type="text/event-stream")

        # Otherwise, do a single call and return JSON
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


# ---------------------------------------------------
# List Models
# ---------------------------------------------------
@app.route("/models", methods=["GET"])
def list_models():
    """
    GET /models
    """
    try:
        requester = CloudflareRequester()
        models_data = requester.get_models()
        return jsonify(models_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------
# Main
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)  # For Experimental use only
