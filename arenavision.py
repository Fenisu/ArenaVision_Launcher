#!/usr/bin/env python3
import bs4
import logging
import re
import socket
import subprocess
import sys
import time
import urllib.request


__author__ = "Ignacio Quezada"

__version__ = "0.2"
__maintainer__ = "Ignacio Quezada"
__email__ = "dreamtrick@gmail.com"
__status__ = "dev"

user_agent = 'Arenavision for Linux Launcher v0.1'
headers = {'user-agent': user_agent}

NO_SOPCAST_SUPPORT = "Not working"

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


def old_parse_agenda(soup):
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


def parse_agenda(soup):
    chart = soup.find('table').find_all('tr')[1:11]
    event_list = []
    for event in chart:
        event = event.find_all('td')
        chan_list = event[5].text.upper()
        languages = re.findall('\[[A-Z]{3}\]', chan_list)
        channels = []
        last_pos = 0
        for lang in languages:
            new_pos = chan_list.find(lang)
            sopcast_channels = re.findall('S[1-9]|S[0-7]', chan_list[last_pos:new_pos])
            if sopcast_channels:
                channels.append(lang)
                channels.extend(sopcast_channels)
            last_pos = new_pos

        if channels:
            day = event[0].text
            event_time, zone = event[1].text.split(' ')
            event_type = event[2].text
            league = event[3].text
            name = event[4].text.replace('\n\t\t', ' ')
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
        logger.error("Please report the issue: https://github.com/Fenisu/ArenaVision_Launcher/issues")
        sys.exit(1)
    return agenda


def parse_channel(soup):
    sopcast = soup.find_all("div", class_="auto-style2")[0].find_all("a")[2]['href']
    return sopcast


def get_sopcast(channel):
    url = 'http://arenavision.in/av' + str(channel)
    logger.debug("Fetching sopcast link from: %s", url)
    try:
        soup = get_soup(url)
        sopcast = parse_channel(soup)
    except:
        logger.error("Something changed in the channel page, an update is needed.")
        logger.error("Please report the issue: https://github.com/Fenisu/ArenaVision_Launcher/issues")
        sys.exit(1)
    return sopcast


def start_sopcast(sopcast, p2p, port):
    cmd = ["sp-sc-auth", sopcast, p2p, port]
    logger.info("Running Sopcast...")
    logger.debug(" ".join([sopcast, p2p, port]))
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL)


def start_player(player, port):
    cmd = [player, "--quiet", "http://localhost:%s/tv.asf" % port]
    # return code
    logger.info("Running %s.", player)
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_ip():
    return [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1],
                       [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in
                         [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]


def cli_match(event_list):
    for i, e in enumerate(event_list):
        print("[%s] %s" % (i, e))
    try:
        choice = input("Choose number [0-%d] or [q] to quit: " % i)
    except UnboundLocalError:
        logger.error("Something changed in the agenda, an update is needed.")
        logger.error("Please report the issue: https://github.com/Fenisu/ArenaVision_Launcher/issues")
        sys.exit(1)
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
    lang = "[ENG]"
    for i, e in enumerate(match.channels):
        if e.find('[') > -1:
            lang = e
        else:
            print("[%s] %s %s" % (i, e, lang))
    if i == 1:
        choice = input("Choose channel [1] or [q] to quit: ")
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


def cli(event_list, config, server_mode):
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

            counter = 0
            while not p_sopcast.poll():
                ct = 0
                logger.info("Going to sleeping %s seconds for cache.", config['cold-start-time'])
                while ct < int(config['cold-start-time']) and not p_sopcast.poll():
                    print('.', end="", flush=True)
                    time.sleep(1)
                    ct += 1
                print()
                if not p_sopcast.poll() and not server_mode:
                    print("Opening player.")
                    p_player = start_player(config['video-player'], config['sopcast-stream-port'])
                    if p_player.returncode == 0:
                        logger.info("Closed player, closing Sopcast, returning to channel menu.")
                        p_sopcast.kill()
                elif not p_sopcast.poll() and server_mode:
                    print("Stream available at: http://{}:{}/tv.asf".format(get_ip(), config['sopcast-stream-port']))
                    input("Press enter to stop stream.")
                    p_sopcast.kill()
                if counter > 3 and not server_mode:
                    p_sopcast.kill()
                counter += 1
            if p_sopcast.poll() > 0:
                logger.error("Sopcast closed with code %d. Back to channel menu." % p_sopcast.poll())
            else:
                print("Sopcast closed.")
                logger.info("Sopcast closed.")


def gui(event_list, config):
    return event_list, config
