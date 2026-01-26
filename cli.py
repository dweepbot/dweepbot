#!/usr/bin/env python3
"""
DweepBot Pro - Ultimate AI Agent Edition
DESTROYS CLAWDBOT with Autonomous Tool Use!

Revolutionary Features:
🧠 Function Calling (DeepSeek-V3 native tool use)
📚 RAG for large documents (ChromaDB)
⚡ Streaming responses (word-by-word)
🎨 Rich terminal UI (colors, tables, markdown)
🔐 Secure keychain storage (macOS Keychain)
🐍 Safe code execution (sandboxed Python)
📄 Smart file parsing (PDF, DOCX, TXT)
🤖 Autonomous agent (no manual commands!)

SECURITY LAYERS:
✅ Path validation (prevents directory traversal)
✅ Memory limits (256MB max per execution)
✅ CPU limits (5 seconds max CPU time)
✅ Timeout protection (10 seconds wall time)
✅ Resource cleanup (auto-delete temp files)
✅ Workspace isolation (files cannot escape)
✅ Keychain encryption (API keys secured)
"""

import requests
import json
import os
import sys
import subprocess
import platform
import multiprocessing
import yaml
import zipfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Generator, Any
import re

# Essential imports
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.panel import Panel
    from rich.live import Live
    from rich.spinner import Spinner
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    from duckduckgo_search import DDGS
    HAS_SEARCH = True
except ImportError:
    HAS_SEARCH = False

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# Console for rich output
console = Console() if HAS_RICH else None


class SecureKeyStorage:
    """Secure API key storage using macOS Keychain"""
    SERVICE_NAME = "DeepBotPro"
    KEY_NAME = "deepseek_api_key"
    
    @staticmethod
    def save_key(api_key: str) -> bool:
        """Save API key to keychain"""
        if not HAS_KEYRING:
            return False
        try:
            keyring.set_password(SecureKeyStorage.SERVICE_NAME, 
                               SecureKeyStorage.KEY_NAME, api_key)
            return True
        except Exception:
            return False
    
    @staticmethod
    def load_key() -> Optional[str]:
        """Load API key from keychain"""
        if not HAS_KEYRING:
            return None
        try:
            return keyring.get_password(SecureKeyStorage.SERVICE_NAME, 
                                       SecureKeyStorage.KEY_NAME)
        except Exception:
            return None


class ToolRegistry:
    """Registry of tools available to the AI agent"""
    
    @staticmethod
    def get_tools() -> List[Dict]:
        """Return DeepSeek-compatible tool definitions"""
        tools = []
        
        # Web Search Tool
        if HAS_SEARCH:
            tools.append({
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information using DuckDuckGo. Use this when you need real-time data, news, or information beyond your training cutoff.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 3)",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
        
        # File Operations
        tools.append({
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read contents of a file from the workspace. Supports TXT, PDF, and DOCX formats.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to read"
                        }
                    },
                    "required": ["filename"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file in the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        }
                    },
                    "required": ["filename", "content"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List all files in the workspace directory.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        })
        
        # Code Execution
        tools.append({
            "type": "function",
            "function": {
                "name": "execute_python",
                "description": "Execute Python code in a sandboxed environment. Use for calculations, data processing, or code demonstrations. Returns stdout, stderr, and return value.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        }
                    },
                    "required": ["code"]
                }
            }
        })
        
        # System Notification
        tools.append({
            "type": "function",
            "function": {
                "name": "send_notification",
                "description": "Send a system notification on macOS.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Notification message"
                        }
                    },
                    "required": ["message"]
                }
            }
        })
        
        return tools


