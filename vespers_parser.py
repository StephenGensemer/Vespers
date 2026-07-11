"""
Parser for vespers input text.

This module extracts structured data from the parsed universalis ebook
and converts it to VespersService objects. It does NOT load external files
(that's done by VespersEnricher).
"""

from typing import List, Optional
from vespers_data import Psalm, VespersService
from vespers_format import get_nonempty_lines, parse_psalm_universalis, get_2nd_reading


def parse_vespers_text(service_name: str, parts: List[str], 
                       readings_parts: Optional[List[str]] = None) -> VespersService:
    """
    Parse vespers text from universalis ebook format into a VespersService.
    
    Args:
        service_name: Name of the service (e.g., "12th Sunday in Ordinary Time")
        parts: List of text sections from parse_universalis_ebook() for vespers
               [date_string, intro, hymn_section, psalm_a, psalm_b, canticle, ...]
        readings_parts: Optional list of text sections from parse_universalis_ebook() 
                       for office of readings. If None, reading_second will be empty.
    
    Returns:
        VespersService with all fields populated from input text
        (but psalm.text and magnificat_score_latex still empty - loaded by enricher)
    """
    
    # Extract data using existing parsing functions
    parsed_data = _extract_all_data(service_name, parts)
    
    # Try to get second reading from readings file if provided
    if readings_parts is not None:
        try:
            parsed_data.update(get_2nd_reading(readings_parts))
        except (ValueError, IndexError):
            # If second reading can't be parsed, leave it empty
            parsed_data['2read'] = []
    else:
        parsed_data['2read'] = []
    
    # Build Psalm objects for the three psalms
    psalms = [
        Psalm(
            reference=parsed_data['ps A'],
            name=parsed_data['ps A name'],
            antiphon_latin=parsed_data['ps A ant_lat'],
            antiphon_english=parsed_data['ps A ant_eng'],
        ),
        Psalm(
            reference=parsed_data['ps B'],
            name=parsed_data['ps B name'],
            antiphon_latin=parsed_data['ps B ant_lat'],
            antiphon_english=parsed_data['ps B ant_eng'],
        ),
        Psalm(
            reference=parsed_data['can'],
            name=parsed_data['can name'],
            antiphon_latin=parsed_data['can ant_lat'],
            antiphon_english=parsed_data['can ant_eng'],
        ),
    ]
    
    # Create the service
    service = VespersService(
        name=service_name,
        date_str=parts[0],
        hymn_latin=parsed_data['hymn_text'],
        hymn_english=parsed_data['hymn_text_eng'],
        psalms=psalms,
        chapter=parsed_data['chap'],
        response_short=parsed_data['response'],
        reading_second=parsed_data['2read'],
        magnificat_antiphon_latin=parsed_data['mag antiphon'],
        magnificat_antiphon_english=parsed_data['mag ant_eng'],
        prayers=parsed_data['pandi'],
        conclusion=parsed_data['conc'],
    )
    
    return service


def _extract_all_data(service_name: str, parts: List[str]) -> dict:
    """
    Extract all data from parts using existing parsing logic.
    
    This is essentially the body of get_vespers_data_universalis(),
    refactored to make the data flow clearer.
    
    Args:
        service_name: Name of the service
        parts: Sections from parse_universalis_ebook()
    
    Returns:
        Dictionary with keys like 'ps A', 'ps A name', 'hymn_text', etc.
    """
    d = {}
    d['name'] = service_name
    d['date_string'] = parts[0]
    
    # ============ HYMN ============
    text = parts[3].split('Hymn')[-2]
    d['hymn_text'] = get_nonempty_lines(text)[1:]
    d['hymn'] = ' '.join(d['hymn_text'][0].split()[:3])
    
    text = parts[3].split('Hymn')[-1]
    d['hymn_text_eng'] = get_nonempty_lines(text)
    
    # ============ PSALMS ============
    # Parse Psalm A
    d.update(parse_psalm_universalis('ps A', parts[4]))
    
    # Parse Psalm B
    d.update(parse_psalm_universalis('ps B', parts[5]))
    
    # Remove Psalm B's name if it's a continuation of the same psalm
    ps_num_A = d['ps A'].split(':')[0]
    ps_num_B = d['ps B'].split(':')[0]
    if ps_num_B == ps_num_A:
        d['ps B name'] = ''
    
    # Parse Canticle
    d.update(parse_psalm_universalis('can', parts[6]))
    
    # ============ CHAPTER (SCRIPTURE READING) ============
    text = parts[7].split('Scripture Reading')[1]
    d['chap'] = get_nonempty_lines(text)
    d['chap'].insert(1, '')  # Formatting fix
    
    # ============ SHORT RESPONSORY ============
    text = parts[8].split('Short Responsory')[1]
    d['response'] = get_nonempty_lines(text)
    
    # ============ MAGNIFICAT ANTIPHON ============
    text = parts[9]
    d['mag antiphon'] = get_nonempty_lines(text, 3)[2]
    d['mag ant'] = ' '.join(d['mag antiphon'].split()[:3]).strip(',')
    
    text = parts[9].split('Canticle')[1]
    d['mag ant_eng'] = get_nonempty_lines(text, 3)[2]
    
    # ============ PRAYERS AND INTERCESSIONS ============
    text = parts[10].split('Prayers and intercessions')[1]
    d['pandi'] = get_nonempty_lines(text)
    
    # ============ CONCLUSION ============
    text = parts[12].split('Amen.')[1]
    d['conc'] = get_nonempty_lines(text) + ['Amen.']
    
    # ============ SECOND READING (loaded separately from readings file) ============
    d['2read'] = []  # Will be updated by caller if readings_parts provided
    
    return d
