#!/usr/bin/env python3
"""
CLI script to parse, enrich, and render a Vespers service handout.

Usage:
  python test_parse_enrich.py <all_services> <all_readings> <service_name>

Output:
  <service_name>_handout.tex
"""

import argparse

from vespers_format import parse_universalis_ebook
from vespers_parser import parse_vespers_text
from vespers_enricher import VespersEnricher
from vespers_renderer import VespersRenderer


def build_handout(all_services_path: str, all_readings_path: str, service_name: str) -> str:
    """Parse, enrich, render, and write a handout .tex file for one service."""

    all_services = parse_universalis_ebook(all_services_path)
    all_readings = parse_universalis_ebook(all_readings_path, n_parts=100)

    if service_name not in all_services:
        raise KeyError(f"Service '{service_name}' not found in all_services input")
    if service_name not in all_readings:
        raise KeyError(f"Service '{service_name}' not found in all_readings input")

    service = parse_vespers_text(
        service_name,
        all_services[service_name],
        all_readings[service_name],
    )

    enricher = VespersEnricher('.', 'antiphons')
    service = enricher.enrich(service)

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

    renderer = VespersRenderer(header_file="header.tex")
    handout_lines = renderer.render_handout_lines(d, '.', 'antiphons')

    output_file = f"{service_name}_handout.tex"
    with open(output_file, 'w') as f:
        for line in handout_lines:
            f.write(line + '\n')

    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse, enrich, and render a Vespers handout for a service."
    )
    parser.add_argument('all_services', help='Path to universalis all-services input file')
    parser.add_argument('all_readings', help='Path to universalis all-readings input file')
    parser.add_argument('service_name', help='Exact service name key to render')

    args = parser.parse_args()

    output_file = build_handout(args.all_services, args.all_readings, args.service_name)
    print(f"Wrote handout to {output_file}")


if __name__ == '__main__':
    main()
