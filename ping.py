import configparser
import json
import sys
import requests
import datetime
import logging
import smtplib
import os


def json_output(data):
    """Helper function for outputting json file that contains site state after check"""
    with open(os.path.dirname(sys.argv[0]) + "/" + 'sites_state.json', 'w') as outfile:
        json.dump(data, outfile)


def json_read():
    """Helper function for reading json file with previous state of web-sites"""
    try:
        with open(os.path.dirname(sys.argv[0]) + "/" + 'sites_state.json') as json_file:
            data = json.load(json_file)
        return data
    except FileNotFoundError:
        return None


def send_email(config, site, status_code, time, back=False):
    """Helper function for sending emails"""
    recipients = json.loads(config['RECIPIENTS']['EMAILS'])
    smtp_server = config['EMAIL']['SMTP_SERVER']
    port = config['EMAIL']['PORT']
    from_email = config['EMAIL']['FROM_EMAIL']
    password = config['EMAIL']['PASSWORD']
    logging.basicConfig(filename=config['LOG']['EMAIL'], level=logging.WARN)

    try:
        server = smtplib.SMTP_SSL(smtp_server, port)
        server.ehlo()  # Can be omitted
        server.login(from_email, password)
        for recipient in recipients:
            message = "\r\n".join([
                "From: {}".format(from_email),
                "To: {}".format(recipient),
                "Subject: {} {}".format(site, 'BACK ONLINE' if back else 'IS DOWN'),
                "",
                'Resource {} \nresponded with {} at {}'.format(site, status_code, time)
            ])
            if back:
                message += "\nResource is BACK ONLINE!"
            server.sendmail(from_email, recipient, message)
    except Exception as e:
        logging.error(' {} — {}'.format(time, e))
    finally:
        server.quit()


def ping(cfg):
    """
    Main function that goes through every site specified in config.ini
    and tries to reach it. If site can not be reached or responds with status code
    other than 200, function will notify user via email. If the web-site stays down
    for two checks in a row, you will not get notification that site is down.
    After next check, if site goes back online, user will get an email notification.
    """
    if len(cfg) > 1:
        cfg = cfg[1]
    else:
        # if no files were passed in command line, run with default 'config.ini'
        cfg = os.path.dirname(sys.argv[0]) + "/" + 'config.ini'

    config = configparser.ConfigParser()
    config.read(cfg)
    sites = json.loads(config['SITES']['SITES'])
    logging.basicConfig(filename=config['LOG']['PATH'], level=logging.WARN)

    sites_state = {}
    for site in sites:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = json_read()

        # handle case of server not responding at all
        try:
            r = requests.get(site, headers={'User-Agent': 'Mozilla/5.0'})

            # there will be no json data file on a first launch of script
            if data:
                # if resource was DOWN but now it's UP
                if r.status_code == 200 and data.get(site, 404) != 200:
                    logging.error('  {} — !!! {} !!! BACK ONLINE — {}'.format(current_time, site, r.status_code))
                    sites_state[site] = 200
                    send_email(config, site, r.status_code, current_time, back=True)

                # if site is DOWN for a 2nd check in a row
                if r.status_code != 200 and data.get(site, 404) != 200:
                    logging.error('  {} — !!! {} !!! — {}'.format(current_time, site, r.status_code))
                    sites_state[site] = r.status_code

            # basic case when the web site was UP on previous checks but now it's DOWN
            if r.status_code != 200 and (not data or data.get(site, 404) == 200):
                logging.error('  {} — !!! {} !!! — {}'.format(current_time, site, r.status_code))
                sites_state[site] = r.status_code
                send_email(config, site, r.status_code, current_time)
            # site was UP and it's still UP
            else:
                logging.warning('  {} — !!! {} !!! — {}'.format(current_time, site, r.status_code))
                sites_state[site] = r.status_code

        except Exception as err:
            logging.error('  {} — !!! {} !!! — {}'.format(current_time, site, err))
            # if site not responded at all, status code in "sites_state.json" will be set
            # to 404 for convenience. The proper error will be sent in email
            sites_state[site] = 404
            # handle first launch
            if not data:
                send_email(config, site, err, current_time)
            elif data and data.get(site, 404) == 200:
                send_email(config, site, err, current_time)

    sites_state['LAST_CHECK'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(sites_state)
    json_output(sites_state)

from time import time
if __name__ == "__main__":
    start = time()
    ping(sys.argv)
    end = time()
    print('Elapsed time: {}'.format(end - start))