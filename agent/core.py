"""
Core AI Agent
Implements the reasoning loop for codebase research.
"""
from typing import List, Dict, Any, Tuple
from django.conf import settings
from agent.llm_client import get_llm_client
from agent.tools import AgentTools
from research_sessions.models import ResearchSession


class CodebaseResearchAgent:
    """
    AI agent that explores codebases using tool-calling and multi-step reasoning.
    """
    
    def __init__(
        self,
        session_id: int,
        repo_local_path: str,
        max_iterations: int = None
    ):
        self.session_id = session_id
        self.repo_local_path = repo_local_path
        self.max_iterations = max_iterations or settings.AGENT_MAX_ITERATIONS
        
        self.llm_client = get_llm_client()
        self.tools = AgentTools(session_id, repo_local_path)
        
        self.conversation_history = []
        self.visited_files = set()
        self.tool_call_history = []
    
    def research(self, question: str) -> str:
        """
        Main research method. Executes the agent loop.
        
        Args:
            question: The research question to answer
            
        Returns:
            Final answer as string
        """
        # Update session status
        session = ResearchSession.objects.get(id=self.session_id)
        session.mark_processing()
        
        try:
            # Initialize conversation with system prompt and question
            system_prompt = self._build_system_prompt()
            self.conversation_history = [
                {"role": "user", "content": question}
            ]
            
            # Run reasoning loop
            final_answer = self._reasoning_loop(system_prompt)
            
            # Format answer (two-stage: fix wishy-washy, then enforce format)
            formatted_answer = self._format_final_answer(final_answer)
            formatted_answer = self._ensure_format(formatted_answer)
            
            # Mark session as completed
            session.mark_completed(formatted_answer)
            
            # Refresh to get accurate total_tool_calls count from database
            session.refresh_from_db()
            
            return formatted_answer
            
        except Exception as e:
            session.mark_failed(str(e))
            raise
    
    def _reasoning_loop(self, system_prompt: str) -> str:
        """
        Execute the iterative reasoning loop.
        
        Loop:
        1. Send messages + tools to LLM
        2. LLM returns tool calls or final answer
        3. Execute tool calls
        4. Add results to conversation
        5. Repeat until done or max iterations
        """
        session = ResearchSession.objects.get(id=self.session_id)
        
        # FORCE INITIAL EXPLORATION - Don't trust LLM to do it
        # This ensures the agent ALWAYS looks at the repo first
        if not self.conversation_history or len(self.conversation_history) == 1:
            # First iteration - FORCE directory structure check
            initial_structure = self.tools.execute_tool(
                "get_directory_structure",
                {"max_depth": 2}
            )
            
            # Add forced exploration to conversation
            self.conversation_history.append({
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Let me explore the repository structure first."
                    },
                    {
                        "type": "tool_use",
                        "id": "forced_initial",
                        "name": "get_directory_structure",
                        "input": {"max_depth": 2}
                    }
                ]
            })
            
            self.conversation_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "forced_initial",
                        "content": initial_structure
                    }
                ]
            })
            
            session.increment_iteration()
        
        for iteration in range(self.max_iterations):
            self.tools.current_iteration = iteration
            session.increment_iteration()
            
            # Call LLM
            response = self.llm_client.chat_completion(
                messages=self.conversation_history,
                tools=self.tools.get_tool_definitions(),
                system=system_prompt
            )
            
            # Track token usage
            try:
                tokens = self.llm_client.count_tokens(response)
                session.add_token_usage(tokens)  # Always track, even if estimated
            except Exception:
                pass  # Skip if anything goes wrong
            
            # Check if we have tool calls
            if self.llm_client.has_tool_calls(response):
                # Execute all tool calls
                tool_calls = self.llm_client.extract_tool_calls(response)
                
                # Check for repeated tool calls (safety)
                if self._is_repeating_tools(tool_calls):
                    # Force a final answer
                    return self._force_final_answer()
                
                # Add assistant's response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.get("content", [])
                })
                
                # Execute tools and collect results
                tool_results = []
                for tool_call in tool_calls:
                    result = self.tools.execute_tool(
                        tool_call["name"],
                        tool_call["input"]
                    )
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": result
                    })
                    
                    # Track visited files
                    if tool_call["name"] == "read_file":
                        self.visited_files.add(tool_call["input"].get("file_path"))
                    
                    # Track tool call history
                    self.tool_call_history.append({
                        "iteration": iteration,
                        "tool": tool_call["name"],
                        "input": tool_call["input"]
                    })
                
                # Add tool results to conversation
                self.conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })
            
            else:
                # No tool calls - Check if this is iteration 0 or 1
                # If so, FORCE tool usage based on question keywords
                if iteration < 2:
                    forced_tool_calls = self._suggest_tools_from_question(
                        self.conversation_history[0]["content"]
                    )
                    
                    if forced_tool_calls:
                        # Force execute suggested tools
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Let me search the repository to answer your question."
                                }
                            ]
                        })
                        
                        tool_results = []
                        for tool_call in forced_tool_calls:
                            result = self.tools.execute_tool(
                                tool_call["name"],
                                tool_call["input"]
                            )
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": f"forced_{iteration}",
                                "content": result
                            })
                            
                            # Track in history
                            self.tool_call_history.append({
                                "iteration": iteration,
                                "tool": tool_call["name"],
                                "input": tool_call["input"]
                            })
                        
                        # Add tool results and continue loop
                        self.conversation_history.append({
                            "role": "user",
                            "content": tool_results
                        })
                        continue  # Go to next iteration
                
                # No tool calls - we have a final answer
                final_answer = self.llm_client.extract_text_response(response)
                
                if not final_answer.strip():
                    # Empty response, try once more
                    if iteration < self.max_iterations - 1:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.get("content", [])
                        })
                        self.conversation_history.append({
                            "role": "user",
                            "content": "Please provide your final answer based on what you've learned."
                        })
                        continue
                    else:
                        return "Unable to generate a complete answer."
                
                return final_answer
        
        # Max iterations reached
        return self._force_final_answer()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent"""
        return """You are a direct, no-nonsense code analyst. Give CLEAR, DEFINITIVE answers about code.

