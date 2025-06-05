#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Unit tests for the SRV3 writer"""

import unittest
from fractions import Fraction

from ttconv.model import ContentDocument, Region, Body, Div, P, Span, Text
import ttconv.srv3.writer as srv3_writer

class Srv3WriterTest(unittest.TestCase):

  def test_srv3_writer(self):
    doc = ContentDocument()

    r1 = Region("r1", doc)
    doc.put_region(r1)

    body = Body(doc)
    doc.set_body(body)

    div = Div(doc)
    body.push_child(div)

    p = P(doc)
    p.set_region(r1)
    p.set_end(Fraction(2))
    div.push_child(p)

    span = Span(doc)
    span.push_child(Text(doc, "Lorem ipsum dolor sit amet,"))
    p.push_child(span)

    p = P(doc)
    p.set_region(r1)
    p.set_begin(Fraction(2))
    p.set_end(Fraction(4))
    div.push_child(p)

    span = Span(doc)
    span.push_child(Text(doc, "consectetur adipiscing elit."))
    p.push_child(span)

    expected = (
      '<?xml version="1.0" encoding="utf-8"?>\n'
      '<timedtext format="3"><body>'
      '<p t="0" d="2000"><s>Lorem ipsum dolor sit amet,</s></p>'
      '<p t="2000" d="2000"><s>consectetur adipiscing elit.</s></p>'
      '</body></timedtext>'
    )

    srv3_from_model = srv3_writer.from_model(doc)
    self.assertEqual(expected, srv3_from_model)

if __name__ == '__main__':
  unittest.main()
