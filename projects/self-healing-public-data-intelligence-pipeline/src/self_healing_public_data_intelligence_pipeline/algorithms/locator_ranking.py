from typing import List, Dict

def rank_locators(locators: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Ranks CSS/XPath selectors by stability.
    Accessibility (ARIA) > Semantic > Positional/Classes.
    locators should be a list of dicts like [{"type": "css", "value": "[aria-label='price']"}, ...]
    """
    def score_locator(loc: Dict[str, str]) -> int:
        val = loc.get("value", "").lower()
        if "aria-" in val or "role=" in val: return 3
        if "id=" in val or "#" in val and "nth-child" not in val: return 2
        if "nth-child" in val or "tr[" in val or "div > div" in val: return 0
        return 1
    
    return sorted(locators, key=score_locator, reverse=True)
