import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
import datetime
import configparser
import json
import os
import sys
import logging
import smtplib
from requests.exceptions import ConnectionError


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


async def send_email(config, site, status_code, time, back=False):
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


def fetch(session, site):
    try:
        with session.get(site, headers={'User-Agent': 'Mozilla/5.0'}) as response:
            return {site: response.status_code}
    except Exception as err:
        return {site: err}


async def ping_async(cfg):
    # initialization
    if len(cfg) > 1:
        cfg = cfg[1]
    else:
        # if no files were passed in command line, run with default 'config.ini'
        cfg = os.path.dirname(sys.argv[0]) + "/" + 'config.ini'

    config = configparser.ConfigParser()
    config.read(cfg)
    sites = json.loads(config['SITES']['SITES'])
    data = json_read()
    sites_state = {}

    with ThreadPoolExecutor(max_workers=15) as executor:
        with requests.Session() as session:
            # Set any session parameters here before calling `fetch`
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    executor,
                    fetch,
                    *(session, site) # Allows us to pass in multiple arguments to `fetch`
                )
                for site in sites
            ]
            responses = await asyncio.gather(*tasks)
            for i in range(len(responses)):
                for site in responses[i]:
                    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    if data:
                        # if resource was DOWN but now it's UP
                        if responses[i][site] == 200 and data.get(site, 404) != 200:
                            logging.error('  {} — !!! {} !!! BACK ONLINE — {}'.format(current_time, site, responses[i][site]))
                            sites_state[site] = 200
                            await send_email(config, site, responses[i][site], current_time, back=True)

                        # if site is DOWN for a 2nd check in a row
                        elif responses[i][site] != 200 and data.get(site, 404) != 200:
                            logging.error('  {} — !!! {} !!! — {}'.format(current_time, site, responses[i][site]))
                            sites_state[site] = 404 if isinstance(responses[i][site], ConnectionError) else responses[i][site]

                    # basic case when the web site was UP on previous checks but now it's DOWN
                    if responses[i][site] != 200 and (not data or data.get(site, 404) == 200):
                        logging.error('  {} — !!! {} !!! — {}'.format(current_time, site, responses[i][site]))
                        sites_state[site] = 404 if isinstance(responses[i][site], ConnectionError) else responses[i][site]
                        await send_email(config, site, responses[i][site], current_time)
                    # site was UP and it's still UP
                    else:
                        logging.warning('  {} — !!! {} !!! — {}'.format(current_time, site, responses[i][site]))
                        sites_state[site] = 404 if isinstance(responses[i][site], ConnectionError) else responses[i][site]

        sites_state['LAST_CHECK'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(sites_state)
        json_output(sites_state)



def main(cfg):
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(ping_async(cfg))
    loop.run_until_complete(future)


if __name__ == "__main__":
    from time import time
    start = time()
    main(sys.argv)
    end = time()
    print('Elapsed time: {}'.format(end - start))
