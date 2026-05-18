"""
Streaming example — print tokens as they arrive in real time.
"""

from agentrouter import Client

client = Client(api_key="sk-YOUR_API_KEY_HERE")

print("Streaming response:\n")
for token in client.stream("Write a haiku about Python programming."):
    print(token, end="", flush=True)
print()  # newline after stream
