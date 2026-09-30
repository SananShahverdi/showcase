from typing import Dict, Any
from local_ai_inference_gateway_llmops_console.domain.models import PromptTemplate
import re

def extract_variables(template_string: str) -> list[str]:
    """Extracts variables from a template string e.g. 'Hello {name}' -> ['name']"""
    return re.findall(r'\{([^}]+)\}', template_string)

def compile_prompt(template: PromptTemplate, variables: Dict[str, Any]) -> str:
    """Compiles the active version of a prompt template with provided variables."""
    if not template.active_version_id:
        raise ValueError("Template has no active version")
        
    active_version = next((v for v in template.versions if v.id == template.active_version_id), None)
    if not active_version:
        raise ValueError("Active version not found")
        
    compiled = active_version.template_string
    for var in active_version.variables:
        if var not in variables:
            raise ValueError(f"Missing variable: {var}")
        compiled = compiled.replace(f"{{{var}}}", str(variables[var]))
        
    return compiled