🚨 CRITICAL RULES:

1. You MUST explore the repository using tools FIRST
2. After exploring, answer the ACTUAL QUESTION ASKED
3. Be direct and specific - reference actual files and line numbers

**REQUIRED Answer Format for YES/NO questions:**

**Answer: YES** or **Answer: NO**
**Evidence:** [What files you checked and what you found]
**Conclusion:** [Clear statement]

**For HOW/WHAT/WHERE questions:**

**Answer:** [Direct answer to the question]
**Evidence:** [Specific files, line numbers, code snippets]
**Details:** [Additional relevant information]

**EXAMPLES:**

Question: "Is PostgreSQL used?"
**Answer: NO**
**Evidence:** Searched for "postgres", "postgresql" in all files - no matches. Checked docker-compose.yml - only Kafka services defined.
**Conclusion:** This project uses Kafka only, no database.

---

Question: "How are static files served?"
**Answer:** Static files are served using Django's STATICFILES_DIRS configuration
**Evidence:** 
- settings.py line 125: STATIC_URL = '/static/'
- settings.py line 126: STATICFILES_DIRS = [BASE_DIR / 'static']
- Found static/ directory containing css/, js/, images/
**Details:** Run `python manage.py collectstatic` to gather all static files for production.

---

Question: "Where is the authentication code?"
**Answer:** Authentication is handled in app/views.py using Django's built-in auth
**Evidence:**
- app/views.py lines 15-25: login_view() function using authenticate()
- app/views.py line 45: @login_required decorator on dashboard view
- urls.py line 8: path('login/', login_view)
**Details:** Uses session-based authentication with the default Django auth backend.

---

Question: "Is Docker configured?"
**Answer: YES**
**Evidence:** Found docker-compose.yml in root directory defining kafka (port 9092) and kafka-ui (port 8080) services.
**Conclusion:** Run `docker-compose up` to start the environment.

**IMPORTANT:**
- Answer the ACTUAL question asked (YES/NO, HOW, WHAT, WHERE, etc.)
- Don't add wrong prefixes - if asked about static files, answer about static files!
- Be specific with file names and line numbers when possible
- If you can't find something after thorough search, say so directly
- Never say "you should check" - YOU do the checking with tools!

