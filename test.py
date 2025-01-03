import requests
import json

def send_chat_completion(stream=False):
    url = "http://127.0.0.1:3666/chat/v1/completions"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": "ish_ajl27Qo8pHgq5jZzIdoC178MpOk0oKWExGkn"  # Include your valid API key
    }
    payload = {
        "model": "@cf/meta/llama-3.1-8b-instruct",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "stream": stream
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload), stream=stream)

    if response.status_code == 200:
        print("\n--- Response ---")
        if stream:
            print("Streaming mode:\n")
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = line[6:]  # Strip the "data: " prefix
                    print(json.loads(data)["response"])
                elif line == "data: [DONE]":
                    print("\n[Stream Complete]")
        else:
            print("Non-streaming mode:\n")
            print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    print("=== Non-Streaming Mode ===")
    send_chat_completion(stream=False)

    print("\n\n=== Streaming Mode ===")
    send_chat_completion(stream=True)
