"""
Enrichment of VespersService with external data.

This module loads psalm texts, antiphon scores, and other external files,
attaching them to a VespersService. It handles caching and graceful failures.
"""

from pathlib import Path
from typing import Optional, Dict, Tuple
import os
import re

from vespers_data import VespersService, Psalm
from vespers_format import get_antiphon_tex


class VespersEnricher:
    """Load and attach external data to a VespersService.
    
    Responsibilities:
    - Load psalm texts from psalm_texts/ directory
    - Determine tone from antiphon filename
    - Get LaTeX for gregorioscore antiphons
    - Cache loaded psalms to avoid re-reading
    - Handle missing files gracefully
    """
    
    def __init__(self, psalm_dir: str, antiphon_dir: str):
        """Initialize enricher with paths to external data.
        
        Args:
            psalm_dir: Path to directory containing psalm text files
                       (e.g., './psalm_texts' with files like 'Ps 109;1-5,7.txt')
            antiphon_dir: Path to directory containing .gabc antiphon files
                         (e.g., 'antiphons' with files like 'In_splendóribus_sanctis-6.gabc')
        """
        self.psalm_dir = Path(psalm_dir)
        self.antiphon_dir = Path(antiphon_dir)
        self._psalm_cache: Dict[str, list] = {}  # Cache for loaded psalm texts
        self._antiphon_cache: Dict[str, str] = {}  # Cache for antiphon LaTeX
    
    def enrich(self, service: VespersService) -> VespersService:
        """Enrich a VespersService by loading all external files.
        
        Populates:
        - Each psalm.text with verses
        - Each psalm.tone with the liturgical tone (from antiphon filename)
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
        
        Tone is determined by looking for the antiphon file in the antiphons folder.
        
        Args:
            psalm: Psalm object to enrich (modified in place)
        """
        # First: find the antiphon file and extract tone from its filename
        antiphon_file = self._find_antiphon_file(psalm.antiphon_latin)
        if antiphon_file:
            psalm.tone = self._extract_tone_from_filename(antiphon_file)
            psalm.score_latex = self._get_antiphon_score(psalm.antiphon_latin)
        else:
            # Antiphon not found - use default tone "1"
            psalm.tone = "1"
            psalm.score_latex = ""
            print(f"Warning: Could not find antiphon file for: {psalm.antiphon_latin[:60]}...")
        
        # Second: load the psalm verses from the text file
        psalm.text = self._load_psalm_file(psalm.reference)
    
    def _load_psalm_file(self, psalm_ref: str) -> list:
        """Load psalm verses from file.
        
        Handles Mac-style filenames where colons are replaced with semicolons.
        Example: psalm_ref "109:1-5,7" matches file "Ps 109;1-5,7.txt"
        
        Uses cache to avoid re-reading the same psalm.
        
        Args:
            psalm_ref: Reference like "109:1-5,7" or "111:1-10"
        
        Returns:
            List of psalm text lines (all lines from the file)
        """
        if psalm_ref in self._psalm_cache:
            return self._psalm_cache[psalm_ref]
        
        # Convert reference to Mac-friendly filename pattern
        # "109:1-5,7" -> "109;1-5,7" (replace : with ;)
        mac_friendly = psalm_ref.replace(':', ';')
        file_pattern = f'*{mac_friendly}*.txt'
        
        # Search for matching file in psalm_dir
        try:
            matching_files = list(self.psalm_dir.glob(file_pattern))
            if matching_files:
                psalm_file = matching_files[0]
                text = self._parse_psalm_file(psalm_file)
                self._psalm_cache[psalm_ref] = text
                return text
            else:
                print(f"Warning: Could not find psalm file for {psalm_ref} (pattern: {file_pattern})")
                return []
        except Exception as e:
            print(f"Warning: Could not load psalm {psalm_ref}: {e}")
            return []
    
    def _parse_psalm_file(self, file_path: Path) -> list:
        """Parse a psalm text file.
        
        All lines in the file are psalm verses (text starts from the beginning).
        
        Args:
            file_path: Path to the psalm text file
        
        Returns:
            List of all text lines from the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.read().strip().split('\n')
            
            # All lines are psalm verses
            text = [line.strip() for line in lines if line.strip()]
            return text
        except Exception as e:
            print(f"Warning: Could not parse psalm file {file_path}: {e}")
            return []
    
    def _find_antiphon_file(self, antiphon_name: str) -> Optional[str]:
        """Find antiphon .gabc file matching antiphon text.
        
        Converts antiphon Latin text to filename pattern by:
        1. Taking the first ~40 characters (before punctuation)
        2. Replacing spaces with underscores
        3. Searching for matching .gabc files
        
        Example: "In splendóribus sanctis, ante lucíferum génui te"
        → pattern: "In_splendóribus_sanctis*.gabc"
        → matches: "In_splendóribus_sanctis-6.gabc"
        
        Args:
            antiphon_name: Latin text like "In splendóribus sanctis, ante lucíferum génui te, allelúia..."
        
        Returns:
            Filename of matching .gabc file, or None if not found
        """
        if not antiphon_name:
            return None
        
        # Extract the beginning of the antiphon (up to first punctuation or comma)
        # This gives us a reasonably unique identifier
        match = re.match(r"([^,]+?)(?:[,\.]|$)", antiphon_name.strip())
        if match:
            antiphon_start = match.group(1).strip()
        else:
            antiphon_start = antiphon_name.strip()
        
        # Limit to reasonable length to avoid overly long filenames
        antiphon_start = antiphon_start[:50]
        
        # Convert to filename pattern: spaces → underscores
        file_pattern = antiphon_start.replace(' ', '_') + '*.gabc'
        
        # Search for matching files
        try:
            antiphon_files = os.listdir(self.antiphon_dir)
            
            # Use simple wildcard matching
            import fnmatch
            matching = fnmatch.filter(antiphon_files, file_pattern)
            
            if matching:
                return matching[0]  # Return first match
            else:
                # If no exact match, try a more lenient search on word boundaries
                # Look for files that start with the first word
                first_word = antiphon_start.split()[0] if antiphon_start else ""
                if first_word:
                    lenient_pattern = first_word + '*.gabc'
                    lenient_matching = fnmatch.filter(antiphon_files, lenient_pattern)
                    if lenient_matching:
                        return lenient_matching[0]
        except Exception as e:
            print(f"Warning: Could not search antiphons directory: {e}")
        
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
        - "In_splendóribus_sanctis-6.gabc" → "6"
        - "O_lux_beáta_Trínitas-1a.gabc" → "1a"
        - "antiphon-8G.gabc" → "8G"
        
        Args:
            filename: Basename of .gabc file
        
        Returns:
            Tone code like "1", "8G", "6", etc.
        """
        # Extract part after last hyphen, before .gabc
        return filename.split('-')[-1].split('.')[0]
    
    def clear_cache(self) -> None:
        """Clear all caches.
        
        Useful if external files change and you need to reload them.
        """
        self._psalm_cache.clear()
        self._antiphon_cache.clear()
