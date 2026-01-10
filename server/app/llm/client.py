"""
LangChain-based LLM client for interacting with Google Gemini.
Provides a clean abstraction over the LLM with proper error handling.
"""

from typing import Optional, List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from app.settings import settings
from app.core.logger import setup_logger
from app.core.exceptions import AgentError


logger = setup_logger(__name__)


class LLMClient:
    """
    Wrapper around LangChain's Gemini client.
    Provides consistent interface for all LLM interactions.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize the LLM client.
        
        Args:
            model: Model name (defaults to settings)
            temperature: Sampling temperature (defaults to settings)
            max_tokens: Max output tokens (defaults to settings)
        """
        self.model_name = model or settings.DEFAULT_LLM_MODEL
        self.temperature = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens or settings.MAX_OUTPUT_TOKENS
        
        # Validate API key
        if not settings.GEMINI_API_KEY:
            error_msg = "GEMINI_API_KEY is not set. Please set it in your .env file or environment variables."
            logger.error(error_msg)
            raise AgentError(error_msg)
        
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                google_api_key=settings.GEMINI_API_KEY
            )
            logger.info(f"Initialized LLM client with model: {self.model_name}")
        except Exception as e:
            error_msg = f"Failed to initialize LLM client: {str(e)}"
            logger.error(error_msg)
            raise AgentError(error_msg)
    
    def generate_text(
        self,
        prompt: str,
        system_message: Optional[str] = None
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: User prompt
            system_message: Optional system instruction
            
        Returns:
            Generated text
        """
        try:
            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=prompt))
            
            chain = self.llm | StrOutputParser()
            response = chain.invoke(messages)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise AgentError(f"LLM generation error: {str(e)}")
    
    def generate_json(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        fallback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON from a prompt with robust error handling.
        Handles LaTeX/math expressions and other special characters in JSON strings.
        
        Args:
            prompt: User prompt
            system_message: Optional system instruction
            fallback: Fallback dict to return on error
            
        Returns:
            Parsed JSON object
        """
        import json
        import re
        
        def extract_json_object(text: str) -> Optional[str]:
            """
            Extract JSON object from text using balanced brace matching.
            More robust than simple regex for handling nested structures.
            """
            # Find first opening brace
            start = text.find('{')
            if start == -1:
                return None
            
            # Count braces to find matching closing brace
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i in range(start, len(text)):
                char = text[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return text[start:i+1]
            
            return None
        
        def fix_json_escaping(text: str) -> str:
            """
            Fix common JSON escaping issues, especially for LaTeX/math expressions.
            Handles unescaped backslashes in string values.
            """
            # More aggressive fix: replace unescaped backslashes that aren't part of valid escape sequences
            # Valid escape sequences: \\, \", \/, \b, \f, \n, \r, \t, \uXXXX
            # Pattern: backslash not followed by ", \, /, b, f, n, r, t, or u (for unicode)
            def replace_unescaped_backslash(match):
                # Check if this backslash is already part of a valid escape sequence
                pos = match.start()
                if pos + 1 < len(text):
                    next_char = text[pos + 1]
                    if next_char in '"\\/bfnrtu':
                        return match.group(0)  # Keep valid escape sequences
                # Replace unescaped backslash with escaped backslash
                return '\\\\'
            
            # Replace unescaped backslashes in the entire string
            # But we need to be careful not to break valid escape sequences
            result = []
            i = 0
            while i < len(text):
                if text[i] == '\\':
                    # Check if it's a valid escape sequence
                    if i + 1 < len(text):
                        next_char = text[i + 1]
                        if next_char in '"\\/bfnrtu':
                            # Valid escape sequence, keep it
                            result.append(text[i])
                            result.append(text[i + 1])
                            i += 2
                            continue
                        elif next_char == 'u' and i + 5 < len(text):
                            # Unicode escape sequence \uXXXX
                            result.append(text[i:i+6])
                            i += 6
                            continue
                    # Invalid or unescaped backslash, escape it
                    result.append('\\\\')
                    i += 1
                else:
                    result.append(text[i])
                    i += 1
            
            return ''.join(result)
        
        try:
            # Enhanced JSON prompt with explicit LaTeX escaping instructions
            json_prompt = f"""{prompt}

CRITICAL INSTRUCTIONS:
1. Respond with VALID JSON only (no markdown, no code blocks, no extra text)
2. Use double quotes for keys and string values
3. Ensure all brackets are properly closed
4. Do not use trailing commas
5. **ESCAPE ALL BACKSLASHES IN STRINGS**: LaTeX expressions like \\sum, \\binom, \\frac must be written as \\\\sum, \\\\binom, \\\\frac in JSON
6. **ESCAPE SPECIAL CHARACTERS**: In JSON strings, backslashes must be doubled (\\ becomes \\\\)
7. Example: "reasoning": "Use $\\\\sum_{{i=0}}^{{n}}$ formula" (note the double backslashes)
8. For math expressions in strings, escape all backslashes: $\\\\frac{{a}}{{b}}$ not $\\frac{{a}}{{b}}$

Your response must be parseable by json.loads()."""
            
            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=json_prompt))
            
            # Try with JsonOutputParser first
            try:
                chain = self.llm | JsonOutputParser()
                response = chain.invoke(messages)
                
                if response and isinstance(response, dict):
                    return response
            except Exception as parse_error:
                logger.warning(f"JsonOutputParser failed: {parse_error}, trying manual parsing")
            
            # Fallback: Get raw text and parse manually
            chain = self.llm | StrOutputParser()
            raw_response = chain.invoke(messages)
            
            # Clean up the response
            raw_response = raw_response.strip()
            
            # Remove markdown code blocks if present
            if raw_response.startswith("```"):
                raw_response = re.sub(r'^```(?:json)?\s*', '', raw_response)
                raw_response = re.sub(r'\s*```$', '', raw_response)
                raw_response = raw_response.strip()
            
            # Extract JSON object using balanced brace matching
            json_text = extract_json_object(raw_response)
            if not json_text:
                logger.warning("Could not extract JSON object from response")
                logger.error(f"Raw response (first 500 chars): {raw_response[:500]}")
                if fallback:
                    logger.info("Using fallback response")
                    return fallback
                raise AgentError("No valid JSON object found in response")
            
            # Try to parse JSON with multiple fallback strategies
            try:
                # First attempt: parse as-is
                response = json.loads(json_text)
            except json.JSONDecodeError as e1:
                # Second attempt: fix escaping issues
                logger.info("Attempting to fix JSON escaping issues...")
                fixed_json = fix_json_escaping(json_text)
                try:
                    response = json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    # Third attempt: try to fix more aggressively
                    logger.info("Attempting aggressive JSON fixing...")
                    # Additional fix: ensure all backslashes before non-escape chars are doubled
                    # This handles cases where the LLM didn't escape LaTeX commands
                    more_fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', fixed_json)
                    try:
                        response = json.loads(more_fixed)
                    except json.JSONDecodeError as e3:
                        logger.error(f"JSON decode error after all fixes: {str(e3)}")
                        logger.error(f"Original error: {str(e1)}")
                        logger.error(f"Raw response (first 1000 chars): {raw_response[:1000]}")
                        logger.error(f"Extracted JSON (first 500 chars): {json_text[:500]}")
                        if fallback:
                            logger.info("Using fallback response")
                            return fallback
                        raise AgentError(f"Invalid json output after fixes: {str(e3)}")
            
            if not isinstance(response, dict):
                logger.warning(f"Parsed JSON is not a dict: {type(response)}")
                return fallback or {}
            
            logger.info(f"Successfully parsed JSON response with {len(response)} keys")
            return response
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Raw response (first 500 chars): {raw_response[:500] if 'raw_response' in locals() else 'N/A'}")
            
            if fallback:
                logger.info("Using fallback response")
                return fallback
            
            raise AgentError(f"Invalid json output: {str(e)}")
            
        except Exception as e:
            logger.error(f"JSON generation failed: {str(e)}")
            
            if fallback:
                logger.info("Using fallback response due to error")
                return fallback
            
            raise AgentError(f"JSON generation error: {str(e)}")
    
    def batch_generate(
        self,
        prompts: List[str],
        system_message: Optional[str] = None
    ) -> List[str]:
        """
        Generate responses for multiple prompts in batch.
        
        Args:
            prompts: List of prompts
            system_message: Optional system instruction
            
        Returns:
            List of generated responses
        """
        try:
            batch_messages = []
            for prompt in prompts:
                messages = []
                if system_message:
                    messages.append(SystemMessage(content=system_message))
                messages.append(HumanMessage(content=prompt))
                batch_messages.append(messages)
            
            chain = self.llm | StrOutputParser()
            responses = chain.batch(batch_messages)
            
            return [r.strip() for r in responses]
            
        except Exception as e:
            logger.error(f"Batch generation failed: {str(e)}")
            raise AgentError(f"Batch generation error: {str(e)}")


# Singleton instance for reuse
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