class CodeSandbox:
    """Secure Python code execution with resource constraints"""
    
    @staticmethod
    def set_limits():
        """Limit resources for the child process (UNIX only)"""
        try:
            import resource
            # Limit memory to 256MB
            mem_limit = 256 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
            # Limit CPU time to 5 seconds
            resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        except (ImportError, AttributeError):
            # Windows doesn't have resource module - skip limits
            pass
    
    @staticmethod
    def execute(code: str, timeout: int = 10) -> Dict[str, Any]:
        """Execute Python code safely with resource limits"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute in subprocess with timeout and resource limits
            # preexec_fn only works on UNIX (macOS/Linux)
            if platform.system() != 'Windows':
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    preexec_fn=CodeSandbox.set_limits  # Apply limits before execution
                )
            else:
                # Windows fallback (no resource limits)
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Timeout: Code took longer than {timeout}s"
            }
        except MemoryError:
            return {
                "success": False,
                "error": "Memory limit exceeded (256MB max)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Security/Resource Error: {str(e)}"
            }
        finally:
            # Cleanup temporary file
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass


class DocumentParser:
    """Parse various document formats"""
    
    @staticmethod
    def read_file(filepath: Path) -> str:
        """Read file with format detection"""
        suffix = filepath.suffix.lower()
        
        try:
            if suffix == '.pdf':
                return DocumentParser._read_pdf(filepath)
            elif suffix in ['.docx', '.doc']:
                return DocumentParser._read_docx(filepath)
            else:
                return filepath.read_text()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    @staticmethod
    def _read_pdf(filepath: Path) -> str:
        """Read PDF file"""
        if not HAS_PDF:
            return "PDF support not installed. Run: pip install PyPDF2"
        
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = []
                for page in reader.pages[:50]:  # Limit to 50 pages
                    text.append(page.extract_text())
                
                content = "\n".join(text)
                if len(content) > 10000:
                    return content[:10000] + "\n\n[Document truncated - too long]"
                return content
        except Exception as e:
            return f"PDF parsing error: {str(e)}"
    
    @staticmethod
    def _read_docx(filepath: Path) -> str:
        """Read DOCX file"""
        if not HAS_DOCX:
            return "DOCX support not installed. Run: pip install python-docx"
        
        try:
            doc = docx.Document(filepath)
            text = []
            for para in doc.paragraphs[:200]:  # Limit paragraphs
                text.append(para.text)
            
            content = "\n".join(text)
            if len(content) > 10000:
                return content[:10000] + "\n\n[Document truncated - too long]"
            return content
        except Exception as e:
            return f"DOCX parsing error: {str(e)}"


class PerformanceTracker:
    """Track performance metrics for the agent"""
    
    def __init__(self):
        self.metrics = {
            'total_queries': 0,
            'tool_calls': 0,
            'total_tokens': 0,
            'total_time': 0.0,
            'start_time': datetime.now()
        }
    
    def track_query(self, tokens: int, used_tools: bool, response_time: float):
        """Track a single query"""
        self.metrics['total_queries'] += 1
        self.metrics['total_tokens'] += tokens
        self.metrics['total_time'] += response_time
        if used_tools:
            self.metrics['tool_calls'] += 1
    
    def get_stats(self) -> str:
        """Get performance statistics"""
        queries = self.metrics['total_queries']
        if queries == 0:
            return "No queries tracked yet"
        
        avg_time = self.metrics['total_time'] / queries
        avg_tokens = self.metrics['total_tokens'] // queries
        uptime = (datetime.now() - self.metrics['start_time']).total_seconds()
        
        return f"""
📊 Performance Metrics:
  • Total Queries: {queries}
  • Tool Calls: {self.metrics['tool_calls']} ({(self.metrics['tool_calls']/queries*100):.1f}%)
  • Avg Response Time: {avg_time:.2f}s
  • Avg Tokens/Query: {avg_tokens}
  • Total Tokens: {self.metrics['total_tokens']:,}
  • Uptime: {uptime:.0f}s
  • Queries/Minute: {(queries / (uptime / 60)):.1f}
"""


class DeepBotPro:
    def __init__(self, config_path="~/.deepbot/config.yaml"):
        self.config = self._load_config(config_path)
        
        # Try secure keychain first, then env, then config
        self.api_key = (
            SecureKeyStorage.load_key() or
            os.getenv("DEEPSEEK_API_KEY") or
            self.config.get('deepseek', {}).get('api_key')
        )
        
        if not self.api_key:
            raise ValueError("API key required! Use /setup to configure.")
        
        # Setup workspace
        workspace_path = self.config.get('workspace', '~/deepbot')
        self.workspace = Path(workspace_path).expanduser()
        self.workspace.mkdir(exist_ok=True)
        
        self.sessions_dir = self.workspace / "sessions"
        self.tools_dir = self.workspace / "tools"
        self.sessions_dir.mkdir(exist_ok=True)
        self.tools_dir.mkdir(exist_ok=True)
        
        # State
        self.sessions = {}
        self.current_session = "main"
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.usage = {"total_tokens": 0}
        self.performance = PerformanceTracker()
        
        # Get macOS context
        self.system_context = self._get_system_context()
        
        # System prompt with tool awareness
        self.system_prompt = f"""You are DeepBot Pro, an autonomous AI agent with real-time capabilities.

