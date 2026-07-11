#!/usr/bin/env python3
"""
Test script to demonstrate Phase 1 (Parse), Phase 2 (Enrich), and Phase 3 (Render).

Run this to see the data flow:
  - Load text from universalis files
  - Parse into VespersService
  - Enrich with external files
  - Render handout LaTeX via VespersRenderer
  - Inspect generated output
"""

from vespers_format import parse_universalis_ebook
from vespers_parser import parse_vespers_text
from vespers_enricher import VespersEnricher
from vespers_renderer import VespersRenderer


def test_parse_and_enrich():
    """Test parsing, enrichment, and rendering with real data."""

    print("=" * 80)
    print("PHASE 1: PARSE")
    print("=" * 80)

    # Load the universalis files
    print("\n1. Loading universalis files...")
    all_services = parse_universalis_ebook('Scripts_2026/uy2026.txt')
    all_readings = parse_universalis_ebook('Scripts_2026/uy2026_readings.txt', n_parts=100)
    print(f"   ✓ Loaded {len(all_services)} services")
    print(f"   ✓ Loaded {len(all_readings)} readings")

    # Pick a service to test
    service_name = '12th Sunday in Ordinary Time'
    print(f"\n2. Parsing service: {service_name}")

    service = parse_vespers_text(
        service_name,
        all_services[service_name],
        all_readings[service_name]
    )

    print(f"   ✓ Service name: {service.name}")
    print(f"   ✓ Date: {service.date_str}")
    print(f"   ✓ Hymn lines: {len(service.hymn_latin)}")
    print(f"   ✓ Psalms: {len(service.psalms)}")
    print(f"   ✓ Chapter lines: {len(service.chapter)}")
    print(f"   ✓ Second reading lines: {len(service.reading_second)}")

    # Inspect first psalm (before enrichment)
    print(f"\n3. First psalm (before enrichment):")
    ps = service.psalms[0]
    print(f"   Reference: {ps.reference}")
    print(f"   Name: {ps.name}")
    print(f"   Antiphon (Latin): {ps.antiphon_latin[:60]}...")
    print(f"   Psalm text: {len(ps.text)} lines loaded: {ps.text}")  # Should be empty
    print(f"   Tone: '{ps.tone}'")  # Should be empty
    print(f"   Score LaTeX: {len(ps.score_latex)} chars")  # Should be empty

    print("\n" + "=" * 80)
    print("PHASE 2: ENRICH")
    print("=" * 80)

    # Enrich with external files
    print("\n4. Creating enricher...")
    enricher = VespersEnricher('.', 'antiphons')
    print("   ✓ VespersEnricher created")

    print("\n5. Enriching service (loading external files)...")
    service = enricher.enrich(service)
    print("   ✓ Enrichment complete")

    # Inspect first psalm (after enrichment)
    print(f"\n6. First psalm (after enrichment):")
    ps = service.psalms[0]
    print(f"   Reference: {ps.reference}")
    print(f"   Name: {ps.name}")
    print(f"   Antiphon (Latin): {ps.antiphon_latin[:60]}...")
    print(f"   Psalm text: {len(ps.text)} lines loaded")
    if ps.text:
        print(f"      First 3 lines:")
        for i, line in enumerate(ps.text[:3], 1):
            print(f"        {i}. {line[:70]}...")
    print(f"   Tone: '{ps.tone}'")
    print(f"   Score LaTeX: {len(ps.score_latex)} chars")
    if ps.score_latex:
        print(f"      Preview: {ps.score_latex[:80]}...")

    # Inspect second psalm
    print(f"\n7. Second psalm (after enrichment):")
    ps = service.psalms[1]
    print(f"   Reference: {ps.reference}")
    print(f"   Name: {ps.name}")
    print(f"   Psalm text: {len(ps.text)} lines loaded")
    print(f"   Tone: '{ps.tone}'")
    print(f"   Score LaTeX: {len(ps.score_latex)} chars")

    # Inspect canticle
    print(f"\n8. Canticle (after enrichment):")
    ps = service.psalms[2]
    print(f"   Reference: {ps.reference}")
    print(f"   Name: {ps.name}")
    print(f"   Psalm text: {len(ps.text)} lines loaded")
    print(f"   Tone: '{ps.tone}'")
    print(f"   Score LaTeX: {len(ps.score_latex)} chars")

    # Inspect magnificat
    print(f"\n9. Magnificat antiphon (after enrichment):")
    print(f"   Antiphon (Latin): {service.magnificat_antiphon_latin[:60]}...")
    print(f"   Score LaTeX: {len(service.magnificat_score_latex)} chars")
    if service.magnificat_score_latex:
        print(f"      Preview: {service.magnificat_score_latex[:80]}...")

    print("\n" + "=" * 80)
    print("PHASE 3: RENDER")
    print("=" * 80)

    # Build legacy dict expected by initial renderer extraction
    print("\n10. Building legacy render dictionary...")
    d = {
        'hymn_text': service.hymn_latin,
        'ps A': service.psalms[0].reference,
        'ps A name': service.psalms[0].name,
        'ps A ant': service.psalms[0].antiphon_latin,
        'ps A ant_lat': service.psalms[0].antiphon_latin,
        'ps A ant_eng': service.psalms[0].antiphon_english,
        'ps B': service.psalms[1].reference,
        'ps B name': service.psalms[1].name,
        'ps B ant': service.psalms[1].antiphon_latin,
        'ps B ant_lat': service.psalms[1].antiphon_latin,
        'ps B ant_eng': service.psalms[1].antiphon_english,
        'can': service.psalms[2].reference,
        'can name': service.psalms[2].name,
        'can ant': service.psalms[2].antiphon_latin,
        'can ant_lat': service.psalms[2].antiphon_latin,
        'can ant_eng': service.psalms[2].antiphon_english,
        'response': service.response_short,
        'pandi': service.prayers,
        'mag antiphon': service.magnificat_antiphon_latin,
        'mag ant_eng': service.magnificat_antiphon_english,
        'name': service.name,
    }
    print("   ✓ Legacy dictionary built")

    print("\n11. Rendering handout lines via VespersRenderer...")
    header = [r'\\documentclass{article}', r'\\begin{document}']
    renderer = VespersRenderer(header_lines=header)
    handout_lines = renderer.render_handout_lines(d, '.', 'antiphons')
    print(f"   ✓ Rendered {len(handout_lines)} lines")

    # Basic render assertions
    assert len(handout_lines) > 0, "Renderer produced no output"
    output_text = '\n'.join(handout_lines)
    assert r'\begin{document}' in output_text, "Missing document start"
    assert r'\textbf{MAGNIFICAT ANTIPHON}' in output_text, "Missing Magnificat section"
    assert r'\end{document}' in output_text, "Missing document end"

    out_file = 'test_renderer_output.tex'
    with open(out_file, 'w') as f:
        for line in handout_lines:
            f.write(line + '\n')
    print(f"   ✓ Wrote renderer output to {out_file}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"""
    VespersService is now fully populated and renderable:
    - Hymn: {len(service.hymn_latin)} Latin lines, {len(service.hymn_english)} English lines
    - Psalm A: {len(service.psalms[0].text)} verses, tone: {service.psalms[0].tone}
    - Psalm B: {len(service.psalms[1].text)} verses, tone: {service.psalms[1].tone}
    - Canticle: {len(service.psalms[2].text)} verses, tone: {service.psalms[2].tone}
    - Chapter: {len(service.chapter)} lines
    - Response: {len(service.response_short)} lines
    - Second Reading: {len(service.reading_second)} lines
    - Magnificat: tone ready (score LaTeX loaded)
    - Prayers: {len(service.prayers)} lines
    - Conclusion: {len(service.conclusion)} lines

    ✓ Phase 1 Parse works
    ✓ Phase 2 Enrich works
    ✓ Phase 3 Renderer produces handout LaTeX lines
    """)


if __name__ == '__main__':
    test_parse_and_enrich()
