"""
Enrichment of VespersService with external data.

This module loads psalm texts, antiphon scores, and other external files,
attaching them to a VespersService. It handles caching and graceful failures.
"""

from pathlib import Path
from typing import Optional, Dict
import os
import re
import unicodedata

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
        hymn_dir = os.path.join(self.psalm_dir, "hymn_text")  # or your repo root path source
        hymn_key = " ".join((service.hymn_latin[0] if service.hymn_latin else "").split()[:4])  # better than 3
        path = self._find_hymn_file(hymn_dir, hymn_key)

        if path:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.rstrip("\n") for ln in f]
            service.hymn_latin = lines
            print(f"Loaded hymn from file: {path}")
        else:
            print(f"Warning: hymn file not found for key '{hymn_key}' in {hymn_dir}")

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

    def _normalize_text(self, text: str) -> str:
        """Normalize Unicode and punctuation for robust matching.

        - NFD normalize
        - strip combining marks
        - lowercase
        - replace punctuation/whitespace with underscores
        - collapse repeated underscores
        """
        if not text:
            return ""
        nfd = unicodedata.normalize("NFD", text)
        no_marks = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
        lowered = no_marks.lower()
        cleaned = re.sub(r"[^a-z0-9]+", "_", lowered)
        return re.sub(r"_+", "_", cleaned).strip("_")

    def _psalm_ref_candidates(self, psalm_ref: str) -> list[str]:
        """Build normalized search candidates for psalm reference lookups."""
        base = psalm_ref.strip()
        candidates = {
            base,
            base.replace(':', ';'),
            base.replace(':', ' '),
            base.replace(';', ':'),
            base.replace(';', ' '),
        }
        # Common references include leading "Ps " or "Ap " in filenames
        expanded = set(candidates)
        for c in list(candidates):
            expanded.add(f"Ps {c}")
            expanded.add(f"Ap {c}")
        return [c for c in expanded if c]

    def _load_psalm_file(self, psalm_ref: str) -> list:
        """Load psalm verses from file with tolerant matching."""
        if psalm_ref in self._psalm_cache:
            return self._psalm_cache[psalm_ref]

        try:
            all_txt_files = list(self.psalm_dir.glob("*.txt"))
            candidate_refs = self._psalm_ref_candidates(psalm_ref)

            # 1) direct glob attempts (fast path)
            for cand in candidate_refs:
                pattern = f"*{cand}*.txt"
                matching_files = list(self.psalm_dir.glob(pattern))
                if matching_files:
                    psalm_file = matching_files[0]
                    text = self._parse_psalm_file(psalm_file)
                    self._psalm_cache[psalm_ref] = text
                    return text

            # 2) normalized fallback matching
            norm_candidates = [self._normalize_text(c) for c in candidate_refs]
            for file_path in all_txt_files:
                file_norm = self._normalize_text(file_path.stem)
                if any(nc and nc in file_norm for nc in norm_candidates):
                    text = self._parse_psalm_file(file_path)
                    self._psalm_cache[psalm_ref] = text
                    return text

            print(f"Warning: Could not find psalm file for {psalm_ref}")
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
        """Find antiphon .gabc file matching antiphon text using normalized matching."""
        if not antiphon_name:
            return None

        # Extract opening phrase up to punctuation as a likely filename stem
        match = re.match(r"([^,\.]+?)(?:[,\.]|$)", antiphon_name.strip())
        antiphon_start = match.group(1).strip() if match else antiphon_name.strip()
        antiphon_start = antiphon_start[:80]

        try:
            antiphon_files = [f for f in os.listdir(self.antiphon_dir) if f.endswith('.gabc')]

            # 1) legacy direct matching
            direct_pattern = antiphon_start.replace(' ', '_') + '*.gabc'
            import fnmatch
            direct = fnmatch.filter(antiphon_files, direct_pattern)
            if direct:
                return direct[0]

            # 2) normalized robust matching
            antiphon_norm = self._normalize_text(antiphon_start)
            antiphon_words = [w for w in antiphon_norm.split('_') if w]
            first_words = antiphon_words[:4]  # opening words are usually stable

            best_file = None
            best_score = -1
            for fn in antiphon_files:
                stem_norm = self._normalize_text(Path(fn).stem)
                score = 0
                if antiphon_norm and antiphon_norm in stem_norm:
                    score += 10
                for w in first_words:
                    if w in stem_norm:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_file = fn

            # require a minimal confidence to avoid bad matches
            if best_file and best_score >= max(2, len(first_words) // 2):
                return best_file
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

    def _norm_text(self, s: str) -> str:
        if not s:
            return ""
        s = unicodedata.normalize("NFC", s).strip().casefold()
        s = unicodedata.normalize("NFD", s)
        s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
        s = re.sub(r"[^0-9a-z]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _prefix_tokens(self, s: str, n: int = 4) -> str:
        return " ".join(self._norm_text(s).split()[:n])

    def _find_hymn_file(self, hymn_dir: str, hymn_key: str) -> Optional[str]:
        files = [f for f in os.listdir(hymn_dir) if f.lower().endswith(".txt")]
        target = self._norm_text(hymn_key)
        target_prefix = self._prefix_tokens(hymn_key, 4)

        # exact stem
        for fn in files:
            stem, _ = os.path.splitext(fn)
            if self._norm_text(stem) == target:
                return os.path.join(hymn_dir, fn)

        # startswith either direction
        for fn in files:
            stem, _ = os.path.splitext(fn)
            s = self._norm_text(stem)
            if s.startswith(target) or target.startswith(s):
                return os.path.join(hymn_dir, fn)

        # token-prefix fallback
        for fn in files:
            stem, _ = os.path.splitext(fn)
            p = self._prefix_tokens(stem, 4)
            if p and (p == target_prefix or p.startswith(target_prefix) or target_prefix.startswith(p)):
                return os.path.join(hymn_dir, fn)

        return None

    def clear_cache(self) -> None:
        """Clear all caches.

        Useful if external files change and you need to reload them.
        """
        self._psalm_cache.clear()
        self._antiphon_cache.clear()
