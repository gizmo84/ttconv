#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""SRV3 writer configuration"""
from __future__ import annotations

from dataclasses import dataclass
from ttconv.config import ModuleConfiguration

@dataclass
class SRV3WriterConfiguration(ModuleConfiguration):
  """SRV3 writer configuration"""

  @classmethod
  def name(cls):
    return "srv3_writer"
