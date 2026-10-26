"""Render display math embedded in Markdown paragraphs without editing the source.

Arithmatex's block processor expects $$...$$ to occupy a complete block.
Original book prose also puts it inside quotes/list items without blank lines.
Capture those remaining spans before emphasis or backslash escapes alter TeX.
"""
from xml.etree import ElementTree

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.util import AtomicString


class EmbeddedDisplayMath(InlineProcessor):
    def handleMatch(self, match, data):
        element = ElementTree.Element("span", {"class": "arithmatex math-display"})
        element.text = AtomicString("\\[" + match.group(1) + "\\]")
        return element, match.start(0), match.end(0)


class DisplayMathExtension(Extension):
    def extendMarkdown(self, md):
        md.registerExtension(self)
        # Backtick code (190) is protected first; arithmatex inline (189.9) next.
        md.inlinePatterns.register(
            EmbeddedDisplayMath(r"(?<!\\)\$\$(.+?)(?<!\\)\$\$", md),
            "embedded-display-math", 189.95,
        )


def makeExtension(**kwargs):
    return DisplayMathExtension(**kwargs)