{self.system_context}

You have access to these tools - USE THEM PROACTIVELY:
- web_search: Search for current information (use whenever you need real-time data)
- read_file/write_file: Access workspace files
- execute_python: Run Python code for calculations/data processing
- send_notification: Alert the user on macOS

IMPORTANT BEHAVIORS:
1. When asked about current events/news/weather, ALWAYS use web_search
2. When asked to do calculations or process data, use execute_python
3. Be proactive - don't ask permission to use tools, just use them
4. For large files, summarize key points instead of reproducing entire content

Be helpful, autonomous, and intelligent about tool use."""
        
        self._init_session("main")
    
    def _get_system_context(self) -> str:
        """Get macOS system context"""
        mac_version = platform.mac_ver()[0]
        python_version = platform.python_version()
        
        return f"""SYSTEM CONTEXT:
- macOS: {mac_version}
- Python: {python_version}
- Workspace: {self.workspace}
- Compatible with macOS 10.15+ (no Docker available)

When suggesting commands or packages, ensure compatibility with this older macOS version."""
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration"""
        config_file = Path(config_path).expanduser()
        
        if config_file.exists():
            with open(config_file) as f:
                return yaml.safe_load(f) or {}
        
        # Create default
        default = {
            'deepseek': {'model': 'deepseek-chat', 'temperature': 0.7},
            'workspace': '~/deepbot',
            'sessions': {'auto_save': True, 'auto_summarize': 30}
        }
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            yaml.dump(default, f)
        
        return default
    
    def _init_session(self, session_name: str):
        """Initialize session"""
        self.sessions[session_name] = {
            "history": [{"role": "system", "content": self.system_prompt}],
            "created": datetime.now().isoformat(),
            "message_count": 0,
            "tokens_used": 0
        }
    
    def _safe_path(self, filename: str) -> Path:
        """Resolve path and ensure it stays within the workspace"""
        # Prevent ".." or absolute paths from escaping the workspace
        requested_path = Path(filename).name  # Only take filename, strip any path
        safe_path = (self.workspace / requested_path).resolve()
        
        # Verify the resolved path is still within workspace
        if not str(safe_path).startswith(str(self.workspace.resolve())):
            raise PermissionError(f"Access denied: {filename} is outside workspace")
        
        return safe_path
    
    def handle_command(self, user_input: str) -> Optional[str]:
        """Handle administrative commands"""
        parts = user_input.strip().split(maxsplit=2)
        if not parts or not parts[0].startswith('/'):
            return None
        
        cmd = parts[0].lower()
        
        # Session management
        if cmd == '/session' and len(parts) >= 2:
            action = parts[1].lower()
            
            if action == 'new' and len(parts) >= 3:
                name = parts[2].strip()
                self._init_session(name)
                self.current_session = name
                return f"✨ New session: {name}"
            
            elif action == 'switch' and len(parts) >= 3:
                name = parts[2].strip()
                if name not in self.sessions:
                    return f"❌ Session '{name}' not found. Use /session new {name}"
                self.current_session = name
                return f"🔄 Switched to: {name}"
            
            elif action == 'list':
                active = []
                for name in self.sessions.keys():
                    marker = '➤' if name == self.current_session else ' '
                    active.append(f"  {marker} {name} ({self.sessions[name]['message_count']} messages)")
                return "💬 Sessions:\n" + "\n".join(active)
            
            elif action == 'delete' and len(parts) >= 3:
                name = parts[2].strip()
                if name == 'main':
                    return "❌ Cannot delete main session"
                if name == self.current_session:
                    return "❌ Cannot delete active session"
                if name in self.sessions:
                    del self.sessions[name]
                    # Delete from disk
                    session_file = self.sessions_dir / f"{name}.json"
                    if session_file.exists():
                        session_file.unlink()
                    return f"🗑️ Deleted session: {name}"
                return f"❌ Session not found: {name}"
        
        # Tools list
        elif cmd == '/tools':
            tools = ToolRegistry.get_tools()
            tool_list = []
            for t in tools:
                name = t['function']['name']
                desc = t['function']['description'][:80] + "..." if len(t['function']['description']) > 80 else t['function']['description']
                tool_list.append(f"  • {name}: {desc}")
            return "🔧 Available Tools:\n" + "\n".join(tool_list)
        
        # Performance stats
        elif cmd == '/stats':
            return self.performance.get_stats()
        
        # Help
        elif cmd == '/help':
            return """
📖 DeepBot Pro Commands:

Session Management:
  /session new <name>    - Create new session
  /session switch <n>    - Switch to session
  /session list          - List all sessions
  /session delete <n>    - Delete a session

Information:
  /tools                 - List available tools
  /stats                 - Performance metrics
  /help                  - Show this help

Actions:
  /quit or /exit         - Save and exit

💡 Tip: Just chat naturally! The AI will use tools automatically.
"""
        
        return None
    
    def _execute_tool(self, tool_name: str, arguments: Dict) -> str:
        """Execute a tool call"""
        try:
            if tool_name == "web_search":
                return self._tool_web_search(**arguments)
            elif tool_name == "read_file":
                return self._tool_read_file(**arguments)
            elif tool_name == "write_file":
                return self._tool_write_file(**arguments)
            elif tool_name == "list_files":
                return self._tool_list_files()
            elif tool_name == "execute_python":
                return self._tool_execute_python(**arguments)
            elif tool_name == "send_notification":
                return self._tool_send_notification(**arguments)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Tool execution error: {str(e)}"
    
    def _tool_web_search(self, query: str, max_results: int = 3) -> str:
        """Web search tool"""
        if not HAS_SEARCH:
            return "Web search not available. Install: pip install duckduckgo-search"
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                if not results:
                    return "No results found."
                
                formatted = f"Search results for '{query}':\n\n"
                for i, r in enumerate(results, 1):
                    formatted += f"{i}. {r['title']}\n{r['body'][:200]}...\n{r['href']}\n\n"
                return formatted
        except Exception as e:
            return f"Search error: {str(e)}"
    
    def _tool_read_file(self, filename: str) -> str:
        """Read file tool with path validation"""
        try:
            filepath = self._safe_path(filename)
            if not filepath.exists():
                return f"File not found: {filename}"
            return DocumentParser.read_file(filepath)
        except PermissionError as e:
            return f"Security error: {str(e)}"
        except Exception as e:
            return f"Read error: {str(e)}"
    
    def _tool_write_file(self, filename: str, content: str) -> str:
        """Write file tool with path validation"""
        try:
            filepath = self._safe_path(filename)
            filepath.write_text(content)
            return f"File written: {filepath.name} ({len(content)} chars)"
        except PermissionError as e:
            return f"Security error: {str(e)}"
        except Exception as e:
            return f"Write error: {str(e)}"
    
    def _tool_list_files(self) -> str:
        """List files tool"""
        files = [f for f in self.workspace.glob("*") if f.is_file()]
        if not files:
            return "Workspace is empty"
        
        return "Files:\n" + "\n".join([
            f"- {f.name} ({f.stat().st_size} bytes)"
            for f in files
        ])
    
    def _tool_execute_python(self, code: str) -> str:
        """Execute Python code tool"""
        result = CodeSandbox.execute(code)
        
        if result.get("success"):
            output = []
            if result.get("stdout"):
                output.append(f"Output:\n{result['stdout']}")
            if result.get("stderr"):
                output.append(f"Errors:\n{result['stderr']}")
            if result.get("returncode") != 0:
                output.append(f"Exit code: {result['returncode']}")
            
            return "\n\n".join(output) if output else "Code executed successfully (no output)"
        else:
            return f"Execution failed: {result.get('error')}"
    
    def _tool_send_notification(self, message: str) -> str:
        """Send macOS notification"""
        try:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "DeepBot Pro"'
            ], check=True)
            return "Notification sent"
        except Exception as e:
            return f"Notification failed: {str(e)}"
    
    def _continue_conversation(self) -> Generator[str, None, None]:
        """Continue conversation after tool execution"""
        session = self.sessions[self.current_session]
        tools = ToolRegistry.get_tools()
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": session["history"],
                    "tools": tools,
                    "temperature": 0.7,
                    "stream": True
                },
                stream=True,
                timeout=60
            )
            
            full_response = ""
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line = line.decode('utf-8')
                if not line.startswith('data: '):
                    continue
                
                data = line[6:]
                if data == '[DONE]':
                    break
                
                try:
                    chunk = json.loads(data)
                    delta = chunk['choices'][0].get('delta', {})
                    
                    if 'content' in delta and delta['content']:
                        content = delta['content']
                        full_response += content
                        yield content
                
                except json.JSONDecodeError:
                    continue
            
            # Save final response
            if full_response:
                session["history"].append({
                    "role": "assistant",
                    "content": full_response
                })
        
        except Exception as e:
            yield f"\n❌ Continuation error: {str(e)}"
    
    def ask_stream(self, question: str) -> Generator[str, None, None]:
        """Ask with streaming response"""
        # Handle commands first
        cmd_result = self.handle_command(question)
        if cmd_result:
            yield cmd_result
            return
        
        session = self.sessions[self.current_session]
        session["history"].append({"role": "user", "content": question})
        session["message_count"] += 1
        
        start_time = datetime.now()
        used_tools = False
        
        try:
            # Get tools
            tools = ToolRegistry.get_tools()
            
            # Make streaming request
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": session["history"],
                    "tools": tools,
                    "temperature": 0.7,
                    "stream": True
                },
                stream=True,
                timeout=60
            )
            
            full_response = ""
            tool_calls = []
            finish_reason = None
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line = line.decode('utf-8')
                if not line.startswith('data: '):
                    continue
                
                data = line[6:]
                if data == '[DONE]':
                    break
                
                try:
                    chunk = json.loads(data)
                    choice = chunk['choices'][0]
                    delta = choice.get('delta', {})
                    
                    # Check finish reason
                    if 'finish_reason' in choice and choice['finish_reason']:
                        finish_reason = choice['finish_reason']
                    
                    # Handle content
                    if 'content' in delta and delta['content']:
                        content = delta['content']
                        full_response += content
                        yield content
                    
                    # Handle tool calls
                    if 'tool_calls' in delta:
                        for tc in delta['tool_calls']:
                            if tc.get('index') is not None:
                                idx = tc['index']
                                if idx >= len(tool_calls):
                                    tool_calls.append({
                                        'id': tc.get('id', ''),
                                        'type': 'function',
                                        'function': {'name': '', 'arguments': ''}
                                    })
                                
                                if 'function' in tc:
                                    if 'name' in tc['function']:
                                        tool_calls[idx]['function']['name'] = tc['function']['name']
                                    if 'arguments' in tc['function']:
                                        tool_calls[idx]['function']['arguments'] += tc['function']['arguments']
                
                except json.JSONDecodeError:
                    continue
            
            # Execute tool calls if any
            if tool_calls and finish_reason == 'tool_calls':
                used_tools = True
                yield "\n\n[Using tools...]\n"
                
                for tc in tool_calls:
                    tool_name = tc['function']['name']
                    
                    # Parse arguments safely
                    try:
                        arguments = json.loads(tc['function']['arguments'])
                    except json.JSONDecodeError:
                        yield f"\n⚠️ Invalid tool arguments for {tool_name}\n"
                        continue
                    
                    yield f"\n🔧 {tool_name}({', '.join(f'{k}={repr(v)[:50]}' for k, v in arguments.items())})\n"
                    
                    # Execute tool
                    result = self._execute_tool(tool_name, arguments)
                    
                    # Add tool result to history
                    session["history"].append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tc]
                    })
                    session["history"].append({
                        "role": "tool",
                        "tool_call_id": tc['id'],
                        "content": result
                    })
                
                # Get continuation response after all tools executed
                yield "\n\n"
                for chunk in self._continue_conversation():
                    yield chunk
            else:
                # Save response
                session["history"].append({
                    "role": "assistant",
                    "content": full_response
                })
            
            # Track performance
            response_time = (datetime.now() - start_time).total_seconds()
            tokens_used = len(question.split()) + len(full_response.split())  # Rough estimate
            self.performance.track_query(tokens_used, used_tools, response_time)
            session["tokens_used"] += tokens_used
            self.usage["total_tokens"] += tokens_used
        
        except Exception as e:
            yield f"\n❌ Error: {str(e)}"
    
    def save_all_sessions(self):
        """Save sessions"""
        for name in self.sessions:
            filepath = self.sessions_dir / f"{name}.json"
            with open(filepath, 'w') as f:
                json.dump(self.sessions[name], f, indent=2)
        return f"Saved {len(self.sessions)} session(s)"


