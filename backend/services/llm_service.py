import json
import os
import re
from typing import Any, Dict, List, Optional
from openai import OpenAI

from backend.config import GROQ_API_KEY, DEFAULT_LLM_MODEL


class LLMService:
    def __init__(self):
        self.client: Optional[OpenAI] = None
        self.provider: str = "offline"
        self.model: str = DEFAULT_LLM_MODEL
        self._initialize_client()

    def _initialize_client(self):
        """
        Initialize the primary LLM provider (Groq or OpenAI).
        """
        api_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        if api_key:
            try:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.groq.com/openai/v1"
                )
                self.provider = "groq"
                self.model = os.getenv("GROQ_MODEL", DEFAULT_LLM_MODEL)
                return
            except Exception as e:
                print(f"Warning: Failed to initialize Groq client: {e}")

        # Check for standard OpenAI fallback
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                self.client = OpenAI(api_key=openai_key)
                self.provider = "openai"
                self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                return
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")

        self.client = None
        self.provider = "offline"

    def is_available(self) -> bool:
        return self.client is not None

    def generate_chat_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate conversational completion using the configured LLM.
        """
        if not self.is_available():
            self._initialize_client()

        if not self.is_available():
            return (
                "I am currently operating in offline mode. "
                "To enable my full AI reasoning, please configure GROQ_API_KEY in your .env file."
            )

        system = system_prompt or (
            "You are JARVIS, an advanced, highly intelligent desktop AI operating system. "
            "You are concise, professional, futuristic, and helpful. "
            "Provide direct answers suitable for both voice and visual display."
        )

        messages = [{"role": "system", "content": system}]

        if conversation_history:
            messages.extend(conversation_history[-8:])

        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM generation error ({self.provider}): {e}")
            return f"I encountered an error communicating with my AI core: {str(e)}"

    def plan_and_route(
        self,
        user_prompt: str,
        available_tools: Dict[str, Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent, extract arguments, and select appropriate tool(s).
        """
        if not self.is_available():
            self._initialize_client()

        # If offline or key not set, use deterministic rule-based routing
        if not self.is_available():
            return self._fallback_rule_router(user_prompt, available_tools)

        # Build tool definitions for prompt
        tools_summary = []
        for name, meta in available_tools.items():
            desc = meta.get("description", "")
            params = meta.get("parameters", {})
            tools_summary.append(f"- {name}: {desc} | Parameters: {params}")

        tools_str = "\n".join(tools_summary)

        system = (
            "You are the central Planner of JARVIS AI OS.\n"
            "Analyze the user's natural language request, select the best tool from the available tools, "
            "and extract required parameters.\n"
            "If no tool is required (e.g. conversational questions, greetings, jokes, philosophical queries), "
            "set tool_name to null and provide a direct_response.\n\n"
            "CRITICAL TOOL SELECTION RULES:\n"
            "1. PERSONAL MEMORY & USER FACTS:\n"
            "   - If the user asks about their identity, name, learning topic, current project, preferences, or past statements (e.g. 'what is my name?', 'do you remember my name?', 'what am I learning?', 'who am I?'):\n"
            "     NEVER select 'search_web'. Use the provided Context to answer directly (tool_name=null) or choose 'search_memory' / 'recall'.\n"
            "2. WEB SEARCH:\n"
            "   - ONLY choose 'search_web' for questions about external world events, public news, weather, or explicit internet search requests (e.g. 'latest AI news', 'weather today', 'search the web for Python tutorials').\n"
            "   - NEVER search the web for personal user information.\n\n"
            f"Available Tools:\n{tools_str}\n\n"
            f"Context:\n{context or 'No prior context.'}\n\n"
            "Return ONLY a valid JSON object with the following schema:\n"
            "{\n"
            '  "intent": "<intent_category>",\n'
            '  "tool_name": "<exact_tool_name_or_null>",\n'
            '  "parameters": { "<param_name>": "<value>" },\n'
            '  "direct_response": "<spoken_response_if_no_tool_needed>",\n'
            '  "requires_confirmation": false,\n'
            '  "confirmation_message": null\n'
            "}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=400
            )

            raw_text = response.choices[0].message.content.strip()

            # Clean markdown code blocks
            clean_json = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
            clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE).strip()

            parsed = json.loads(clean_json)
            return parsed
        except Exception as e:
            print(f"LLM planning warning ({e}), falling back to deterministic routing.")
            return self._fallback_rule_router(user_prompt, available_tools)

    def _fallback_rule_router(self, user_prompt: str, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast deterministic pattern matching when offline or as a fallback.
        """
        prompt = user_prompt.lower().strip()

        # Open application
        open_prefix = None
        for prefix in ["open ", "launch ", "start "]:
            if prompt.startswith(prefix):
                open_prefix = prefix
                break

        if open_prefix:
            app = prompt[len(open_prefix):].strip()
            for filler in ["for me", "please", "right now", "now", "app", "application"]:
                app = re.sub(rf"\b{filler}\b", "", app, flags=re.IGNORECASE).strip()
            return {
                "intent": "open_application",
                "tool_name": "open_application",
                "parameters": {"app_name": app},
                "direct_response": None
            }

        # Screenshot
        if "screenshot" in prompt:
            return {
                "intent": "screenshot",
                "tool_name": "take_screenshot",
                "parameters": {},
                "direct_response": None
            }

        # System info / diagnostics
        if any(k in prompt for k in ["system info", "system information", "ram", "cpu", "status", "health"]):
            return {
                "intent": "system_info",
                "tool_name": "get_system_info",
                "parameters": {},
                "direct_response": None
            }

        # Minimize windows
        if "minimize" in prompt:
            return {
                "intent": "minimize_windows",
                "tool_name": "minimize_all_windows",
                "parameters": {},
                "direct_response": None
            }

        # Run terminal command
        if prompt.startswith("run command ") or prompt.startswith("terminal "):
            cmd = prompt.replace("run command ", "", 1).replace("terminal ", "", 1).strip()
            return {
                "intent": "run_command",
                "tool_name": "run_command",
                "parameters": {"command": cmd},
                "direct_response": None
            }

        # Search files
        if prompt.startswith("search file ") or prompt.startswith("find file "):
            keyword = prompt.replace("search file ", "", 1).replace("find file ", "", 1).strip()
            return {
                "intent": "search_files",
                "tool_name": "search_files",
                "parameters": {"folder": ".", "keyword": keyword},
                "direct_response": None
            }

        # Memory / Personal queries (MUST precede web search to avoid routing personal queries to web)
        personal_patterns = [
            r"^(what|who|where|how) (is|are|am|was) (my|i)\b",
            r"^what(?:'s|s) my\b",
            r"^do you (remember|know|recall)\b",
            r"^(can you )?tell me (about )?(my|what my|what i am)\b",
            r"^what did i (tell you|say)\b",
            r"^what do you (remember|know) about (me|my)\b",
            r"^(list|show) (my )?memories\b",
            r"^who am i\b",
        ]
        if any(re.search(pat, prompt) for pat in personal_patterns):
            q = prompt
            for prefix in [
                "what is my ", "what's my ", "what was my ", "what am i ",
                "do you remember my ", "do you know my ", "do you recall my ",
                "tell me my ", "tell me about my ", "can you tell me my ",
                "what did i tell you about my ", "what did i say about my "
            ]:
                if prompt.startswith(prefix):
                    q = prompt.replace(prefix, "", 1).strip()
                    break
            q = q.rstrip("?.! ")
            if q in ("who am i", "who i am"):
                q = "name"
            tool = "search_memory" if "search_memory" in available_tools else "recall"
            return {
                "intent": "recall",
                "tool_name": tool,
                "parameters": {"query": q or prompt},
                "direct_response": None
            }

        # Web search
        web_prefixes = [
            "search the web for ", "search web for ", "search for ", "search ", "google ",
            "look up ", "find info on ", "find information on ", "research "
        ]
        is_web_prefix = any(prompt.startswith(p) for p in web_prefixes)
        has_personal_pronoun = bool(re.search(r"\b(my|i|me|we|our|myself)\b", prompt))
        is_info_question = (
            (prompt.startswith("who is ") or prompt.startswith("what is ") or prompt.startswith("what are "))
            and not has_personal_pronoun
        )
        is_news_or_weather = any(k in prompt for k in ["weather", "news", "forecast", "latest"])

        if is_web_prefix or is_info_question or is_news_or_weather:
            q = prompt
            for p in web_prefixes:
                if q.startswith(p):
                    q = q.replace(p, "", 1).strip()
                    break
            return {
                "intent": "web_search",
                "tool_name": "search_web",
                "parameters": {"query": q or prompt},
                "direct_response": None
            }

        # General conversation
        return {
            "intent": "general_chat",
            "tool_name": None,
            "parameters": {},
            "direct_response": f"I heard: '{user_prompt}'. How would you like me to assist you with that, sir?"
        }


    def analyze_image(self, image_path: str, prompt: str = "Describe what you see in this image in detail.") -> Dict[str, Any]:
        """
        Analyze an image using a multimodal LLM (Groq vision or OpenAI gpt-4o-mini).
        """
        if not self.is_available():
            self._initialize_client()

        if not os.path.exists(image_path):
            return {
                "success": False,
                "message": f"Image file not found: {image_path}",
                "data": None,
                "error": "FileNotFound"
            }

        import base64
        import mimetypes

        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/png"

        try:
            with open(image_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to read image: {e}",
                "data": None,
                "error": str(e)
            }

        if not self.is_available():
            return {
                "success": False,
                "message": "AI vision requires an active API key (GROQ_API_KEY or OPENAI_API_KEY).",
                "data": {"image_path": image_path},
                "error": "OfflineMode"
            }

        # Select vision-capable model
        vision_model = self.model
        if self.provider == "groq":
            vision_model = "llama-3.2-11b-vision-preview"
        elif self.provider == "openai":
            vision_model = "gpt-4o-mini"

        try:
            response = self.client.chat.completions.create(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=600
            )
            analysis = response.choices[0].message.content.strip()
            return {
                "success": True,
                "message": analysis,
                "data": {
                    "image_path": image_path,
                    "analysis": analysis,
                    "model_used": vision_model
                },
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Multimodal analysis error: {e}",
                "data": {"image_path": image_path},
                "error": str(e)
            }


# Singleton service instance
llm_service = LLMService()
