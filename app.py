import aiohttp
import asyncio
import json
from flask import Flask, request, jsonify

# Initialize the Flask app
app = Flask(__name__)

BASE_URL = "https://free-duck-duck-go-assist-coral.vercel.app/api"
TOKEN_URL = BASE_URL + "/get-token"
CHAT_URL = BASE_URL + "/conversation"

token = ""
messHistory = []

# Async function to handle chat responses
async def chat(messList):
    global token
    async with aiohttp.ClientSession() as session:
        # Request a token if not already fetched
        if token == "":
            async with session.get(TOKEN_URL) as resp:
                data = await resp.json()
                token = data["token"]

        body = {
            "token": token,
            "message": messList,
            "stream": True
        }

        # Post the message to the chat API
        async with session.post(CHAT_URL, json=body) as resp:
            if resp.status != 200:
                return {"error": "Failed to get response from server."}
            fullmessage = ""
            async for chunk in resp.content:
                data_str = chunk.decode("utf-8")
                json_str = data_str.replace("data: ", "")
                if json_str.strip() == "[DONE]":
                    break
                else:
                    try:
                        data_dict = json.loads(json_str)
                        fullmessage += data_dict["message"]
                        token = data_dict["resp_token"]  # Update token
                    except KeyError:
                        pass
            messHistory.append({"role": "assistant", "content": fullmessage})  # Append assistant response to history
            return fullmessage

# Route to handle chat requests compatible with OpenAI /v1/chat/completions
@app.route("/v1/chat/completions", methods=["POST"])
def handle_chat():
    try:
        # Get the user message from the POST request
        data = request.get_json()
        model = data.get("model", "")  # OpenAI API expects model, messages, etc.
        messages = data.get("messages", [])

        if not messages:
            return jsonify({"error": "Messages are required"}), 400

        # Add user message to history
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role and content:
                messHistory.append({"role": role, "content": content})

        # Run the chat function and return the result
        result = asyncio.run(chat(messHistory))
        if isinstance(result, dict) and "error" in result:
            return jsonify({"error": result["error"]}), 500

        # Format the response as per OpenAI's API structure
        response = {
            "id": "chatcmpl-123",  # Placeholder ID
            "object": "chat.completion",
            "created": 1698312333,  # Example timestamp
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(messHistory),  # Example token count, adjust as needed
                "completion_tokens": len(result.split()),  # Example completion token count
                "total_tokens": len(messHistory) + len(result.split())
            }
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run Flask app
    app.run(host="0.0.0.0")
