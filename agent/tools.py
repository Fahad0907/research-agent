"""
Agent Tools System
Defines all tools available to the AI agent for code exploration and database interaction.
"""
import json
import time
from typing import Dict, Any, List, Optional
from django.utils import timezone
from agent.repo_loader import get_repo_loader
from research_sessions.models import ToolCall, Finding


class AgentTools:
    """
    Collection of tools that the agent can use to explore code and interact with DB.
    """
    
    def __init__(self, session_id: int, repo_local_path: str):
        self.session_id = session_id
        self.repo_local_path = repo_local_path
        self.repo_loader = get_repo_loader()
        self.current_iteration = 0
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Return tool definitions in Anthropic's tool format.
        These are sent to the LLM so it knows what tools are available.
        """
        return [
            {
                "name": "list_files",
                "description": "List files in a directory of the repository. Use this to explore the codebase structure.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path in the repository (empty string for root)"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum depth to traverse (default: 3)",
                            "default": 3
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "read_file",
                "description": "Read the contents of a specific file. Returns the full file content.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative path to the file"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "search_code",
                "description": "Search for a text pattern across all repository files. Returns matching lines with file names and line numbers.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Text pattern to search for"
                        },
                        "file_extensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of file extensions to search (e.g., ['.py', '.js'])"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_directory_structure",
                "description": "Get a tree-like view of the repository structure. Useful for understanding the project layout.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum depth to show (default: 3)",
                            "default": 3
                        }
                    }
                }
            },
            {
                "name": "save_finding",
                "description": "Save an important finding or insight about the code. Use this to record what you've learned.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the relevant file"
                        },
                        "note": {
                            "type": "string",
                            "description": "Your insight or observation about this code"
                        },
                        "line_start": {
                            "type": "integer",
                            "description": "Optional starting line number"
                        },
                        "line_end": {
                            "type": "integer",
                            "description": "Optional ending line number"
                        }
                    },
                    "required": ["file_path", "note"]
                }
            },
            {
                "name": "get_previous_findings",
                "description": "Retrieve findings from previous research sessions on this repository. Useful to avoid repeating work.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of findings to retrieve (default: 10)",
                            "default": 10
                        }
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a tool and log it to the database.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            
        Returns:
            Tool output as string
        """
        start_time = time.time()
        
        try:
            # Execute the tool
            if tool_name == "list_files":
                output = self._list_files(**tool_input)
            elif tool_name == "read_file":
                output = self._read_file(**tool_input)
            elif tool_name == "search_code":
                output = self._search_code(**tool_input)
            elif tool_name == "get_directory_structure":
                output = self._get_directory_structure(**tool_input)
            elif tool_name == "save_finding":
                output = self._save_finding(**tool_input)
            elif tool_name == "get_previous_findings":
                output = self._get_previous_findings(**tool_input)
            else:
                output = f"Error: Unknown tool '{tool_name}'"
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Log to database
            ToolCall.objects.create(
                session_id=self.session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=output[:5000],  # Truncate long outputs
                iteration=self.current_iteration,
                execution_time_ms=execution_time
            )
            
            return output
            
        except Exception as e:
            error_output = f"Error executing {tool_name}: {str(e)}"
            
            # Log error to database
            ToolCall.objects.create(
                session_id=self.session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=error_output,
                iteration=self.current_iteration,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
            return error_output
    
    # ==================== Tool Implementations ====================
    
    def _list_files(self, path: str = "", max_depth: int = 3) -> str:
        """List files in a directory"""
        files = self.repo_loader.list_files(
            self.repo_local_path,
            relative_path=path,
            max_depth=max_depth
        )
        
        if not files:
            return f"No files found in path: {path or 'root'}"
        
        # Group by directory for better readability
        result = f"Found {len(files)} files in '{path or 'root'}':\n\n"
        result += "\n".join(sorted(files)[:100])  # Limit to 100 files
        
        if len(files) > 100:
            result += f"\n\n... and {len(files) - 100} more files"
        
        return result
    
    def _read_file(self, file_path: str) -> str:
        """Read a file's contents"""
        try:
            content = self.repo_loader.read_file(
                self.repo_local_path,
                file_path
            )
            
            lines = content.split('\n')
            numbered_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            
            return f"File: {file_path}\n{'='*60}\n" + "\n".join(numbered_lines)
            
        except FileNotFoundError:
            return f"File not found: {file_path}"
        except ValueError as e:
            return str(e)
    
    def _search_code(
        self,
        query: str,
        file_extensions: Optional[List[str]] = None
    ) -> str:
        """Search for code patterns"""
        results = self.repo_loader.search_in_files(
            self.repo_local_path,
            query,
            file_extensions=file_extensions,
            max_results=30
        )
        
        if not results:
            return f"No matches found for: {query}"
        
        output = f"Found {len(results)} matches for '{query}':\n\n"
        
        # Group by file
        by_file = {}
        for r in results:
            file = r['file']
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(r)
        
        for file, matches in list(by_file.items())[:10]:  # Limit to 10 files
            output += f"\n{file}:\n"
            for match in matches[:5]:  # Limit to 5 matches per file
                output += f"  Line {match['line_number']}: {match['line_content']}\n"
        
        return output
    
    def _get_directory_structure(self, max_depth: int = 3) -> str:
        """Get directory tree structure"""
        return self.repo_loader.get_directory_structure(
            self.repo_local_path,
            max_depth=max_depth
        )
    
    def _save_finding(
        self,
        file_path: str,
        note: str,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None
    ) -> str:
        """Save a finding to the database"""
        Finding.objects.create(
            session_id=self.session_id,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            note=note,
            relevance_score=0.8  # Could be improved with relevance scoring
        )
        
        return f"✓ Finding saved for {file_path}"
    
    def _get_previous_findings(self, limit: int = 10) -> str:
        """Get previous findings from other sessions on this repo"""
        from research_sessions.models import ResearchSession
        
        # Get current session to find repository
        current_session = ResearchSession.objects.get(id=self.session_id)
        
        # Get other completed sessions on same repo
        previous_sessions = ResearchSession.objects.filter(
            repository=current_session.repository,
            status='completed'
        ).exclude(
            id=self.session_id
        ).order_by('-created_at')[:5]
        
        if not previous_sessions:
            return "No previous research sessions found for this repository."
        
        output = f"Found {previous_sessions.count()} previous research sessions:\n\n"
        
        for session in previous_sessions:
            output += f"\n{'='*60}\n"
            output += f"Question: {session.question}\n"
            output += f"Date: {session.created_at.strftime('%Y-%m-%d')}\n"
            
            # Get top findings
            findings = session.findings.all()[:3]
            if findings:
                output += "\nKey Findings:\n"
                for finding in findings:
                    output += f"  • {finding.file_path}: {finding.note[:100]}...\n"
        
        return output
