"""
Basic chat example — get a full reply as a string.
"""

from agentrouter import Client

client = Client(api_key="sk-YOUR_API_KEY_HERE")

reply = client.ask("What is the capital of France?")
print(reply)
