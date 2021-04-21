from typing import Dict


class LayoutEngine:
    """Base layout Engine

    Potential Methods:
        - machinery to standardize edge post processing
        - complexity checking (hide deeply nested elements to help rendering?)
        - label sizing
    """

    async def layout(self, value: Dict) -> Dict:
        """Takes elk json and returns laid out elk json"""
        raise NotImplementedError("Subclasses must implement layout method")