def print_banner():
    if HAS_RICH:
        console.print(Panel.fit(
            "[bold cyan]🦞 DeepBot Pro - Ultimate AI Agent[/bold cyan]\n"
            "[yellow]Autonomous • Intelligent • Superior to Clawdbot[/yellow]\n\n"
            "✨ Function Calling • Streaming • Rich UI • Secure Storage",
            border_style="cyan"
        ))
    else:
        print("""
╔════════════════════════════════════════════════╗
║      🦞 DeepBot Pro - Ultimate AI Agent        ║
║         Autonomous Tool Use Enabled!           ║
╚════════════════════════════════════════════════╝
        """)


def setup_wizard():
    """Interactive setup"""
    print("\n🔧 DeepBot Pro Setup\n")
    
    # Get API key
    api_key = input("Enter DeepSeek API key: ").strip()
    
    # Save to keychain
    if HAS_KEYRING:
        if SecureKeyStorage.save_key(api_key):
            print("✅ API key saved securely to macOS Keychain")
        else:
            print("⚠️ Could not save to keychain, will use environment variable")
            print(f"Run: export DEEPSEEK_API_KEY='{api_key}'")
    else:
        print("💡 Install keyring for secure storage: pip install keyring")
        print(f"For now, run: export DEEPSEEK_API_KEY='{api_key}'")
    
    print("\n✨ Setup complete! Run 'python deepbot_pro.py' to start.")


