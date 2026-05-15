"""
LLM Client wrapper for Ollama API.
Handles all interactions with the local Ollama language model.
"""
import json
import requests
import re
from typing import List, Dict, Any, Optional
from django.conf import settings


class LLMClient:
    """
    Wrapper for Ollama LLM API interactions.
    Supports function/tool calling for agent workflows via JSON format.
    """
    
    def __init__(self):
        self.api_url = settings.LLM_API_URL
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions for function calling
            system: Optional system prompt
            
        Returns:
            API response dict (formatted to match expected interface)
        """
        # Transform messages to Ollama-compatible format
        transformed_messages = self._transform_messages(messages)
        
        # Format system prompt with tools
        full_system = system or ""
        if tools:
            full_system += self._format_tools_for_prompt(tools)
        
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": self.model,
            "messages": transformed_messages,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens,
            }
        }
        
        if full_system:
            payload["system"] = full_system
        
        try:
            response = requests.post(
                f"{self.api_url}/api/chat",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            
            # Transform Ollama response to match Claude format
            return self._transform_response(data)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama API request failed: {str(e)}")
    
    def _transform_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform messages from Claude API format to Ollama format.
        Converts tool results and complex content structures to simple strings.
        """
        transformed = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # If content is a list (tool results or content blocks)
            if isinstance(content, list):
                # Convert list of content blocks to a single string
                content_str = ""
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            content_str += block.get("text", "") + "\n"
                        elif block.get("type") == "tool_use":
                            # Skip tool_use blocks in transformation
                            pass
                        elif block.get("type") == "tool_result":
                            # Convert tool_result to simple text
                            content_str += f"Tool {block.get('tool_use_id')} result: {block.get('content', '')}\n"
                    else:
                        content_str += str(block) + "\n"
                
                transformed.append({
                    "role": role,
                    "content": content_str.strip() or "..."
                })
            else:
                # Simple string content
                transformed.append({
                    "role": role,
                    "content": str(content) if content else "..."
                })
        
        return transformed
    
    def _format_tools_for_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """
        Format tools for Ollama with VERY clear instructions.
        """
        tools_desc = "\n"
        for tool in tools:
            tools_desc += f"\n### {tool['name']}\n"
            tools_desc += f"**Description:** {tool.get('description', '')}\n"
            
            # Add parameters
            schema = tool.get('input_schema', {})
            props = schema.get('properties', {})
            required = schema.get('required', [])
            
            if props:
                tools_desc += "**Parameters:**\n"
                for param, details in props.items():
                    req_label = " (REQUIRED)" if param in required else " (optional)"
                    tools_desc += f"  - {param}{req_label}: {details.get('description', '')}\n"
            tools_desc += "\n"
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️  AVAILABLE TOOLS - YOU MUST USE THESE TO EXPLORE THE REPO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{tools_desc}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 HOW TO CALL A TOOL - FOLLOW THIS FORMAT EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When you want to use a tool, respond with JSON in a code block:

```json
{{"tool": "tool_name_here", "args": {{"parameter": "value"}}}}
```

🔥 EXAMPLES OF CORRECT TOOL CALLS:

Example 1 - Search for Docker files:
```json
{{"tool": "search_code", "args": {{"query": "Dockerfile"}}}}
```

Example 2 - Read a specific file:
```json
{{"tool": "read_file", "args": {{"file_path": "src/main.py"}}}}
```

Example 3 - List all files:
```json
{{"tool": "list_files", "args": {{"path": ""}}}}
```

Example 4 - Get directory tree:
```json
{{"tool": "get_directory_structure", "args": {{}}}}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  CRITICAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ALWAYS use tools BEFORE answering any question
2. Put JSON tool calls inside ```json code blocks
3. Use exact tool names from the list above
4. One tool call per code block
5. You can make multiple tool calls - just use multiple code blocks

