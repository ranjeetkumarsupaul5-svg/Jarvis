from backend.tools.web_tools import search_web


result = search_web("artificial intelligence")

print("\n--- WEB SEARCH TEST ---\n")

print("Status:", result["status"])
print("Message:", result["message"])
print("Query:", result["query"])