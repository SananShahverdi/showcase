from typing import List, Optional
from local_ai_inference_gateway_llmops_console.domain.models import ProviderConfig

def select_provider(
    providers: List[ProviderConfig],
    capability: str = "chat",
    requires_high_privacy: bool = False
) -> Optional[ProviderConfig]:
    """Selects the best provider based on capabilities, privacy constraints, and priority."""
    valid_providers = []
    
    for p in providers:
        if not p.is_active:
            continue
        if capability not in p.capabilities:
            continue
        if requires_high_privacy and p.privacy_level != "high":
            continue
            
        valid_providers.append(p)
        
    if not valid_providers:
        return None
        
    # Sort by priority (lowest number is highest priority), then cost
    valid_providers.sort(key=lambda x: (x.priority, x.cost_per_1k_tokens))
    
    return valid_providers[0]
