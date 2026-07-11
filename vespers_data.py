"""
Data structures for vespers services.

This module defines the canonical representation of a vespers service,
decoupling data parsing from LaTeX rendering.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Psalm:
    """A single psalm or canticle in the service.
    
    This represents the structure with both parsed input and enriched data
    (loaded from external files).
    """
    
    # From input text file
    reference: str              # "109:1-5,7" or "111:1-10"
    name: str                   # "Dixit Dominus" or "Beatus vir"
    antiphon_latin: str         # "In splendóribus sanctis, ante lucíferum génui te, allelúia."
    antiphon_english: str       # "In holy splendour I begot you before the dawn, alleluia."
    
    # Loaded via enrichment (external files)
    text: List[str] = field(default_factory=list)      # Psalm verses after parsing
    tone: str = ""              # "1", "8G", "2*a", etc. (extracted from antiphon filename)
    score_latex: str = ""       # LaTeX snippet for gregorioscore antiphon


@dataclass
class VespersService:
    """Complete vespers service for one day.
    
    This is the canonical data structure for a single day's vespers.
    It's populated by parse_vespers_text() and enriched by VespersEnricher.
    """
    
    # Metadata
    name: str                   # "12th Sunday in Ordinary Time"
    date_str: str              # "21 June 2026"
    
    # Opening hymn
    hymn_latin: List[str] = field(default_factory=list)      # Latin verses
    hymn_english: List[str] = field(default_factory=list)    # English verses
    
    # Three psalms/canticles (Psalm A, Psalm B, Canticle)
    psalms: List[Psalm] = field(default_factory=list)
    
    # Chapter (Scripture reading)
    chapter: List[str] = field(default_factory=list)
    
    # Short Responsory
    response_short: List[str] = field(default_factory=list)
    
    # Second Reading
    reading_second: List[str] = field(default_factory=list)
    
    # Magnificat antiphon (sung before and after the Magnificat)
    magnificat_antiphon_latin: str = ""
    magnificat_antiphon_english: str = ""
    magnificat_score_latex: str = ""  # Loaded via enrichment
    
    # Prayers and intercessions
    prayers: List[str] = field(default_factory=list)
    
    # Conclusion (before dismissal)
    conclusion: List[str] = field(default_factory=list)


def to_filename(service: VespersService) -> str:
    """Generate consistent output filename from service data.
    
    Example: "12TH_SUNDAY_IN_ORDINARY_TIME_handout.tex"
    """
    return service.name.upper().replace(' ', '_') + '_handout.tex'
