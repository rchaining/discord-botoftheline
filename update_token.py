import yaml
import sys

import logging
logging.basicConfig(format = '%(levelname)s:%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # usage:
    #  python update_token <config file name> <field>:<field data>
    args = sys.argv
    logger.info('Args: %s'%args)

    fname = args[1]
    field = args[2].split(':')[0]
    data = args[2].split(':')[1]

    with open(fname, 'r') as f:
        conf = yaml.load(f)
    conf[field] = data
    with open(fname, 'w') as f:
        yaml.dump(conf, f)

main()