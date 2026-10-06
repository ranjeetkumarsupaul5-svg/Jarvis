import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

#from httpx2 import query

from backend.config import ASSISTANT_NAME, USER_NAME
from backend.core.router import router
from backend.memory.memory_manager import memory_manager
from backend.services.llm_service import llm_service
def _clean_fact_value(val: Any, topic: str = "") -> str:
    """
    Extract concise entity/value from natural language predicate strings.
    Example: 'my name is Ranjeet.' -> 'Ranjeet'
             'my current project is Jarvis OS' -> 'Jarvis OS'
             'I am learning GenAI' -> 'GenAI'
    """
    if not isinstance(val, str):
        return str(val) if val is not None else ""
    cleaned = val.strip().rstrip(".?! ")
    for sep in [" is ", " am ", " are "]:
        if sep in cleaned:
            cleaned = cleaned.split(sep, 1)[1].strip()
            break
    if topic:
        topic_lower = topic.lower().strip()
        if cleaned.lower().startswith(topic_lower + " "):
            cleaned = cleaned[len(topic_lower) + 1:].strip()
    return cleaned.rstrip(".?! ")


class JarvisBrain:
    """
    Central Cognitive Engine of JARVIS AI OS.

    Translates natural language into intent, selects and executes tools,
    manages conversational memory, and synthesizes voice responses.
    """

    def clean_command(self, command: str) -> str:
        """
        Strip wake names, greeting prefixes, and formatting.
        """
        if not command:
            return ""

        text = command.strip()

        # Remove assistant name prefix/suffix with optional greeting (e.g. 'Hey Jarvis', 'OK Jarvis')
        text = re.sub(
            rf"^(hey|ok|okay|hi|hello)?\s*\b{ASSISTANT_NAME}\b[,:\s]*",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            rf"[,:\s]*\b{ASSISTANT_NAME}\b$",
            "",
            text,
            flags=re.IGNORECASE
        )

        # Remove polite filler words
        text = re.sub(
            r"^(please|could you|can you|would you)\s+",
            "",
            text,
            flags=re.IGNORECASE
        )

        return text.strip()

    def process_command(self, raw_command: str) -> Dict[str, Any]:
        """
        Process a user command from text, voice, or GUI.
        """

        if not raw_command or not raw_command.strip():
            return {
                "success": False,
                "message": "No command provided.",
                "spoken": "I didn't hear anything, sir.",
                "data": None,
                "tool": None,
                "error": "EmptyCommand"
            }

        command = self.clean_command(raw_command)

        if not command:
            command = raw_command.strip()

        # ---------------------------------------------------------
        # 1. Record user turn in memory
        # ---------------------------------------------------------
        memory_manager.add_conversation_turn("user", raw_command)

                # ---------------------------------------------------------
        # 1.5 Handle pending dangerous-action confirmation
        # ---------------------------------------------------------
        from backend.core.permission import (
            get_pending_action,
            clear_pending_action,
            is_confirmation,
            is_rejection,
        )

        pending_action = get_pending_action()

        if pending_action:

            # User approved the pending action
            if is_confirmation(command):

                tool_name = pending_action["tool"]
                args = pending_action["args"]
                kwargs = pending_action["kwargs"]

                clear_pending_action()

                result = router.execute(
                    tool_name,
                    *args,
                    _confirmed=True,
                    **kwargs
                )

                return result

            # User rejected the pending action
            if is_rejection(command):

                clear_pending_action()

                return {
                    "success": True,
                    "message": "Action cancelled.",
                    "spoken": "Okay sir, action cancelled.",
                    "data": None,
                    "tool": "permission"
                }

            # User said something other than yes/no
            return {
                "success": False,
                "message": "Please say yes to continue or no to cancel.",
                "spoken": "Please say yes to continue or no to cancel, sir.",
                "data": {
                    "pending_tool": pending_action["tool"]
                },
                "tool": "permission",
                "error": "ConfirmationExpected"
            }

        # ---------------------------------------------------------
        # 2. Handle explicit memory commands FIRST
        # ---------------------------------------------------------
        #
        # This is important:
        # Personal-memory questions must not reach the LLM planner
        # and accidentally become search_web requests.
        #
        
        # Automation / Reminder routing
        automation_query = command.lower().strip()

        if any(x in automation_query for x in [
            "remind me",
            "set a reminder",
            "create a reminder",
            "schedule a reminder"
        ]):

            # "in 10 minutes"
            match = re.search(
                r"in\s+(\d+)\s+(minutes|minute|mins|min|hours|hour|hrs|hr)\b",
                automation_query
            )

            if match:
                amount = int(match.group(1))
                unit = match.group(2)

                if "hour" in unit or "hr" in unit:
                    run_at = datetime.now() + timedelta(hours=amount)
                else:
                    run_at = datetime.now() + timedelta(minutes=amount)

                # Extract reminder message
                message = re.sub(
                    r"^remind me\s+in\s+\d+\s+(?:minutes|minute|mins|min|hours|hour|hrs|hr)\b\s*(?:to\s+)?",
                    "",
                    automation_query,
                    count=1
                ).strip()

                if not message:
                    message = "You have a scheduled reminder."

                return router.execute(
                    "add_reminder",
                    message,
                    run_at.strftime("%Y-%m-%d %H:%M:%S")
                )

        # Deterministic system monitor commands
        system_query = command.lower().strip()

        if system_query in [
            "system status",
            "system information",
            "system info",
            "check system",
            "check my system",
            "show system status",
            "show system information",
        ]:
            result = router.execute("get_system_monitor", {})

            if result.get("success"):
                data = result["data"]

                cpu = data["cpu"]["usage_percent"]
                memory = data["memory"]["usage_percent"]
                disk = data["disk"]["usage_percent"]
                battery = data["battery"]

                message = (
                    f"CPU usage is {cpu} percent. "
                    f"Memory usage is {memory} percent. "
                    f"Disk usage is {disk} percent."
                )

                if battery:
                    charging = (
                        "and the battery is charging"
                        if battery["charging"]
                        else "and the battery is not charging"
                    )

                    message += (
                        f" Battery is at {battery['percent']} percent, "
                        f"{charging}."
                    )

                return {
                    "success": True,
                    "message": message,
                    "spoken": message + " sir.",
                    "data": data,
                    "tool": "get_system_monitor",
                }

            return result

        # Deterministic weather commands
        weather_query = command.lower().strip()

        if weather_query.startswith("weather in "):
            location = command[len("weather in "):].strip()

            result = router.execute(
                "get_weather",
                {"location": location}
            )

            if result.get("success"):
                data = result["data"]

                message = (
                    f"The current weather in {data['location']} is "
                    f"{data['temperature_c']} degrees Celsius, "
                    f"with {data['humidity_percent']} percent humidity. "
                    f"It feels like {data['feels_like_c']} degrees."
                )

                if data["rain_mm"] > 0:
                    message += f" Rainfall is {data['rain_mm']} millimeters."
                else:
                    message += " There is no rain currently."

                return {
                    "success": True,
                    "message": message,
                    "spoken": message + " sir.",
                    "data": data,
                    "tool": "get_weather",
                }

            return result


        # Deterministic location commands
        location_query = command.lower().strip()

        if location_query in [
            "where am i",
            "what is my location",
            "my location",
            "current location",
            "where are we",
        ]:
            result = router.execute("get_location", {})

            if result.get("success"):
                data = result["data"]

                message = (
                    f"You are currently in {data['city']}, "
                    f"{data['region']}, {data['country']}."
                )

                return {
                    "success": True,
                    "message": message,
                    "spoken": message + " sir.",
                    "data": data,
                    "tool": "get_location",
                }

            return result

        # ---------------------------------------------------------
        # Deterministic vision / face detection commands
        # ---------------------------------------------------------
        vision_query = command.lower().strip()

        if vision_query in [
            "detect faces",
            "detect face",
            "scan my face",
            "scan faces",
            "check my face",
            "check faces",
            "look at me",
        ]:
            result = router.execute("detect_faces")

            if result.get("success"):
                data = result["data"]
                face_count = data["face_count"]

                if face_count == 0:
                    message = "I don't see any face in the camera frame."
                elif face_count == 1:
                    message = "I detected one face in the camera frame."
                else:
                    message = f"I detected {face_count} faces in the camera frame."

                return {
                    "success": True,
                    "message": message,
                    "spoken": message + " sir.",
                    "data": data,
                    "tool": "detect_faces",
                }

            return result
        
        # ---------------------------------------------------------
        # Deterministic time handling
        # ---------------------------------------------------------
        time_query = command.lower().strip()

        if time_query in [
            "what time is it",
            "what's the time",
            "what is the time",
            "current time",
            "tell me the time",
            "time now",
            "what time now"
        ]:
            current_time = datetime.now().strftime("%I:%M %p")

            response = {
                "success": True,
                "message": f"The current time is {current_time}.",
                "spoken": f"The current time is {current_time}, sir.",
                "data": {
                    "time": current_time
                },
                "tool": "get_current_time"
            }

            memory_manager.add_conversation_turn(
                "assistant",
                response["message"]
            )

            return response

        mem_response = self._handle_memory_commands(command)

        if mem_response:
            memory_manager.add_conversation_turn(
                "assistant",
                mem_response["message"]
            )
            return mem_response

        # ---------------------------------------------------------
        # 3. Retrieve relevant long-term memories
        # ---------------------------------------------------------
        relevant_memories = memory_manager.search_memory(
            command,
            limit=4
        )

        mem_lines = []

        for m in relevant_memories:
            fact_text = (
                m.get("fact")
                or f"{m.get('key')}: {m.get('value')}"
            )

            mem_lines.append(f"- {fact_text}")

        mem_context = (
            "User Memories / Preferences:\n"
            + "\n".join(mem_lines)
            if mem_lines
            else ""
        )

        # ---------------------------------------------------------
        # Recent conversation
        # ---------------------------------------------------------
        recent_history = memory_manager.get_recent_conversation(
            limit=4
        )

        conv_context = (
            "Recent Conversation:\n"
            + "\n".join(
                [
                    f"{m['role']}: {m['content']}"
                    for m in recent_history[:-1]
                ]
            )
            if recent_history
            else ""
        )

        context_parts = [
            p for p in [
                mem_context,
                conv_context
            ]
            if p
        ]

        context_str = "\n\n".join(context_parts)

        vision_query = command.lower().strip()

        if any(x in vision_query for x in [
            "look at my screen",
            "check my screen",
            "inspect my screen",
            "what is on my screen",
            "what's on my screen",
        ]):
            return router.execute("inspect_screen")

        if any(x in vision_query for x in [
            "take a picture with my webcam",
            "take a photo with my webcam",
            "take a picture using my webcam",
            "take a photo using my webcam",
            "take a webcam picture",
            "take a webcam photo",
            "capture webcam",
        ]):
            return router.execute("capture_webcam")

        coding_query = command.lower().strip()

        if any(x in coding_query for x in [
            "inspect my project",
            "inspect my project repository",
            "inspect the project",
            "inspect repository",
            "inspect my repository",
        ]):
            return router.execute("inspect_repo", ".")

        if any(x in coding_query for x in [
            "git status",
            "check my git status",
            "check git status",
            "show git status",
            "show my git status",
        ]):
            return router.execute("git_status")

        if "git diff" in coding_query:
            return router.execute("git_diff")

        if any(x in coding_query for x in [
            "git log",
            "recent commits",
            "recent git commits",
            "show recent commits",
            "show me the recent commits",
        ]):
            return router.execute("git_log", 5)

        if any(x in coding_query for x in [
            "run the tests",
            "run tests",
            "run my tests",
            "execute tests",
            "execute the tests",
            "test the project",
        ]):
            return router.execute("run_tests")

        if "git log" in coding_query or "recent commits" in coding_query:
            return router.execute("git_log", 5)

                # ---------------------------------------------------------
        # Deterministic terminal command routing
        # ---------------------------------------------------------
        terminal_query = command.strip()

        terminal_match = re.match(
            r"^(?:execute|run)\s+(?:command\s+)?(.+)$",
            terminal_query,
            flags=re.IGNORECASE
        )

        if terminal_match:
            terminal_command = terminal_match.group(1).strip()

            if terminal_command:
                return router.execute(
                    "run_command",
                    terminal_command
                )

        file_query = command.lower().strip()

        if any(x in file_query for x in [
            "list files",
            "list files in my project",
            "show files in my project",
            "show project files",
        ]):
            return router.execute("list_folder", ".")

        if any(x in file_query for x in [
            "show information about",
            "show info about",
            "file information",
            "get file info",
        ]):
            filename = command.lower()

            for known_file in ["requirements.txt", "readme.md", ".env.example"]:
                if known_file in filename:
                    return router.execute("get_file_info", known_file)

        if "search for" in file_query or "find file" in file_query:
            if "requirements.txt" in file_query:
                return router.execute(
                    "search_files",
                    ".",
                    "requirements.txt"
                )


        
                
        # ---------------------------------------------------------
        # 4. Plan and route using LLM or deterministic fallback
        # ---------------------------------------------------------
        available_tools = router.get_all_tools()

        plan = llm_service.plan_and_route(
            command,
            available_tools,
            context=context_str
        )

        tool_name = plan.get("tool_name")
        params = plan.get("parameters", {})
        direct_resp = plan.get("direct_response")

        # ---------------------------------------------------------
        # 5. Case A: Tool execution required
        # ---------------------------------------------------------
        if tool_name:
            if tool_name not in available_tools:
                spoken = f"I do not have the capability '{tool_name}' available, sir."
                resp = {
                    "success": False,
                    "message": f"Tool '{tool_name}' is not recognized or available.",
                    "spoken": spoken,
                    "data": None,
                    "tool": tool_name,
                    "error": "ToolNotFound"
                }
                memory_manager.add_conversation_turn("assistant", spoken)
                return resp

            tool_meta = available_tools[tool_name]

            # Risky tool execution check
            if (
                tool_meta.get("requires_confirmation")
                and not params.get("confirmed")
            ):
                resp = {
                    "success": False,
                    "message": (
                        f"Action requires confirmation: "
                        f"{tool_name} with {params}"
                    ),
                    "spoken": (
                        "This action requires your confirmation "
                        f"before proceeding with {tool_name}."
                    ),
                    "data": {
                        "tool": tool_name,
                        "parameters": params,
                        "needs_confirmation": True
                    },
                    "tool": tool_name,
                    "error": "ConfirmationRequired"
                }

                memory_manager.add_conversation_turn(
                    "assistant",
                    resp["spoken"]
                )

                return resp

            tool_result = router.execute(
                tool_name,
                **params
            )

            # Defensive handling in case a tool returns something
            # unexpected instead of a dictionary.
            if not isinstance(tool_result, dict):
                tool_result = {
                    "success": True,
                    "message": str(tool_result),
                    "data": tool_result,
                    "error": None
                }

            if tool_name in ["search_memory", "recall"] and isinstance(tool_result.get("data"), list):
                items = tool_result["data"]
                if items:
                    facts = [m.get("fact") or f"{m.get('key')}: {m.get('value')}" for m in items[:3]]
                    spoken = f"I found the following in memory: {'; '.join(facts)}."
                else:
                    spoken = f"I searched my memory for '{params.get('query', '')}' but found no records, sir."
                tool_result["message"] = spoken

            spoken = tool_result.get(
                "message",
                f"Completed {tool_name}."
            )

            response = {
                "success": tool_result.get("success", True),
                "message": tool_result.get("message", ""),
                "spoken": spoken,
                "data": tool_result.get("data"),
                "tool": tool_name,
                "error": tool_result.get("error")
            }

            memory_manager.add_conversation_turn(
                "assistant",
                spoken
            )

            return response

        # ---------------------------------------------------------
        # 6. Case B: Pure conversational request
        # ---------------------------------------------------------
        is_success = True
        err = None
        if direct_resp:
            spoken = direct_resp

        else:
            chat_sys = None

            if mem_context:
                chat_sys = (
                    "You are JARVIS, an advanced, highly intelligent "
                    "desktop AI operating system. "
                    "You are concise, professional, futuristic, "
                    "and helpful.\n\n"
                    f"Known facts about the user:\n{mem_context}"
                )

            if llm_service.is_available():
                spoken = llm_service.generate_chat_response(
                    prompt=command,
                    conversation_history=recent_history,
                    system_prompt=chat_sys
                )
            else:
                spoken = f"I am not sure how to handle '{command}', sir. Could you please rephrase or specify a command?"
                is_success = False
                err = "UnknownCommand"

        response = {
            "success": is_success,
            "message": spoken,
            "spoken": spoken,
            "data": None,
            "tool": None,
            "error": err
        }

        memory_manager.add_conversation_turn(
            "assistant",
            spoken
        )

        return response

    # =================================================================
    # MEMORY COMMAND HANDLER
    # =================================================================

    def _handle_memory_commands(
        self,
        command: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle direct memory storage, recall, and forgetting commands.

        IMPORTANT:
        Personal-memory questions are handled here before the LLM planner.
        This prevents questions such as "do you remember my name?"
        from being incorrectly routed to search_web.
        """

        cmd_lower = command.lower().strip()

        # Remove trailing punctuation for easier matching
        normalized = re.sub(
            r"[?.!]+$",
            "",
            cmd_lower
        ).strip()

        # =============================================================
        # 1. REMEMBER COMMANDS
        # =============================================================

        if (
            normalized.startswith("remember that ")
            or normalized.startswith("remember ")
        ):

            content = re.sub(
                r"^remember(\s+that)?\s+",
                "",
                command,
                flags=re.IGNORECASE
            ).strip()

            content = re.sub(r"[?.!]+$", "", content).strip()

            if not content:
                return {
                    "success": False,
                    "message": "No fact provided to remember.",
                    "spoken": (
                        "Please tell me what you would like "
                        "me to remember, sir."
                    ),
                    "data": None,
                    "tool": "remember",
                    "error": "EmptyFact"
                }

            # Extract key and value for structured storage
            if " is " in content:
                key, val = content.split(" is ", 1)
                fact = f"{key.strip()} is {val.strip()}"

            elif " am " in content:
                key, val = content.split(" am ", 1)
                fact = f"{key.strip()} am {val.strip()}"

            elif " are " in content:
                key, val = content.split(" are ", 1)
                fact = f"{key.strip()} are {val.strip()}"

            else:
                key = content[:40].strip()
                val = content.strip()
                fact = content.strip()

            # If storing a programming language preference, clear conflicting old language entries
            key_clean = key.strip().lower()
            if key_clean.startswith("my "):
                key_clean = key_clean[3:].strip()

            if key_clean in ["favorite language", "preferred language", "preferred programming language", "programming language"]:
                for old_key in ["my preferred programming language", "preferred programming language", "my favorite language", "favorite language"]:
                    if old_key.lower() != key.strip().lower():
                        memory_manager.delete_memory(key=old_key)

            res = memory_manager.add_memory(
                fact=fact,
                key=key.strip(),
                category="user_fact",
                importance=2
            )

            # Natural pronoun conversion for spoken confirmation
            spoken_fact = re.sub(
                r"\bmy\b",
                "your",
                content,
                flags=re.IGNORECASE
            )

            spoken_fact = re.sub(
                r"\bi\s+am\b",
                "you are",
                spoken_fact,
                flags=re.IGNORECASE
            )

            spoken_fact = re.sub(
                r"\bi\b",
                "you",
                spoken_fact
            )

            spoken = (
                f"I will remember that "
                f"{spoken_fact}, sir."
            )

            return {
                "success": True,
                "message": res["message"],
                "spoken": spoken,
                "data": res["data"],
                "tool": "remember",
                "error": None
            }

        # =============================================================
        # 2. GENERAL MEMORY LISTING
        # =============================================================

        memory_list_phrases = [
            "what do you remember",
            "what do you remember about me",
            "recall",
            "list memories",
            "my preferences",
            "what do you know about me",
            "show memories",
            "what memories do you have",
            "show my memories",
            "show what you remember",
            "what did i tell you to remember",
            "what did i tell you",
            "what have i told you to remember",
            "what have i told you",
            "tell me what you remember",
            "tell me what you know about me",
            "do you remember anything about me",
            "do you remember anything",
            "what do you have stored about me",
            "what do you have stored",
            "what do you have in memory",
            "list all memories"
        ]

        # Check if query is asking about a specific topic (e.g. 'about my name', 'about my project')
        # rather than a general listing of all memories.
        is_specific_topic = bool(
            re.search(r"\b(about|regarding)\s+my\s+\w+", normalized)
            or re.search(r"\bwhat my\s+\w+", normalized)
        )

        if not is_specific_topic and (
            any(normalized.startswith(phrase) for phrase in memory_list_phrases)
            or normalized in memory_list_phrases
        ):

            memories = router.execute(
                "list_memories",
                limit=5
            )

            if not memories:
                spoken = (
                    "I do not have any saved memories yet, sir."
                )

                return {
                    "success": True,
                    "message": "No memories stored.",
                    "spoken": spoken,
                    "data": [],
                    "tool": "recall",
                    "error": None
                }

            facts = []

            for m in memories[:5]:

                f = (
                    m.get("fact")
                    or f"{m['key']}: {m['value']}"
                )

                f_spoken = re.sub(
                    r"\bmy\b",
                    "your",
                    f,
                    flags=re.IGNORECASE
                )

                f_spoken = re.sub(
                    r"\bi\s+am\b",
                    "you are",
                    f_spoken,
                    flags=re.IGNORECASE
                )

                facts.append(f_spoken)

            summary = "; ".join(facts)

            spoken = (
                f"I remember the following: "
                f"{summary}."
            )

            return {
                "success": True,
                "message": (
                    f"Retrieved {len(memories)} memories."
                ),
                "spoken": spoken,
                "data": memories,
                "tool": "recall",
                "error": None
            }

        # =============================================================
        # 3. TARGETED NATURAL QUESTIONS ABOUT USER FACTS
        # =============================================================

        target_topic = None

        # Comprehensive pattern matching for personal memory questions
        m = (
            re.match(r"^what(?:'s| is| was)\s+my\s+(.+)$", normalized)
            or re.match(r"^what am i\s+(.+)$", normalized)
            or re.match(r"^where do i\s+(.+)$", normalized)
            or re.match(r"^tell me (?:about )?my\s+(.+)$", normalized)
            or re.match(r"^tell me what my\s+(.+?)(?:\s+is)?$", normalized)
            or re.match(r"^tell me what i am\s+(.+)$", normalized)
            or re.match(r"^do you (?:remember|know|recall) my\s+(.+)$", normalized)
            or re.match(r"^do you (?:remember|know|recall) what my\s+(.+?)(?:\s+is)?$", normalized)
            or re.match(r"^do you (?:remember|know|recall) what i am\s+(.+)$", normalized)
            or re.match(r"^can you (?:tell|remind) me (?:about )?my\s+(.+)$", normalized)
            or re.match(r"^can you (?:tell|remind) me what my\s+(.+?)(?:\s+is)?$", normalized)
            or re.match(r"^what did i (?:tell you|say) (?:about |regarding )?(?:my\s+)?(.+)$", normalized)
            or re.match(r"^what do you (?:remember|know) about (?:my\s+)?(.+)$", normalized)
            or re.match(r"^remind me (?:of |about )?(?:my\s+)?(.+)$", normalized)
        )

        if m:
            target_topic = m.group(1).strip()
        elif normalized in ("who am i", "who i am"):
            target_topic = "name"

        # -------------------------------------------------------------
        # Clean target and search
        # -------------------------------------------------------------

        if target_topic:

            # Strip trailing filler words (e.g. "again", "now", "please")
            target_topic = re.sub(
                r"\b(again|now|please|right now)\b",
                "",
                target_topic,
                flags=re.IGNORECASE
            ).strip()

            target_topic = re.sub(
                r"\s+",
                " ",
                target_topic
            ).strip()

            # Common wording normalization
            topic_aliases = {
                "full name": "name",
                "name": "name",
                "my name": "name",
                "learning": "learning",
                "studying": "learning",
                "programming language": "preferred programming language",
                "preferred language": "preferred programming language",
                "favorite language": "preferred programming language",
                "my programming language": "preferred programming language",
                "current project": "current project",
                "project": "current project",
                "my project": "current project"
            }

            search_topic = topic_aliases.get(
                target_topic.lower(),
                target_topic
            )

            # Route through router.execute so activity log reflects search_memory
            # 1. Search target_topic first
            matches = router.execute(
                "search_memory",
                query=target_topic,
                limit=3
            )

            # 2. If no match and search_topic alias is different, search search_topic
            if not matches and search_topic != target_topic:
                matches = router.execute(
                    "search_memory",
                    query=search_topic,
                    limit=3
                )

            # 3. If still nothing and target_topic starts with 'my ', try stripping it
            if not matches and target_topic.lower().startswith("my "):
                matches = router.execute(
                    "search_memory",
                    query=target_topic[3:].strip(),
                    limit=3
                )

            # 4. If still nothing and topic is language-related, try related aliases
            if not matches and search_topic in [
                "preferred programming language",
                "programming language",
                "favorite language"
            ]:
                for alias in ["favorite language", "programming language", "preferred programming language"]:
                    matches = router.execute("search_memory", query=alias, limit=3)
                    if matches:
                        break

            if matches:

                best = matches[0]

                raw_val = best.get("value", "")
                val = _clean_fact_value(raw_val, target_topic)
                fact = best.get("fact", "")

                # -----------------------------------------------------
                # Name
                # -----------------------------------------------------

                if search_topic in [
                    "name",
                    "full name"
                ]:

                    spoken = (
                        f"Your name is {val}, sir."
                    )

                # -----------------------------------------------------
                # Learning
                # -----------------------------------------------------

                elif search_topic in [
                    "learning",
                    "studying"
                ]:

                    spoken = (
                        f"You are learning {val}, sir."
                    )

                # -----------------------------------------------------
                # Current project
                # -----------------------------------------------------

                elif search_topic in [
                    "current project",
                    "project"
                ]:

                    spoken = (
                        f"Your current project is "
                        f"{val}, sir."
                    )

                # -----------------------------------------------------
                # Programming language
                # -----------------------------------------------------

                elif search_topic in [
                    "preferred programming language",
                    "programming language",
                    "favorite language",
                    "preferred language"
                ]:

                    spoken = (
                        f"Your preferred programming "
                        f"language is {val}, sir."
                    )

                # -----------------------------------------------------
                # Generic fact
                # -----------------------------------------------------

                else:

                    fact_spoken = re.sub(
                        r"\bmy\b",
                        "your",
                        fact,
                        flags=re.IGNORECASE
                    )

                    fact_spoken = re.sub(
                        r"\bi\s+am\b",
                        "you are",
                        fact_spoken,
                        flags=re.IGNORECASE
                    )

                    spoken = (
                        f"Based on my memory, "
                        f"{fact_spoken}, sir."
                    )

                return {
                    "success": True,
                    "message": (
                        f"Retrieved memory for "
                        f"'{target_topic}'."
                    ),
                    "spoken": spoken,
                    "data": best,
                    "tool": "recall",
                    "error": None
                }

            # ---------------------------------------------------------
            # No memory found
            # ---------------------------------------------------------

            spoken = (
                f"I do not have any saved memory "
                f"about your {target_topic}, sir."
            )

            return {
                "success": True,
                "message": (
                    f"No memory found matching "
                    f"'{target_topic}'."
                ),
                "spoken": spoken,
                "data": None,
                "tool": "recall",
                "error": None
            }

        # =============================================================
        # 4. FORGET COMMANDS
        # =============================================================

        if (
            normalized.startswith("forget that ")
            or normalized.startswith("forget ")
            or normalized.startswith("delete memory ")
        ):

            target = re.sub(
                r"^(forget(\s+that)?|delete\s+memory)\s+",
                "",
                command,
                flags=re.IGNORECASE
            )

            target = target.rstrip(". ").strip()

            if not target:
                return {
                    "success": False,
                    "message": "Specify what to forget.",
                    "spoken": (
                        "Please tell me what you would "
                        "like me to forget, sir."
                    ),
                    "data": None,
                    "tool": "forget",
                    "error": "MissingTarget"
                }

            # Attempt deletion by query
            res = memory_manager.delete_memory(
                query=target
            )

            if not res["success"]:

                # Try extracting leading subject/key
                for sep in [
                    " is ",
                    " am ",
                    " are "
                ]:

                    if sep in target:

                        key_part = (
                            target
                            .split(sep)[0]
                            .strip()
                        )

                        res = memory_manager.delete_memory(
                            query=key_part
                        )

                        if res["success"]:
                            break

            if res["success"]:

                spoken_target = re.sub(
                    r"\bmy\b",
                    "your",
                    target,
                    flags=re.IGNORECASE
                )

                spoken_target = re.sub(
                    r"\bi\s+am\b",
                    "you are",
                    spoken_target,
                    flags=re.IGNORECASE
                )

                if " " in target:

                    spoken = (
                        f"I have forgotten that "
                        f"{spoken_target}, sir."
                    )

                else:

                    spoken = (
                        f"I have forgotten about "
                        f"{target}, sir."
                    )

            else:

                spoken = (
                    f"I couldn't find any memory "
                    f"regarding '{target}', sir."
                )

            return {
                "success": res["success"],
                "message": res["message"],
                "spoken": spoken,
                "data": res["data"],
                "tool": "forget",
                "error": res["error"]
            }

        # =============================================================
        # No memory command matched
        # =============================================================

        return None


# =====================================================================
# GLOBAL BRAIN SINGLETON
# =====================================================================

brain = JarvisBrain()

jarvis_brain = brain