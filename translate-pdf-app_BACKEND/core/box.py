from dataclasses import dataclass
from typing import Tuple, Optional
from pathlib import Path

@dataclass
class Box:
    """
    A class representing a bounding box with coordinates and information.
    """
    
    id: int
    coords: Tuple[float, float, float, float]
    content: Optional[str] = None
    translation: Optional[str] = None