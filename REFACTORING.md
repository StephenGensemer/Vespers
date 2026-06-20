# Refactoring: Dataclass Structure

This branch introduces a clean separation between data parsing, external file loading, and LaTeX rendering.

## New Files

### `vespers_data.py`
Defines the canonical data structures:
- **`Psalm`** - A single psalm/canticle with reference, name, antiphons, and optional loaded data (text, tone, score)
- **`VespersService`** - Complete service for one day with all sections (hymn, psalms, readings, etc.)
- **`to_filename()`** - Generates consistent output filenames

**Key idea**: These dataclasses are the "contract" between parsing, enrichment, and rendering. Everything flows through `VespersService`.

### `vespers_parser.py`
Extracts text from the universalis ebook format into `VespersService`:
- **`parse_vespers_text(service_name, parts)`** - Main entry point
- **`_extract_all_data()`** - Consolidates all existing parsing logic

**Key idea**: Parser only reads text - it does NOT load external files. Psalm objects are created with empty `text` and `tone` fields, which get filled later by the enricher.

## How to Use (Now)

Currently, the old code still works. To use the new structure:

```python
from vespers_format import parse_universalis_ebook
from vespers_parser import parse_vespers_text

# 1. Parse the year file (existing code)
all_services = parse_universalis_ebook('Scripts_2026/uy2026.txt')
parts = all_services['12th Sunday in Ordinary Time']

# 2. Parse to VespersService (NEW)
service = parse_vespers_text('12th Sunday in Ordinary Time', parts)

# 3. Inspect the structured data
print(service.name)           # "12th Sunday in Ordinary Time"
print(service.date_str)       # "21 June 2026"
print(len(service.psalms))    # 3
print(service.psalms[0].reference)  # "109:1-5,7"
```

## Next Steps (Phases 2-4)

### Phase 2: Create `VespersEnricher`
Load external files (psalm texts, antiphon scores) and attach to service:

```python
from enricher import VespersEnricher

enricher = VespersEnricher('psalms', 'antiphons')
service = enricher.enrich(service)

# Now service.psalms[0].text is populated
# And service.psalms[0].tone is determined
```

### Phase 3: Refactor `VespersRenderer`
Convert `VespersService` to LaTeX lines:

```python
from renderer import VespersRenderer

renderer = VespersRenderer(header)
latex_lines = renderer.render(service)
```

### Phase 4: Simple Runner Script
All together:

```python
# run_vespers.py
service = parse_vespers_text(service_name, parts)
service = enricher.enrich(service)
latex = renderer.render(service)
```

## Testing the New Code

You can test that the parsing produces the same data as before:

```python
# Old way
d = get_vespers_data_universalis(name, parts)

# New way
service = parse_vespers_text(name, parts)

# Compare (before enrichment):
assert service.name == d['name']
assert service.date_str == d['date_string']
assert service.psalms[0].reference == d['ps A']
assert service.psalms[0].name == d['ps A name']
# ... etc
```

## Benefits of This Structure

✅ **Type safety** - IDEs can auto-complete and catch mistakes  
✅ **Clarity** - Data flow is explicit: parse → enrich → render  
✅ **Testability** - Each step can be tested in isolation  
✅ **Extensibility** - Adding new sections (e.g., Lauds) just requires adding fields to `VespersService`  
✅ **Reusability** - Same `VespersService` can be rendered to HTML, PDF, etc.  
✅ **No breaking changes** - Old code still works; this is additive  

## Files Still Using Old Code

- `vespers_format.py` - Still contains all parsing functions (unchanged for now)
- Existing runner scripts - Still work unchanged

These will be refactored in phases 2-4.
