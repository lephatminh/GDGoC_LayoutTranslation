from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class Box:
    """
    A class representing a bounding box with coordinates and information.
    """
    
    id: int
    coords: Tuple[float, float, float, float]
    content: Optional[str] = None
    translation: Optional[str] = None
    page_num: Optional[int] = None