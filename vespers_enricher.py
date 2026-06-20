"""
Enrichment of VespersService with external data.

This module loads psalm texts, antiphon scores, and other external files,
attaching them to a VespersService. It handles caching and graceful failures.
"""

from pathlib import Path
from typing import Optional, Dict, Tuple
import fnmatch
import os

from vespers_data import VespersService, Psalm
from vespers_format import get_psalm_file, get_antiphon_tex


class VespersEnricher:
    """Load and attach external data to a VespersService.
    
    Responsibilities:
    - Load psalm texts from psalm_texts/ directory
    - Determine tone from antiphon filename or use default
    - Get LaTeX for gregorioscore antiphons
    - Cache loaded psalms to avoid re-reading
    - Handle missing files gracefully
    """
    
    def __init__(self, psalm_dir: str, antiphon_dir: str):
        """Initialize enricher with paths to external data.
        
        Args:
            psalm_dir: Path to directory containing psalm_texts/ subdirectory
            antiphon_dir: Path to directory containing .gabc antiphon files
        """
        self.psalm_dir = Path(psalm_dir)
        self.antiphon_dir = Path(antiphon_dir)
        self._psalm_cache: Dict[str, Tuple[list, str]] = {}  # Cache for loaded psalms
        self._antiphon_cache: Dict[str, str] = {}  # Cache for antiphon LaTeX
    
    def enrich(self, service: VespersService) -> VespersService:
        """Enrich a VespersService by loading all external files.
        
        Populates:
        - Each psalm.text with verses
        - Each psalm.tone with the liturgical tone
        - Each psalm.score_latex with gregorioscore LaTeX
        - service.magnificat_score_latex
        
        Args:
            service: Partially populated VespersService
        
        Returns:
            Same service object, now with all external data loaded
        """
        # Enrich each psalm
        for psalm in service.psalms:
            self._enrich_psalm(psalm)
        
        # Load magnificat antiphon score
        service.magnificat_score_latex = self._get_antiphon_score(
            service.magnificat_antiphon_latin,
            mag=True
        )
        
        return service
    
    def _enrich_psalm(self, psalm: Psalm) -> None:
        """Load psalm text and determine tone for a single psalm.
        
        Args:
            psalm: Psalm object to enrich (modified in place)
        """
        # Load psalm verses from file
        psalm.text, default_tone = self._load_psalm_file(psalm.reference)
        
        # Determine tone: try to get from antiphon file, fall back to default
        antiphon_file = self._find_antiphon_file(psalm.antiphon_latin)
        if antiphon_file:
            psalm.tone = self._extract_tone_from_filename(antiphon_file)
            psalm.score_latex = self._get_antiphon_score(psalm.antiphon_latin)
        else:
            # Use default tone from psalm file
            psalm.tone = default_tone[0] if default_tone else "1"
            psalm.score_latex = self._get_tone_score(default_tone)
    
    def _load_psalm_file(self, psalm_ref: str) -> Tuple[list, str]:
        """Load psalm verses and return default tone.
        
        Uses cache to avoid re-reading the same psalm.
        
        Args:
            psalm_ref: Reference like "109:1-5,7" or "111:1-10"
        
        Returns:
            Tuple of (psalm_text_lines, default_tone_code)
        """
        if psalm_ref in self._psalm_cache:
            return self._psalm_cache[psalm_ref]
        
        # Use existing get_psalm_file() from vespers_format
        try:
            text, tone = get_psalm_file(
                str(self.psalm_dir),
                psalm_ref,
                fix_lord=True,
                tex=True
            )
            self._psalm_cache[psalm_ref] = (text, tone)
            return text, tone
        except Exception as e:
            print(f"Warning: Could not load psalm {psalm_ref}: {e}")
            return [], "1"
    
    def _find_antiphon_file(self, antiphon_name: str) -> Optional[str]:
        """Find antiphon .gabc file matching antiphon text.
        
        Normalizes the antiphon name (replace spaces with underscores, etc.)
        and searches for matching .gabc file.
        
        Args:
            antiphon_name: Latin text like "In splendóribus sanctis..."
        
        Returns:
            Filename of matching .gabc file, or None if not found
        """
        # Normalize antiphon name to match filename conventions
        normalized = antiphon_name.replace(' ', '_').replace(',', '').replace(':', '')
        
        # Search for matching files
        fns = fnmatch.filter(
            os.listdir(self.antiphon_dir),
            normalized + '*.gabc'
        )
        
        if fns:
            return fns[0]  # Return first match
        return None
    
    def _get_antiphon_score(self, antiphon_name: str, mag: bool = False) -> str:
        """Get LaTeX snippet for gregorioscore.
        
        Uses cache to avoid re-computing the same antiphon.
        
        Args:
            antiphon_name: Latin text of antiphon
            mag: If True, print warning for missing magnificat antiphons
        
        Returns:
            LaTeX snippet like r'{\justifying\gregorioscore[a]{antiphons/O_lux_beáta_Trínitas.gabc}}'
            or empty string if antiphon not found
        """
        cache_key = (antiphon_name, mag)
        if cache_key in self._antiphon_cache:
            return self._antiphon_cache[cache_key]
        
        # Use existing get_antiphon_tex() from vespers_format
        result = get_antiphon_tex(
            str(self.antiphon_dir),
            antiphon_name,
            handout=True,
            mag=mag
        )
        
        self._antiphon_cache[cache_key] = result
        return result
    
    def _extract_tone_from_filename(self, filename: str) -> str:
        """Parse tone code from antiphon filename.
        
        Examples:
        - "O_lux_beáta_Trínitas-1a.gabc" → "1a"
        - "antiphon-8G.gabc" → "8G"
        - "response-7.gabc" → "7"
        
        Args:
            filename: Basename of .gabc file
        
        Returns:
            Tone code like "1", "8G", "2*a", etc.
        """
        # Extract part after last hyphen, before .gabc
        return filename.split('-')[-1].split('.')[0]
    
    def _get_tone_score(self, tone: str) -> str:
        """Get tone score image (LaTeX).
        
        Falls back to using existing get_antiphon_tex() to find tone score.
        
        Args:
            tone: Tone code like "1", "8G", etc.
        
        Returns:
            LaTeX snippet for tone score image
        """
        if not tone:
            return ""
        
        try:
            result = get_antiphon_tex(
                str(self.antiphon_dir),
                tone,
                handout=True
            )
            return result
        except Exception as e:
            print(f"Warning: Could not load tone {tone}: {e}")
            return ""
    
    def clear_cache(self) -> None:
        """Clear all caches.
        
        Useful if external files change and you need to reload them.
        """
        self._psalm_cache.clear()
        self._antiphon_cache.clear()
