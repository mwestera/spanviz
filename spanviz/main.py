#!/usr/bin/python

import argparse
import sys
import json
import logging
import math
import tempfile
import webbrowser


colors = {  # matplotlib's tab10 palette
    'blue': '#1f77b4',
    'orange': '#ff7f0e',
    'green': '#2ca02c',
    'red': '#d62728',
    'purple': '#9467bd',
    'brown': '#8c564b',
    'pink': '#e377c2',
    'gray': '#7f7f7f',
    'olive': '#bcbd22',
    'cyan': '#17becf',
}


def main():

    argparser = argparse.ArgumentParser(description='Rendering a text with highlighted spans as html.')
    argparser.add_argument('jsonl', nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="jsonl file with text and spans to render (default: stdin)")
    argparser.add_argument('--text', nargs='?', type=str, help="which key in each json record contains the text", default='text')
    argparser.add_argument('--spans', nargs='?', type=str, help="which key contains the spans, in start,end,label format", default='spans')
    argparser.add_argument('--multi', required=False, action='store_true',help="whether they are discontinuous/multispans")
    argparser.add_argument('--serve', required=False, action='store_true', help="whether to serve the html in a browser")

    args = argparser.parse_args()

    outfile = sys.stdout if not args.serve else tempfile.NamedTemporaryFile('w', delete=False, suffix='.html')

    for line in args.jsonl:
        d = json.loads(line)
        text = d[args.text]
        spans = list(standardize_spans(d[args.spans], args.multi))

        html = spans_to_html(text, spans)

        print(f"<p>{html}</p>", file=outfile)

    if args.serve:
        url = 'file://' + outfile.name
        outfile.close()
        webbrowser.open(url)


def update_colormap(colormap: dict, spans: list[dict]):
    for lab in sorted(set(span['label'] for span in spans)):
        if not lab in colormap:
            colormap[lab] = list(colors.values())[len(colormap) % len(colors)]
        if len(colormap) > len(colors):
            logging.warning('Not enough colors available.')


def spans_to_html(text: str, spans: list[dict], colormap={}):  # :)
    update_colormap(colormap, spans)

    starts_and_ends = {0, len(text)}
    for span in spans:
        starts_and_ends.add(span['start'])
        starts_and_ends.add(span['end'])

    starts_and_ends = sorted(starts_and_ends)

    snippets = []

    for start, end in zip(starts_and_ends, starts_and_ends[1:]):
        labels_for_span = set(span['label'] for span in spans if span['start'] <= start and span['end'] >= end)

        if not labels_for_span:
            snippets.append(text[start:end])
            continue

        colors_for_span = [colormap[label] for label in labels_for_span]
        blended_color = colorblend(*colors_for_span)
        hovertext = ','.join(labels_for_span)

        snippets.append(f'<mark style="background-color:{blended_color}" title="{hovertext}";>{text[start:end]}</mark>')

    return ''.join(snippets)


def standardize_spans(s, multi):
    # TODO Make more flexible; and do input validation
    # spans can be {start:, end:, label/tag:} or [1,2,label]
    # if args.multi: {subspans: [{start:, end:,}, {start: end:}], label/tag:}  or [[1,2],[3,4],label]

    for span in s:
        if multi:
            for subspan in span['subspans']:
                yield {'label': span['label'], **subspan}
        else:
            yield span



# Color blender adapted from https://github.com/ChristianChiarulli/colorblender/blob/master/colorblender.py

def hex_to_rgb(hex: str) -> tuple[int, int, int]:
    clean_hex: str = hex.replace("#", "")
    return tuple(int(clean_hex[i : i + 2], 16) for i in (0, 2, 4))


def colorblend(*hexcolors: tuple[str], alphas: list[float] = None) -> str:

    rgb_colors = [hex_to_rgb(hex) for hex in hexcolors]
    alphas = alphas or [1 / len(rgb_colors) for _ in rgb_colors]

    def blend_channel(channel: int) -> int:
        blended_channel: float = sum(alpha * rgb[channel] for alpha, rgb in zip(alphas, rgb_colors))
        return math.floor(min(max(0, blended_channel), 255) + 0.5)

    def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return "#" + "".join(
            ["0{0:x}".format(v) if v < 16 else "{0:x}".format(v) for v in rgb]
        )

    return rgb_to_hex((blend_channel(0), blend_channel(1), blend_channel(2)))


if __name__ == '__main__':
    main()