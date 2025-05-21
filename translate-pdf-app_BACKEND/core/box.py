from dataclasses import dataclass
from typing import Tuple, Optional
from pathlib import Path
from enum import IntEnum, auto, unique


@unique
class BoxLabel(IntEnum):
    TITLE = 0
    PARAGRAPH = 1
    ABANDONED = 2
    FIGURE = 3
    FIGURE_CAPTION = 4
    TABLE = 5
    TABLE_CAPTION = 6
    TABLE_FOOTNOTE = 7
    ISOLATE_FORMULA = 8
    FORMULA_CAPTION = 9
    
    
@dataclass
class Box:
    """
    A class representing a bounding box with coordinates and information.
    """
    
    id: int
    label: BoxLabel
    coords: Tuple[float, float, float, float]
    content: Optional[str] = None
    translation: Optional[str] = None
    page_num: Optional[int] = None