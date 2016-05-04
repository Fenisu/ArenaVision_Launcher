import arenavision
import argparse
import configparser
import logging
import os
import sys


__author__ = "Ignacio Quezada"

__version__ = "0.1"
__maintainer__ = "Ignacio Quezada"
__email__ = "dreamtrick@gmail.com"
__status__ = "dev"

############
# start internal config
#
# path to config file
#  '.config/arenavision_linux'
config_path = '.config/arenavision_linux'
config_path = os.path.join(os.path.expanduser("~"), config_path)
# name of config file
config_file = 'arenavision_linux.ini'
#
# Logging
logger = logging.getLogger('arenavision_main')
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)
# end internal config
############


def gui(config):
    logger.error("GUI not implemented yet.")
    agenda = arenavision.get_agenda()
    arenavision.gui(agenda, config)


def cli(config):
    agenda = arenavision.get_agenda()[0:10]   # Force only 10 first items
    arenavision.cli(agenda, config)


def cliparse():
    parser = argparse.ArgumentParser(description='Launch Arenavision')
    parser.add_argument('--gui', dest='gui', action='store_true',
                        help='Run with gui (default: run with cli)')
    parser.add_argument('--debug', dest='verbose', action='store_true',
                        help='Debug mode')
    parser.set_defaults(gui=False)
    parser.set_defaults(verbose=False)
    args = parser.parse_args()
    return args


def createconfig():
    logger.info("Creating config file.")
    config = configparser.ConfigParser()
    config['settings'] = {'video-player': 'mpv',
                          'cold-start-time': '15',
                          'sopcast-stream-port': '3908',
                          'sopcast-p2p-port': '8908'}
    try:
        if not os.path.isdir(config_path):
            os.makedirs(config_path)
        with open(os.path.join(config_path, config_file), 'w') as cfgfile:
            config.write(cfgfile)
    except:
        logger.error("Config file creation failed")
        sys.exit(1)
    return config


def readconfig():
    logger.info("Reading config file.")
    if os.path.exists(os.path.join(config_path, config_file)):
        logger.debug("Config file exists, reading")
        config = configparser.ConfigParser()
        config.read(os.path.join(config_path, config_file))
    else:
        logger.debug("Config file does NOT exist.")
        config = createconfig()
    return config


def main():
    args = cliparse()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    config = readconfig()
    if args.gui:
        gui(config)
    else:
        cli(config['settings'])


if __name__ == '__main__':
    main()
