#!/usr/bin/env python3
"""File registry to encapsulate file system related operations."""

import glob
import os
import sys

import pathspec

from ansibledoctor.Config import SingleConfig
from ansibledoctor.Contstants import YAML_EXTENSIONS
from ansibledoctor.Utils import SingleLog


class Registry:

    _doc = {}
    log = None
    config = None

    def __init__(self):
        self._doc = []
        self.config = SingleConfig()
        self.log = SingleLog().logger
        self._scan_for_yamls()

    def get_files(self):
        return self._doc

    def _scan_for_yamls(self):
        """
        Search for the yaml files in each project/role root and append to the corresponding object.

        :param base: directory in witch we are searching
        :return: None
        """
        extensions = YAML_EXTENSIONS
        base_dir = self.config.base_dir
        role_name = os.path.basename(base_dir)
        excludes = self.config.config.get("exclude_files")
        excludespec = pathspec.PathSpec.from_lines("gitwildmatch", excludes)

        self.log.debug("Scan for files: " + base_dir)

        for extension in extensions:
            pattern = os.path.join(base_dir, "**/*." + extension)
            for filename in glob.iglob(pattern, recursive=True):
                if not excludespec.match_file(filename):
                    self.log.debug("Adding file to '{}': {}".format(role_name, os.path.relpath(filename, base_dir)))
                    self._doc.append(filename)
                else:
                    self.log.debug("Excluding file: {}".format(os.path.relpath(filename, base_dir)))