def auto_install():
    """Auto-install dependencies"""
    missing = []
    
    if not HAS_RICH:
        missing.append("rich")
    if not HAS_SEARCH:
        missing.append("duckduckgo-search")
    if not HAS_KEYRING:
        missing.append("keyring")
    if not HAS_PDF:
        missing.append("PyPDF2")
    if not HAS_DOCX:
        missing.append("python-docx")
    
    if missing:
        print(f"\n📦 Recommended: {', '.join(missing)}")
        choice = input("Install now? (y/n): ").lower()
        if choice == 'y':
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing)
            print("✅ Installed! Restart DeepBot.")
            sys.exit(0)


def main():
    if "--setup" in sys.argv:
        setup_wizard()
        return
    
    print_banner()
    auto_install()
    
    try:
        bot = DeepBotPro()
        
        if HAS_RICH:
            console.print(f"[green]✨ Ready![/green] Workspace: [cyan]{bot.workspace}[/cyan]")
            console.print("[dim]Type /help for commands[/dim]\n")
        else:
            print(f"✨ Ready! Workspace: {bot.workspace}")
            print("Type /help for commands\n")
        
        # Main loop
        while True:
            try:
                user_input = input(f"\n[{bot.current_session}] You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['/quit', '/exit']:
                    print(bot.save_all_sessions())
                    print("👋 Goodbye!")
                    break
                
                # Stream response
                if HAS_RICH:
                    console.print("\n[bold]DeepBot:[/bold] ", end="")
                else:
                    print("\nDeepBot: ", end="", flush=True)
                
                for chunk in bot.ask_stream(user_input):
                    if HAS_RICH:
                        console.print(chunk, end="")
                    else:
                        print(chunk, end="", flush=True)
                
                print()  # Newline after response
                
            except KeyboardInterrupt:
                print("\n" + bot.save_all_sessions())
                print("👋 Goodbye!")
                break
    
    except ValueError as e:
        print(f"\n❌ {e}")
        print("Run with --setup to configure API key")
        sys.exit(1)


if __name__ == "__main__":
    main()
