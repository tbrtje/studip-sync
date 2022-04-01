#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from studip_sync.arg_parser import ARGS
from studip_sync.config_creator import ConfigCreator

if ARGS.init:
    with ConfigCreator() as creator:
        creator.new_config()
    exit()

else:
    from studip_sync.studip_rsync import StudIPRSync
    with StudIPRSync() as s:
        exit(s.sync(ARGS.full, ARGS.recent))

