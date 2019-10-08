#!/usr/bin/env python3
"""Prepare output and write compiled jinja2 templates."""

import codecs
import glob
import json
import ntpath
import os
import pprint
import sys
from functools import reduce

import jinja2.exceptions
import ruamel.yaml
from jinja2 import Environment
from jinja2 import FileSystemLoader
from six import binary_type
from six import text_type

import ansibledoctor.Exception
from ansibledoctor.Config import SingleConfig
from ansibledoctor.Utils import FileUtils
from ansibledoctor.Utils import SingleLog


class Generator:
    def __init__(self, doc_parser):
        self.template_files = []
        self.extension = "j2"
        self._parser = None
        self.config = SingleConfig()
        self.log = SingleLog()
        self.logger = self.log.logger
        self.logger.info("Using template dir: " + self.config.get_template())
        self._parser = doc_parser
        self._scan_template()

    def _scan_template(self):
        """
        Search for Jinja2 (.j2) files to apply to the destination.

        :return: None
        """
        base_dir = self.config.get_template()

        for file in glob.iglob(base_dir + "/**/*." + self.extension, recursive=True):

            relative_file = file[len(base_dir) + 1:]
            if ntpath.basename(file)[:1] != "_":
                self.logger.debug("Found template file: " + relative_file)
                self.template_files.append(relative_file)
            else:
                self.logger.debug("Ignoring template file: " + relative_file)

    def _create_dir(self, directory):
        if not self.config.dry_run:
            os.makedirs(directory, exist_ok=True)
        else:
            self.logger.info("Creating dir: " + directory)

    def _write_doc(self):
        files_to_overwite = []

        for file in self.template_files:
            doc_file = os.path.join(self.config.config.get("output_dir"), os.path.splitext(file)[0])
            if os.path.isfile(doc_file):
                files_to_overwite.append(doc_file)

        if len(files_to_overwite) > 0 and self.config.config.get("force_overwrite") is False:
            if not self.config.dry_run:
                self.logger.warn("This files will be overwritten:")
                print(*files_to_overwite, sep="\n")

                try:
                    FileUtils.query_yes_no("Do you want to continue?")
                except ansibledoctor.Exception.InputError:
                    self.log.sysexit_with_message("Aborted...")

        for file in self.template_files:
            doc_file = os.path.join(self.config.config.get("output_dir"), os.path.splitext(file)[0])
            source_file = self.config.get_template() + "/" + file

            self.logger.debug("Writing doc output to: " + doc_file + " from: " + source_file)

            # make sure the directory exists
            self._create_dir(os.path.dirname(os.path.realpath(doc_file)))

            if os.path.exists(source_file) and os.path.isfile(source_file):
                with open(source_file, "r") as template:
                    data = template.read()
                    if data is not None:
                        try:
                            # print(json.dumps(self._parser.get_data(), indent=4, sort_keys=True))
                            jenv = Environment(loader=FileSystemLoader(self.config.get_template()), lstrip_blocks=True, trim_blocks=True)
                            jenv.filters["to_nice_yaml"] = self._to_nice_yaml
                            jenv.filters["deep_get"] = self._deep_get
                            data = jenv.from_string(data).render(self._parser.get_data(), role=self._parser.get_data())
                            if not self.config.dry_run:
                                with open(doc_file, "wb") as outfile:
                                    outfile.write(data.encode("utf-8"))
                                    self.logger.info("Writing to: " + doc_file)
                            else:
                                self.logger.info("Writing to: " + doc_file)
                        except (jinja2.exceptions.UndefinedError, jinja2.exceptions.TemplateSyntaxError)as e:
                            self.log.sysexit_with_message(
                                "Jinja2 templating error while loading file: '{}'\n{}".format(file, str(e)))
                        except UnicodeEncodeError as e:
                            self.log.sysexit_with_message(
                                "Unable to print special characters\n{}".format(str(e)))

    def _to_nice_yaml(self, a, indent=4, *args, **kw):
        """Make verbose, human readable yaml."""
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=indent, sequence=(indent * 2), offset=indent)
        stream = ruamel.yaml.compat.StringIO()
        yaml.dump(a, stream, **kw)
        return stream.getvalue().rstrip()

    def _deep_get(self, _, dictionary, keys, *args, **kw):
        default = None
        return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."), dictionary)

    def render(self):
        self.logger.info("Using output dir: " + self.config.config.get("output_dir"))
        self._write_doc()
