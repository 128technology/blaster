#!/usr/bin/env python3

import argparse
from base64 import b64encode
from gzip import compress
from jinja2 import Environment, FileSystemLoader
import json
import os
import sys
from uuid import uuid4
import yaml


def parse_arguments():
    """Get commandline arguments."""
    parser = argparse.ArgumentParser(
        description='Generate a quickstart file for 128T OTP')
    parser.add_argument('--parameters', '-p', required=True,
                        help='parameters file')
    parser.add_argument('--quickstart', '-q', required=True,
                        help='quickstart file')
    parser.add_argument('--template', '-t', default='quickstart.template',
                        help='template file (default: quickstart.template)')
    parser.add_argument('--workdir', '-w', default='.',
                        help='working directory (default: current dir)')
    parser.add_argument('--xml', '-x', action='store_true',
                        help='print xml config to stdout')
    return parser.parse_args()


def error(*messages):
    """Show error message and quit."""
    print('Error:', *messages)
    sys.exit(1)


def read_parameters(file_name, work_dir='.'):
    """Read parameters from yaml file."""
    cur_dir = os.getcwd()
    os.chdir(work_dir)
    with open(file_name) as f:
        parameters = yaml.safe_load(f)
    os.chdir(cur_dir)
    return parameters


def generate_quickstart(parameters, template_name, xml):
    """Generate quickstart file based on template and parameters."""
    dir = os.path.dirname(template_name)
    file = os.path.basename(template_name)
    env = Environment(loader=FileSystemLoader(dir))
    template = env.get_template(file)
    # add additional parameters
    parameters['has_management'] = True
    if 'interfaces' in parameters:
        parameters['has_lte'] = 'lte' in [
            i.get('type') for i in parameters['interfaces']]
        management = [i.get('management', False) for i in parameters['interfaces']]
        if management.count(True) > 1:
            error('There is only one management interface allowed.')
        parameters['has_management'] = any(management)
    parameters['authority_id'] = uuid4()
    parameters['asset_id'] = uuid4()
    xml_config = template.render(**parameters)
    if xml:
        print('xml_config:', xml_config)
    quickstart = {
        'n': 'generic-quickstart-router',
        'a': None,
        'c': b64encode(compress(bytes(xml_config, 'ascii'))).decode('ascii'),
    }
    return quickstart


def write_quickstart_file(quickstart, filename, work_dir='.'):
    """Write a quickstart document in json format to file."""
    os.chdir(work_dir)
    with open(filename, 'w') as fd:
        json.dump(quickstart, fd)


def main():
    args = parse_arguments()
    parameters = read_parameters(args.parameters, args.workdir)
    quickstart = generate_quickstart(parameters, args.template, args.xml)
    write_quickstart_file(quickstart, args.quickstart, args.workdir)


if __name__ == '__main__':
    main()
