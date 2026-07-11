from __future__ import annotations

from typing import Any

from vespers_format import (
    format_hymn_tex,
    get_antiphon_tex,
    get_psalm_file,
    format_psalm_tex,
)


class VespersRenderer:
    """
    Phase 3 renderer (initial extraction from make_vespers_handout_latex).

    This class currently renders from the legacy dict structure `d` to preserve
    behavior while we migrate to VespersService-based rendering.
    """

    def __init__(
        self,
        header_lines: list[str] | None = None,
        header_file: str | None = None,
    ):
        if header_lines is not None:
            self.header_lines = header_lines
        elif header_file is not None:
            with open(header_file, "r", encoding="utf-8") as f:
                self.header_lines = [line.rstrip("\n") for line in f]
        else:
            self.header_lines = [r"\documentclass{article}", r"\begin{document}"]

    def render_handout_lines(
        self,
        d: dict[str, Any],
        psalm_dir: str,
        antiphon_dir: str,
    ) -> list[str]:
        hymn = format_hymn_tex(d["hymn_text"])
        hymn_tone = get_antiphon_tex(
            antiphon_dir,
            d["hymn_text"][0].strip().replace(",", ""),
            handout=True,
            hymn=True,
        )

        psalms: list[list[str]] = []
        for ps in ["ps A", "ps B", "can"]:
            psalm_text_raw, default_tone = get_psalm_file(psalm_dir, d[ps], tex=True)

            # if there is an antiphon gabc file, use mode from that instead of default
            psalm_antiphon, ant_tone = get_antiphon_tex(
                antiphon_dir, d[ps + " ant"], determine_tone=True
            )
            if psalm_antiphon == "":
                tone = get_antiphon_tex(antiphon_dir, default_tone, handout=True)
            else:
                tone = get_antiphon_tex(antiphon_dir, ant_tone, handout=True)

            # reduce accents according to tone:
            if ant_tone == "":
                tone_num = default_tone[0]
            else:
                tone_num = ant_tone[0]
                if ant_tone == "2*a":
                    tone_num = ant_tone

            psalm_tex = format_psalm_tex(
                psalm_text_raw, tone_num, drop_cap=True, handout=True
            )

            psalms.append(
                [
                    r"\newpage",
                    r"\textbf{" + d[ps] + r"} \hfill \textit{" + d[ps + " name"] + r"}\\",
                    r"\begin{multicols}{2}",
                    d[ps + " ant_lat"] + r"\\",
                    tone,
                    r"\newcolumn",
                    d[ps + " ant_eng"] + r"\\",
                    r"\end{multicols}\begin{multicols}{2}",
                ]
                + psalm_tex
                + [r"\\", r"\leftskip=0pt", r"\end{multicols}"]
            )

        lines = d["response"][:]
        response_text = lines[0].replace("–", "").replace("—", "").strip()
        lines = d["pandi"][:]
        resp_pandi = lines[-2]

        responses = [
            r"\begin{multicols}{2}",
            r"\textbf{RESPONSES} \\",
            r"\textit{First reading}\\",
            r"\textbf{\Responsorium " + response_text + r"}\\",
            r"\newcolumn",
            r"\textit{Prayers and Intercessions}\\",
            r"\textbf{\Responsorium " + resp_pandi + r"}\\",
            r"\end{multicols}",
        ]

        mag_ant = [
            r"\begin{multicols}{2}",
            r"\textbf{MAGNIFICAT ANTIPHON} \\",
            d["mag antiphon"],
            r"\newcolumn",
            d["mag ant_eng"],
            r"\end{multicols}",
        ]

        footer = [
            r"\vfill",
            r"\begin{center}",
            r"\textit{\small " + d["name"] + "}",
            r"\end{center}",
            "}",
            r"\end{document}",
        ]

        handout = (
            self.header_lines
            + [r"\setcounter{page}{3}", r"{\fontsize{18}{20}\selectfont"]
            + [hymn_tone]
            + hymn
            + ["}", r"\grechangedim{spacelinestext}{8mm}{scalable}", r"{\fontsize{20}{22}\selectfont"]
            + psalms[0]
            + psalms[1]
            + psalms[2]
            + responses
            + mag_ant
            + [""]
            + footer
        )
        return handout

    def write_handout(
        self,
        d: dict[str, Any],
        fn_handout: str,
        psalm_dir: str,
        antiphon_dir: str,
    ) -> None:
        handout = self.render_handout_lines(d, psalm_dir, antiphon_dir)
        with open(fn_handout, "w") as file:
            for line in handout:
                file.write(line + "\n")