**Tool Usage:**
- search_code(query) - Search for text in all files
- read_file(path) - Read specific files completely
- list_files(path) - List directory contents  
- get_directory_structure() - See folder tree

**Process:**
1. Use tools to search the repository thoroughly
2. Read relevant files to get details
3. Form your answer based on actual findings
4. Structure your answer clearly with evidence
"""
    
    def _suggest_tools_from_question(self, question: str) -> List[Dict[str, Any]]:
        """
        Intelligently suggest tools to use based on question keywords.
        This is a fallback when the LLM doesn't generate tool calls.
        """
        question_lower = question.lower()
        suggested_tools = []
        
        # Keywords that suggest specific searches
        search_keywords = {
            "docker": ["Dockerfile", "docker-compose"],
            "config": ["config", ".env", "settings"],
            "static": ["static", "STATIC_URL", "STATICFILES"],
            "media": ["media", "MEDIA_URL", "MEDIA_ROOT"],
            "auth": ["auth", "login", "password", "jwt", "token", "authenticate"],
            "database": ["database", "db", "sql", "postgres", "mysql", "sqlite"],
            "postgres": ["postgres", "postgresql", "psycopg2"],
            "sqlite": ["sqlite", "sqlite3"],
            "api": ["api", "endpoint", "route", "view"],
            "test": ["test", "spec", ".test."],
            "main": ["main", "app", "index", "server"],
            "template": ["template", "html", "jinja"],
        }
        
        # Check if question contains any of these keywords
        for keyword, search_terms in search_keywords.items():
            if keyword in question_lower:
                for term in search_terms:
                    suggested_tools.append({
                        "name": "search_code",
                        "input": {"query": term}
                    })
                # Only use first matching category, but get all its terms
                break
        
        # If no specific keyword, do a general structure check
        if not suggested_tools:
            # Check if question is asking "is there", "does it have", etc.
            if any(phrase in question_lower for phrase in ["is there", "does it have", "any ", "find ", "used", "how", "where", "what"]):
                # Do a directory structure check
                suggested_tools.append({
                    "name": "get_directory_structure",
                    "input": {"max_depth": 3}
                })
        
        return suggested_tools[:3]  # Limit to 3 tools
    
    def _format_final_answer(self, raw_answer: str) -> str:
        """
        Format the final answer to be more direct if it's too wishy-washy.
        Only add structure if the answer doesn't already have it AND we're confident.
        """
        # If answer already has the required format, return as-is
        if "**Answer:" in raw_answer and "**Evidence:" in raw_answer:
            return raw_answer
        
        # Check if answer is wishy-washy AND we can confidently restructure it
        wishy_washy_phrases = [
            "it seems", "might be", "it appears", "likely that",
            "to confirm", "you should check", "based on the information",
            "there is no indication"
        ]
        
        is_wishy_washy = any(phrase in raw_answer.lower() for phrase in wishy_washy_phrases)
        
        # Only add structure if answer is truly wishy-washy AND we're confident about the domain
        if is_wishy_washy:
            raw_lower = raw_answer.lower()
            question_in_history = self.conversation_history[0]["content"].lower()
            
            # Only restructure if question matches the topic AND answer suggests clear YES/NO
            if "postgres" in question_in_history or "sqlite" in question_in_history or "database" in question_in_history:
                if "not" in raw_lower or "no database" in raw_lower or "not use" in raw_lower:
                    return f"**Answer: NO** (Database not found)\n\n{raw_answer}"
                elif "uses" in raw_lower or "configured" in raw_lower:
                    return f"**Answer: YES** (Database found)\n\n{raw_answer}"
            
            if "docker" in question_in_history:
                if "found" in raw_lower or "configured" in raw_lower or "docker-compose" in raw_lower:
                    return f"**Answer: YES** (Docker is configured)\n\n{raw_answer}"
                elif "not" in raw_lower or "no docker" in raw_lower:
                    return f"**Answer: NO** (Docker not found)\n\n{raw_answer}"
        
        # If we can't confidently restructure, return as-is
        # This prevents adding wrong prefixes to unrelated questions
        return raw_answer
    
    def _ensure_format(self, answer: str) -> str:
        """
        Enforce the structured format on any answer.
        Extracts key information and restructures it cleanly.
        """
        # If already has our format markers, return as-is
        if "**Answer:**" in answer and "**Evidence:**" in answer:
            return answer
        
        # If it has partial format from _format_final_answer, return as-is
        if answer.startswith("**Answer:"):
            return answer
        
        # Get the original question for context
        question = self.conversation_history[0]["content"].lower() if self.conversation_history else ""
        
        # Detect question type MORE CAREFULLY
        is_yes_no = (
            question.startswith("is ") or 
            question.startswith("does ") or 
            question.startswith("do ") or 
            question.startswith("are ") or 
            question.startswith("can ") or 
            question.startswith("has ") or
            question.startswith("did ")
        )
        is_how = question.startswith("how")
        
        # Clean the answer
        lines = [line.strip() for line in answer.split('\n') if line.strip()]
        if not lines:
            return answer
        
        # Remove numbered list markers if they exist
        cleaned_lines = []
        for line in lines:
            # Remove "1. ", "2. ", etc. from start
            import re
            line = re.sub(r'^\d+\.\s*', '', line)
            # Remove "- " from start if it's just formatting
            if not line.startswith('- **') and not line.startswith('- In'):
                line = re.sub(r'^-\s*', '', line)
            cleaned_lines.append(line)
        
        # Get first substantial sentence
        first_sentence = cleaned_lines[0] if cleaned_lines else answer[:200]
        
        # Clean verbose starts
        verbose_starts = [
            "based on the provided information, ",
            "based on the information provided, ",
            "based on the information, ",
            "it appears that ",
            "it seems that ",
            "here are the key points:",
            "to summarize,",
        ]
        for start in verbose_starts:
            if first_sentence.lower().startswith(start):
                first_sentence = first_sentence[len(start):].strip()
                if first_sentence:
                    first_sentence = first_sentence[0].upper() + first_sentence[1:]
        
        # Build clean formatted response
        formatted = ""
        
        if is_yes_no:
            # YES/NO question
            answer_lower = answer.lower()
            if "is not" in answer_lower or "not included" in answer_lower or "does not" in answer_lower:
                formatted = "**Answer: NO**\n\n"
            elif "yes" in answer_lower[:50] or "configured" in answer_lower[:100]:
                formatted = "**Answer: YES**\n\n"
            else:
                formatted = f"**Answer:** {first_sentence}\n\n"
        elif is_how:
            # HOW question - extract the mechanism
            formatted = f"**Answer:** {first_sentence}\n\n"
        else:
            # Other questions
            formatted = f"**Answer:** {first_sentence}\n\n"
        
        # Extract file references
        file_mentions = []
        for line in cleaned_lines:
            # Look for lines mentioning files or code
            if any(indicator in line.lower() for indicator in ['settings.py', '.py', 'auth_user', 'database', 'table', 'column']):
                # Skip if it's a repeat of first sentence
                if line != first_sentence:
                    file_mentions.append(line)
        
        # Add evidence
        if file_mentions:
            formatted += "**Evidence:**\n"
            # Take first 3-4 unique mentions
            seen = set()
            for mention in file_mentions[:4]:
                if mention.lower() not in seen:
                    formatted += f"- {mention}\n"
                    seen.add(mention.lower())
            formatted += "\n"
        else:
            formatted += "**Evidence:** Based on repository exploration\n\n"
        
        # Add conclusion (last sentence or summary)
        if len(cleaned_lines) > 3:
            # Find summary or conclusion
            for line in reversed(cleaned_lines[-3:]):
                if any(word in line.lower() for word in ['summary', 'conclude', 'overall']):
                    formatted += f"**Summary:** {line}\n"
                    break
        
        return formatted.strip()
        """
        Enforce the structured format on any answer.
        Extracts key information and restructures it cleanly.
        """
        # If already has our format markers, return as-is
        if "**Answer:**" in answer and "**Evidence:**" in answer:
            return answer
        
        # If it has partial format from _format_final_answer, return as-is
        if answer.startswith("**Answer:"):
            return answer
        
        # Otherwise, extract and restructure
        lines = [line.strip() for line in answer.split('\n') if line.strip()]
        
        if not lines:
            return answer
        
        # Get the original question for context
        question = self.conversation_history[0]["content"].lower() if self.conversation_history else ""
        
        # Detect question type MORE CAREFULLY
        # Only treat as yes/no if it starts with these exact patterns
        is_yes_no = (
            question.startswith("is ") or 
            question.startswith("does ") or 
            question.startswith("do ") or 
            question.startswith("are ") or 
            question.startswith("can ") or 
            question.startswith("has ") or
            question.startswith("did ")
        )
        is_how = question.startswith("how")
        is_what = question.startswith("what")
        is_where = question.startswith("where")
        is_why = question.startswith("why")
        
        # Extract first meaningful sentence as direct answer
        first_sentence = lines[0]
        
        # Clean up common verbose starts
        verbose_starts = [
            "based on the information provided, ",
            "based on the information, ",
            "it appears that ",
            "it seems that ",
        ]
        for start in verbose_starts:
            if first_sentence.lower().startswith(start):
                first_sentence = first_sentence[len(start):]
                first_sentence = first_sentence[0].upper() + first_sentence[1:]
        
        # Build formatted response based on question type
        if is_yes_no:
            # Try to detect yes/no from content
            answer_lower = answer.lower()
            if "is not" in answer_lower or "not included" in answer_lower or "does not" in answer_lower:
                direct_answer = "NO"
            elif "yes" in answer_lower[:50] or "is configured" in answer_lower or "found" in answer_lower[:100]:
                direct_answer = "YES"
            else:
                # Can't determine, use first sentence
                direct_answer = first_sentence[:150]
            
            formatted = f"**Answer: {direct_answer}**\n\n"
        elif is_how or is_what or is_where or is_why:
            # HOW/WHAT/WHERE/WHY questions - use descriptive answer
            formatted = f"**Answer:** {first_sentence}\n\n"
        else:
            # General question
            formatted = f"**Answer:** {first_sentence}\n\n"
        
        # Add evidence section
        formatted += f"**Evidence:**\n"
        
        # Look for file references in the answer
        file_refs = []
        for line in lines:
            if any(ext in line.lower() for ext in ['.py', '.yml', '.yaml', '.json', '.env', '.txt', 'settings', 'config']):
                file_refs.append(f"- {line}")
        
        if file_refs:
            formatted += "\n".join(file_refs[:5])  # Max 5 file references
            formatted += "\n\n"
        else:
            formatted += "Based on repository exploration\n\n"
        
        # Add details section with rest of answer
        remaining_content = "\n".join(lines[1:]) if len(lines) > 1 else ""
        if remaining_content:
            formatted += f"**Details:**\n{remaining_content}"
        
        return formatted
    
    def _is_repeating_tools(self, tool_calls: List[Dict[str, Any]]) -> bool:
        """
        Check if agent is repeating the same tool calls.
        Safety mechanism to prevent infinite loops.
        """
        if len(self.tool_call_history) < 3:
            return False
        
        # Get last 3 tool calls
        recent = self.tool_call_history[-3:]
        
        # Check if current call matches any recent call
        for tool_call in tool_calls:
            for recent_call in recent:
                if (tool_call["name"] == recent_call["tool"] and 
                    tool_call["input"] == recent_call["input"]):
                    return True
        
        return False
    
    def _force_final_answer(self) -> str:
        """
        Force the agent to provide a final answer based on what it's learned.
        Called when max iterations reached or repeated tool calls detected.
        """
        # Ask for a summary of findings
        self.conversation_history.append({
            "role": "user",
            "content": "You've reached the exploration limit. Please provide your best answer based on what you've learned so far. Structure your answer clearly with evidence from the files you explored."
        })
        
        response = self.llm_client.chat_completion(
            messages=self.conversation_history,
            system=self._build_system_prompt()
        )
        
        return self.llm_client.extract_text_response(response)