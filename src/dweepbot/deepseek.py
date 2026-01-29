import requests
import os
from typing import Generator

class DeepSeekAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.history = []
    
    def chat(self, message: str) -> Generator[str, None, None]:
        """Stream chat response"""
        self.history.append({"role": "user", "content": message})
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": self.history,
                    "stream": True,
                    "temperature": 0.7
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
                    import json
                    chunk = json.loads(data)
                    delta = chunk['choices'][0]['delta']
                    
                    if 'content' in delta:
                        content = delta['content']
                        full_response += content
                        yield content
                except:
                    continue
            
            self.history.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            yield f"\n❌ Error: {str(e)}"
    
    def reset(self):
        """Clear chat history"""
        self.history = []
