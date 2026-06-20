# Refactoring: Dataclass Structure

This branch introduces a clean separation between data parsing, external file loading, and LaTeX rendering.

## New Files

### `vespers_data.py`
Defines the canonical data structures:
- **`Psalm`** - A single psalm/canticle with reference, name, antiphons, and optional loaded data (text, tone, score)
- **`VespersService`** - Complete service for one day with all sections (hymn, psalms, readings, etc.)
- **`to_filename()`** - Generates consistent output filenames

### `vespers_parser.py`
Extracts text from the universalis ebook format into `VespersService`:
- **`parse_vespers_text(service_name, parts, readings_parts=None)`** - Main entry point
- Handles optional readings file
- Uses existing parsing functions from `vespers_format.py`

### `vespers_enricher.py` ⭐ NEW
Loads external files and attaches them to `VespersService`:
- **`VespersEnricher`** - Main class that handles all file loading
- Loads psalm texts from `psalms/psalm_texts/`
- Determines tone from antiphon filenames
- Gets LaTeX for gregorioscore
- **Caches everything** to avoid re-reading files
- Handles missing files gracefully with warnings

## The Three-Phase Process

```
Phase 1: PARSE ✅
  Text → VespersService (structure only)

Phase 2: ENRICH ⭐ (NEW)
  VespersService + files → VespersService (fully populated)

Phase 3: RENDER (Next)
  VespersService → LaTeX lines → .tex file
```

## How to Use Now

```python
from vespers_format import parse_universalis_ebook
from vespers_parser import parse_vespers_text
from vespers_enricher import VespersEnricher

# 1. Load and parse
all_services = parse_universalis_ebook('Scripts_2026/uy2026.txt')
all_readings = parse_universalis_ebook('Scripts_2026/uy2026_readings.txt', n_parts=100)

service_name = '12th Sunday in Ordinary Time'
service = parse_vespers_text(
    service_name,
    all_services[service_name],
    all_readings[service_name]
)

# 2. Enrich with external files
enricher = VespersEnricher('psalms', 'antiphons')
service = enricher.enrich(service)

# 3. Now you have everything needed for rendering
print(service.psalms[0].reference)       # "109:1-5,7"
print(service.psalms[0].text[:2])        # First two verses
print(service.psalms[0].tone)            # "1", "8G", etc.
print(service.psalms[0].score_latex)     # LaTeX for antiphon
print(service.magnificat_score_latex)    # LaTeX for magnificat
```

## VespersEnricher Features

### Caching
The enricher caches loaded files to avoid re-reading:
```python
enricher = VespersEnricher('psalms', 'antiphons')

service1 = enricher.enrich(service1)  # Psalm 109 loaded from disk
service2 = enricher.enrich(service2)  # Psalm 109 served from cache

# Clear cache if needed
enricher.clear_cache()
```

### Graceful Failures
Missing files don't crash - they produce warnings and empty strings:
```
Warning: Could not load psalm 123:4-5: File not found
Warning: Could not load tone 9: [...]
```

### Tone Determination
The enricher automatically:
1. Looks for antiphon file (e.g., `O_lux_beáta_Trínitas-1a.gabc`)
2. Extracts tone from filename (`1a`)
3. Falls back to default tone if antiphon not found

## Next Steps (Phase 3)

### Create `VespersRenderer`
Convert enriched `VespersService` to LaTeX:

```python
from renderer import VespersRenderer

renderer = VespersRenderer(header)
latex_lines = renderer.render(service)

# Write to file
with open('output.tex', 'w') as f:
    f.write('\n'.join(latex_lines))
```

The renderer will:
- Break down service into sections (hymn, psalms, readings, etc.)
- Format each section using LaTeX templates
- Handle special formatting (drop caps, accents, etc.)
- Respect the handout style

## Testing Phase 2

Verify the enricher works with your data:

```python
from vespers_format import parse_universalis_ebook
from vespers_parser import parse_vespers_text
from vespers_enricher import VespersEnricher

all_services = parse_universalis_ebook('Scripts_2026/uy2026.txt')
all_readings = parse_universalis_ebook('Scripts_2026/uy2026_readings.txt', n_parts=100)

service = parse_vespers_text(
    '12th Sunday in Ordinary Time',
    all_services['12th Sunday in Ordinary Time'],
    all_readings['12th Sunday in Ordinary Time']
)

enricher = VespersEnricher('psalms', 'antiphons')
service = enricher.enrich(service)

# Check that everything is populated
assert len(service.psalms[0].text) > 0, "Psalm text not loaded"
assert service.psalms[0].tone, "Tone not determined"
assert len(service.psalms[0].score_latex) > 0, "Antiphon score not loaded"
assert len(service.magnificat_score_latex) > 0, "Magnificat score not loaded"

print("✓ All data enriched successfully!")
```

## Benefits of This Structure

✅ **Clean separation of concerns** - Parse, enrich, render are independent  
✅ **Caching** - Efficient reuse of loaded data  
✅ **Testability** - Each phase can be tested in isolation  
✅ **Graceful failures** - Missing files don't crash  
✅ **Extensibility** - Easy to add new enrichment steps  
✅ **No breaking changes** - Old code still works  

## Files Still Using Old Code

- `vespers_format.py` - Still contains all original functions (used by enricher)
- Existing runner scripts - Still work unchanged
- `make_vespers_handout_latex()` - Still works (will be refactored in Phase 3)
