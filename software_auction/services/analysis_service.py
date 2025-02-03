import logging
from openai import OpenAI
from django.conf import settings as django_settings
import json
import os
from datetime import datetime
from ..llama_cpp_utils import get_llama_response

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=django_settings.OPENAI_API_KEY)
        self.code_storage_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'generated_code'
        )
        self.use_llama = django_settings.AI_MODEL_CONFIG.get('USE_LLAMA', False)
        self.model_name = django_settings.AI_MODEL_CONFIG.get('OPENAI_MODEL', 'gpt-4')
        self.temperature = django_settings.AI_MODEL_CONFIG.get('TEMPERATURE', 0.7)
        
        if not os.path.exists(self.code_storage_path):
            os.makedirs(self.code_storage_path)

    def generate_analysis_instructions(self, transcript: str, use_llama: bool = None) -> dict:
        """Generate context-appropriate data analysis instructions using configured model"""
        # Use parameter if provided, otherwise use settings default
        use_llama = use_llama if use_llama is not None else self.use_llama
        
        try:
            system_prompt = """You are a data analysis expert. Analyze the conversation and determine which types of analysis would be most relevant.
            Only include sections that are contextually appropriate. You must respond with a valid JSON object using this exact structure:
            {
                "sections": [
                    {
                        "title": "visualization",
                        "items": [
                            {
                                "description": "Clear description of the analysis step",
                                "code": "Executable Python code with necessary imports"
                            }
                        ]
                    }
                ]
            }

            Available section titles:
            - "visualization": for plotting and visual analysis needs
            - "statistical": for statistical tests and modeling
            - "preprocessing": for data cleaning and preparation
            - "forecasting": for time series and prediction tasks
            - "clustering": for grouping and segmentation
            - "correlation": for relationship analysis
            - "anomaly": for outlier detection
            - "text_analysis": for NLP tasks

            Only include relevant sections based on the conversation context.
            Ensure all code is properly escaped for JSON.
            Do not include any text before or after the JSON object."""

            user_prompt = f"Generate contextually appropriate analysis instructions from this conversation: {transcript}"

            if use_llama:
                combined_prompt = f"{system_prompt}\n\nUser: {user_prompt}\nAssistant:"
                instructions = get_llama_response(combined_prompt)
            else:
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature
                )
                instructions = response.choices[0].message.content.strip()
            
            try:
                # Parse and validate JSON structure
                parsed_instructions = json.loads(instructions)
                if not isinstance(parsed_instructions, dict) or 'sections' not in parsed_instructions:
                    raise ValueError("Invalid JSON structure")
                
                # Format JSON for response
                formatted_instructions = json.dumps(parsed_instructions)
                
                # Store the generated code
                self._store_generated_code(parsed_instructions)
                
                return {
                    'status': 'success',
                    'instructions': formatted_instructions,
                    'model': 'llama' if use_llama else 'gpt-4'
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Invalid JSON from {'Llama' if use_llama else 'GPT'}: {str(e)}\nResponse: {instructions}")
                return {
                    'status': 'error',
                    'error': 'Failed to parse analysis instructions',
                    'model': 'llama' if use_llama else 'gpt-4'
                }
                
        except Exception as e:
            logger.error(f"Error generating analysis instructions: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'model': 'llama' if use_llama else 'gpt-4'
            }

    def _store_generated_code(self, instructions: dict):
        """Store generated Python code in files"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            session_dir = os.path.join(self.code_storage_path, f'analysis_{timestamp}')
            os.makedirs(session_dir, exist_ok=True)
            
            # Store code for each section
            if 'sections' in instructions:
                for section in instructions['sections']:
                    if 'items' in section:
                        code_parts = []
                        for item in section['items']:
                            if 'code' in item and 'description' in item:
                                code_parts.append(f"# {item['description']}\n{item['code']}\n")
                        
                        if code_parts:
                            filename = os.path.join(session_dir, f"{section['title']}.py")
                            with open(filename, 'w') as f:
                                f.write("\n\n".join(code_parts))
        except Exception as e:
            logger.error(f"Error storing generated code: {str(e)}") 