When you're ready to give the final answer (after using tools), 
respond with regular text WITHOUT any JSON code blocks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    def _transform_response(self, ollama_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Ollama response to match Claude API format.
        """
        message = ollama_response.get("message", {})
        content_text = message.get("content", "")
        
        # Try to parse tool calls from response
        tool_calls = self._extract_tool_calls_from_text(content_text)
        
        # Build content array
        content = []
        if tool_calls:
            # Remove tool calls from text to get clean reasoning text
            import re
            text_without_tools = re.sub(r'```json\s*\n\{[^}]*\}\s*\n```', '', content_text).strip()
            
            if text_without_tools:
                content.append({
                    "type": "text",
                    "text": text_without_tools
                })
            
            # Add tool calls
            for tool_call in tool_calls:
                content.append({
                    "type": "tool_use",
                    "id": tool_call.get("id", "tool_0"),
                    "name": tool_call.get("name"),
                    "input": tool_call.get("input", {})
                })
        else:
            # No tool calls - just add the text response
            content.append({
                "type": "text",
                "text": content_text
            })
        
        return {
            "content": content,
            "stop_reason": "tool_use" if tool_calls else "end_turn",
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0
            }
        }
    
    def _extract_tool_calls_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from JSON code blocks or parse natural language.
        Falls back to inferring tool calls from model's natural language response.
        """
        tool_calls = []
        
        # First try: JSON code blocks
        json_blocks = re.findall(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        
        for block in json_blocks:
            try:
                parsed = json.loads(block.strip())
                
                if "tool" in parsed:
                    tool_calls.append({
                        "id": f"tool_{len(tool_calls)}",
                        "name": parsed["tool"],
                        "input": parsed.get("args", {})
                    })
                elif "name" in parsed:
                    tool_calls.append({
                        "id": f"tool_{len(tool_calls)}",
                        "name": parsed["name"],
                        "input": parsed.get("input", {})
                    })
            except (json.JSONDecodeError, ValueError):
                continue
        
        # Fallback: try to infer tools from natural language
        if not tool_calls:
            tool_calls = self._infer_tool_calls_from_language(text)
        
        return tool_calls
    
    def _infer_tool_calls_from_language(self, text: str) -> List[Dict[str, Any]]:
        """
        Try to infer tool calls from natural language text.
        Only infer if the model's response isn't explicitly refusing or explaining.
        """
        tool_calls = []
        lower_text = text.lower()
        
        # Don't infer if model is saying it can't do something
        reject_phrases = [
            "don't have access",
            "cannot access",
            "don't have",
            "i cannot",
            "i am unable",
            "unable to",
            "i'm sorry",
            "i cannot help",
            "i don't",
            "you can use"  # Model is explaining how to do it manually
        ]
        
        if any(phrase in lower_text for phrase in reject_phrases):
            return []
        
        # Only infer from first 200 chars to avoid parsing model's long explanations
        text_to_analyze = text[:300]
        lower_text = text_to_analyze.lower()
        
        patterns = [
            {
                "keywords": ["list", "directory"],
                "tool": "list_files",
                "extract_args": lambda t: {"path": self._extract_path_from_text(t)}
            },
            {
                "keywords": ["read", "file"],
                "tool": "read_file",
                "extract_args": lambda t: {"file_path": self._extract_path_from_text(t, is_file=True)}
            },
            {
                "keywords": ["search", "find", "grep"],
                "tool": "search_code",
                "extract_args": lambda t: {"query": self._extract_query_from_text(t)}
            }
        ]
        
        for pattern in patterns:
            if any(keyword in lower_text for keyword in pattern["keywords"]):
                try:
                    args = pattern["extract_args"](text_to_analyze)
                    # Only add if we have meaningful args
                    if not args or any(v for v in args.values()):
                        tool_calls.append({
                            "id": f"tool_{len(tool_calls)}",
                            "name": pattern["tool"],
                            "input": args
                        })
                        break  # Only one tool per response
                except Exception:
                    continue
        
        return tool_calls
    
    def _extract_path_from_text(self, text: str, is_file: bool = False) -> str:
        """Extract a file/directory path from text."""
        # Look for quoted strings first (most reliable)
        quoted = re.search(r"['\"]([^'\"]*\.[a-z]+)['\"]", text)
        if quoted:
            return quoted.group(1)
        
        quoted_generic = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted_generic:
            return quoted_generic.group(1)
        
        # Look for backtick quoted
        backtick = re.search(r"`([^`]+)`", text)
        if backtick:
            return backtick.group(1)
        
        # Look for explicit paths after "in", "from", "of"
        path_match = re.search(r'(?:in|from|of|directory)\s+(?:the\s+)?["\']?([^\s,\."\'\)]+)["\']?', text, re.IGNORECASE)
        if path_match:
            candidate = path_match.group(1)
            # Avoid false positives like "of the"
            if len(candidate) > 1 and candidate not in ["the", "and"]:
                return candidate
        
        return ""
    
    def _extract_query_from_text(self, text: str) -> str:
        """Extract a search query from text."""
        # Look for quoted strings first
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            return quoted.group(1)
        
        # Look for "for X" or "search X" patterns
        search_match = re.search(r'(?:search|find|look)\s+(?:for\s+)?(?:the\s+)?([^,\.]+?)(?:\s+in|,|\.|\s+$)', text, re.IGNORECASE)
        if search_match:
            return search_match.group(1).strip()
        
        return ""
    
    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from LLM response.
        
        Returns:
            List of tool call dicts with 'name' and 'input'
        """
        tool_calls = []
        content = response.get("content", [])
        
        for block in content:
            if block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input", {})
                })
        
        return tool_calls
    
    def extract_text_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from LLM response.
        """
        content = response.get("content", [])
        
        text_parts = []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        
        return "\n".join(text_parts)
    
    def has_tool_calls(self, response: Dict[str, Any]) -> bool:
        """
        Check if response contains tool calls.
        """
        content = response.get("content", [])
        return any(block.get("type") == "tool_use" for block in content)
    
    def get_stop_reason(self, response: Dict[str, Any]) -> str:
        """
        Get the stop reason from response.
        """
        return response.get("stop_reason", "unknown")
    
    def count_tokens(self, response: Dict[str, Any]) -> int:
        """
        Count tokens used in the response.
        Ollama doesn't provide token counts, so we estimate based on response length.
        Rough approximation: ~1 token per 4 characters.
        """
        usage = response.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        # If we got actual token counts, use them
        if input_tokens > 0 or output_tokens > 0:
            return input_tokens + output_tokens
        
        # For Ollama: estimate tokens from response content length
        # Rough approximation: ~1 token per 4 characters
        content = response.get("content", [])
        total_length = 0
        
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    total_length += len(block.get("text", ""))
        
        # Estimate: 1 token per 4 characters
        estimated_tokens = max(1, total_length // 4)
        return estimated_tokens


# Singleton instance
_llm_client = None

def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
