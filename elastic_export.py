#!/usr/bin/env python3

import os
import csv
import statistics

from datetime import datetime
from elasticsearch_dsl import Document, Date, Object, Text, Integer, Double
from elasticsearch_dsl.connections import connections

class CmdPerf(Document):
  start_date = Date(default_timezone="UTC")
  end_date = Date(default_timezone="UTC")
  elapsed_time = Integer()
  cmd = Text()
  options = Text()

  class Index:
    name = "cmd_perf"

  def save(self, **kwargs):
    self.created_at = datetime.utcnow()
    return super().save(**kwargs)

def send_cmd_perf_to_elastic(cmd, options, start_date, end_date):
  cmd_perf = CmdPerf()
  cmd_perf.cmd = cmd
  cmd_perf.options = options
  cmd_perf.start_date = start_date
  cmd_perf.end_date = end_date
  td = end_date - start_date
  cmd_perf.elapsed_time = td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6
  cmd_perf.save()

def parse_options(option_file):
  with open(option_file, newline="") as fp:
    reader = csv.DictReader(fp, delimiter=",")
    for row in reader:
      return row

def init_elastic_models():
  CmdPerf.init()

def init_elastic(host="localhost"):
  connections.create_connection(host=host)
  init_elastic_models()
