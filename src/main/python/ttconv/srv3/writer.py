#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""YouTube SRV3 writer"""

import logging
from fractions import Fraction
from typing import List, Optional
import xml.etree.ElementTree as ET

import ttconv.model as model
from ttconv.isd import ISD
from ttconv.filters.isd.merge_paragraphs import ParagraphsMergingISDFilter
from ttconv.filters.isd.merge_regions import RegionsMergingISDFilter
from ttconv.srv3.config import SRV3WriterConfiguration

LOGGER = logging.getLogger(__name__)


class Srv3Paragraph:
  """SRV3 paragraph"""

  def __init__(self):
    self._begin: Optional[Fraction] = None
    self._end: Optional[Fraction] = None
    self._text: str = ""

  def set_begin(self, offset: Fraction):
    self._begin = offset

  def get_begin(self) -> Optional[Fraction]:
    return self._begin

  def set_end(self, offset: Optional[Fraction]):
    self._end = offset

  def get_end(self) -> Optional[Fraction]:
    return self._end

  def is_only_whitespace(self):
    return len(self._text) == 0 or self._text.isspace()

  def normalize_eol(self):
    self._text = "\n".join(line for line in self._text.splitlines() if line)

  def append_text(self, text: str):
    self._text += text

  def to_element(self) -> ET.Element:
    if self._begin is None:
      raise ValueError("SRV3 paragraph begin time must be set")
    if self._end is None:
      raise ValueError("SRV3 paragraph end time must be set")
    p = ET.Element("p")
    begin_ms = int(self._begin * 1000)
    dur_ms = int((self._end - self._begin) * 1000)
    p.set("t", str(begin_ms))
    p.set("d", str(dur_ms))
    s = ET.SubElement(p, "s")
    s.text = self._text
    return p


class Srv3Context:
  """SRV3 writer context"""

  filters: List = (
    RegionsMergingISDFilter(),
    ParagraphsMergingISDFilter(),
  )

  def __init__(self, config: SRV3WriterConfiguration):
    self._paragraphs: List[Srv3Paragraph] = []

  def process_inline_element(self, element: model.ContentElement):
    if isinstance(element, model.Span):
      for child in list(element):
        self.process_inline_element(child)
    elif isinstance(element, model.Br):
      self._paragraphs[-1].append_text("\n")
    elif isinstance(element, model.Text):
      self._paragraphs[-1].append_text(element.get_text())

  def process_p(self, p: model.P, begin: Fraction, end: Optional[Fraction]):
    para = Srv3Paragraph()
    para.set_begin(begin)
    para.set_end(end)
    self._paragraphs.append(para)

    for child in list(p):
      self.process_inline_element(child)

    self._paragraphs[-1].normalize_eol()

    if self._paragraphs[-1].is_only_whitespace():
      LOGGER.debug("Removing empty paragraph.")
      self._paragraphs.pop()

  def add_isd(self, isd: ISD, begin: Fraction, end: Optional[Fraction]):
    LOGGER.debug("Append ISD from %ss to %ss to SRV3 content.", float(begin), float(end) if end is not None else "unbounded")

    for srv_filter in self.filters:
      srv_filter.process(isd)

    is_isd_empty = True

    for region in isd.iter_regions():
      if len(region) > 0:
        is_isd_empty = False
      for body in region:
        for div in list(body):
          for p in list(div):
            self.process_p(p, begin, end)

    if is_isd_empty:
      LOGGER.debug("Skipping empty paragraph.")

  def finish(self):
    if self._paragraphs and self._paragraphs[-1].get_end() is None:
      if self._paragraphs[-1].is_only_whitespace():
        LOGGER.debug("Removing empty unbounded last paragraph.")
        self._paragraphs.pop()
      else:
        LOGGER.warning("Set a default end value to paragraph (begin + 10s).")
        self._paragraphs[-1].set_end(self._paragraphs[-1].get_begin() + Fraction(10))

  def __str__(self) -> str:
    root = ET.Element("timedtext", {"format": "3"})
    body = ET.SubElement(root, "body")
    for p in self._paragraphs:
      body.append(p.to_element())
    xml_str = ET.tostring(root, encoding="unicode")
    return "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" + xml_str


def from_model(doc: model.ContentDocument, config: Optional[SRV3WriterConfiguration] = None, progress_callback=lambda _: None) -> str:
  srv_config = config if config is not None else SRV3WriterConfiguration()
  srv = Srv3Context(srv_config)

  def _isd_progress(progress: float):
    progress_callback(progress / 2)

  isds = list(ISD.generate_isd_sequence(doc, _isd_progress))

  for i, (begin, isd) in enumerate(isds):
    end = isds[i + 1][0] if i + 1 < len(isds) else None
    srv.add_isd(isd, begin, end)
    progress_callback(0.5 + (i + 1) / len(isds) / 2)

  srv.finish()

  return str(srv)
