#!/usr/bin/env python3
import bs4
import urllib.request
import subprocess
import time
import sys
import re
import logging


__author__ = "Ignacio Quezada"

__version__ = "0.1"
__maintainer__ = "Ignacio Quezada"
__email__ = "dreamtrick@gmail.com"
__status__ = "dev"

user_agent = 'Arenavision for Linux Launcher v0.1'
headers = {'user-agent': user_agent}

# Logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)   # logging.WARNING


class Event:
    """Event object"""
    def __init__(self, day, event_time, zone, event_type, name, league, channels):
        self.time = event_time
        self.day = day
        self.zone = zone
        self.type = event_type
        self.name = name
        self.league = league
        self.channels = channels

    def __str__(self):
        return "%s %s - [%s] %s (%s)" % (self.day, self.time, self.type, self.name, '/'.join(self.channels))

    def __repr__(self):
        return "%s %s - [%s] %s (%s)" % (self.day, self.time, self.type, self.name, '/'.join(self.channels))


def get_soup(url):
    req = urllib.request.Request(url, headers=headers)
    html = urllib.request.urlopen(req).read()
    soup = bs4.BeautifulSoup(html, "html.parser")
    return soup


def parse_agenda(soup):
    chart = soup.find_all("div", class_="content")[0].find_all("p")[1]
    event_list = []
    for event in chart.get_text().split('\n'):
        channels = re.findall('(AV2[1-9])', event)  # If there are any sopcast channels, list them.
        channels.extend(re.findall('(AV3[0-6])', event))  # Find channels 21-36
        if channels:
            day, event_time, zone = event.split(': ')[0].split(' ')[:3]
            event_type = ' '.join(event.split(': ')[0].split(' ')[3:])
            name = event.split(': ')[1].split(' (')[0]
            league = re.search("(?<=\().*(?=\))", event).group(0)
            event_list.append(Event(day, event_time, zone, event_type, name, league, channels))
    return event_list


def get_agenda():
    url = 'http://arenavision.in/agenda'
    logger.debug("Fetching Agenda from: %s", url)
    try:
        soup = get_soup(url)
        agenda = parse_agenda(soup)
    except:
        logger.error("Something changed in the agenda, an update is needed.")
        sys.exit(1)
    return agenda


def parse_channel(soup):
    sopcast = soup.find_all("div", class_="auto-style2")[0].find_all("a")[2]['href']
    return sopcast


def get_sopcast(channel):
    url = 'http://arenavision.in/' + str(channel)
    logger.debug("Fetching sopcast link from: %s", url)
    try:
        soup = get_soup(url)
        sopcast = parse_channel(soup)
    except:
        logger.error("Something changed in the channel page, an update is needed.")
        sys.exit(1)
    return sopcast


def start_sopcast(sopcast, p2p, port):
    cmd = ["sp-sc-auth", sopcast, p2p, port]
    logger.info("Running Sopcast...")
    logger.debug(" ".join([sopcast, p2p, port]))
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL)


def start_player(player, port):
    cmd = [player, "--quiet", "http://localhost:%s/tv.asf" % port]
    # returncode
    logger.info("Running %s.", player)
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cli_match(event_list):
    for i, e in enumerate(event_list):
        print("[%s] %s" % (i, e))
    choice = input("Choose number [0-%d] or [q] to quit: " % i)
    if choice == 'q':
        print("Bye bye.")
        sys.exit(0)
    try:
        choice = int(choice)
        logger.debug("Choice from agenda: %d", choice)
        return [0 <= int(choice) <= i, int(choice)]
    except (IndexError, ValueError):
        logger.error("Wrong input, try again.")
        return [False, choice]


def cli_channel(match):
    logger.debug("Channels available for chosen match: %s", ' - '.join(match.channels))
    # if len(match.channels) > 1:
    for i, e in enumerate(match.channels):
        print("[%s] %s" % (i, e))
    if i == 0:
        choice = input("Choose channel [0] or [q] to quit: ")
    else:
        choice = input("Choose channel [0-%d] or [q] to quit: " % i)
    # else:
    #    choice = 0
    #    return [True, choice]
    try:
        if choice == "q":
            print("Bye bye.")
            sys.exit(0)
        choice = int(choice)
        logger.debug("Chosen channel: %s", match.channels[choice])
        return [0 <= int(choice) <= i, choice]
    except (IndexError, ValueError):
        logger.error("Wrong input, try again.")
        return [False, choice]


def cli(event_list, config):
    while True:
        check, choice = cli_match(event_list)
        if not check:
            logger.error("Failed to get match.")
            input("Press enter to try again...")
            continue
        match = event_list[choice]
        while True:
            check, choice = cli_channel(match)
            if not check:
                logger.error("Failed to get channel.")
                input("Press enter to try again...")
                continue
            sopcast = get_sopcast(match.channels[choice])
            logger.debug("Sopcast link: %s", sopcast)
            print("Opening sopcast stream.")
            p_sopcast = start_sopcast(sopcast, config['sopcast-p2p-port'], config['sopcast-stream-port'])
            # sopcast exit code 152: error with the stream, try another one.
            # code 147, sopcast exit.
            logger.info("Going to sleeping %s seconds for cache.", config['cold-start-time'])

            counter = 0
            while not p_sopcast.poll():
                ct = 0
                while ct < int(config['cold-start-time']) and not p_sopcast.poll():
                    print('.', end="", flush=True)
                    time.sleep(1)
                    ct += 1
                print()
                if not p_sopcast.poll():
                    print("Opening player.")
                    p_player = start_player(config['video-player'], config['sopcast-stream-port'])
                    if p_player.returncode == 0:
                        logger.info("Closed player, closing Sopcast, returning to channel menu.")
                        p_sopcast.kill()
                if counter > 3:
                    break
                counter += 1
            if p_sopcast.poll() > 0:
                logger.error("Sopcast closed with code %d. Back to channel menu." % p_sopcast.poll())
            else:
                print("Sopcast closed.")
                logger.info("Sopcast closed.")


def gui(event_list, config):
    return event_list, config
