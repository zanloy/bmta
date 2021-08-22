#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
import re
import signal
import sys

from aiosmtpd.smtp import SMTP
from contextlib import suppress
from functools import partial
from pprint import pprint
from smtplib import SMTPRecipientsRefused, SMTPHeloError, SMTPSenderRefused, SMTPDataError, SMTPNotSupportedError
from smtplib import SMTP as SMTPClient

class MailHandler:
    def __init__(self, host, port):
        # Setup instance vars
        self.host = host
        self.port = port
        # Setup regexp patterns
        self.ip_pattern = re.compile(r'(?P<ip>((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))')
        self.ticket_pattern = re.compile(r'(?P<ticket>BPS-[\d]+)', flags=re.IGNORECASE)

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if not address.endswith('@va.gov'):
            return '550 not relaying to that domain'
        envelope.rcpt_tos.append(address)
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        # Filter msg content
        envelope.content = self.ip_pattern.sub(self.filter_ip, envelope.content)
        if re.search(r'^Content-Type: text/html', envelope.content, (re.IGNORECASE | re.MULTILINE)) != None:
            envelope.content = self.ticket_pattern.sub(self.filter_ticket, envelope.content)
        else:
            matches = re.findall(self.ticket_pattern, envelope.content)
            if len(matches):
                envelope.content += '\r\n\r\nLinks to tickets found in message body:'
                for match in matches:
                    match = match.upper()
                    envelope.content += f'\r\n{match}: https://vajira.max.gov/browse/{match}'
        # Forward our email
        try:
            with SMTPClient(self.host, self.port) as client:
                client.sendmail(
                    from_addr=envelope.mail_from,
                    to_addrs=envelope.rcpt_tos,
                    msg=envelope.content
                )
        except ConnectionRefusedError:
            return '451 Upstream SMTP Server Refused Our Connection'
        except SMTPDataError:
            return '451 Upstream SMTP Server Refused Message Data'
        except SMTPHeloError:
            return '451 Upstream SMTP Server Returned Invalid HELO response'
        except SMTPNotSupportedError:
            return '451 Upstream SMTP Server Refused SMTPUTF8'
        except SMTPRecipientsRefused:
            return '451 Recipients Refused By Upstream SMTP Server'
        except SMTPSenderRefused:
            return '451 Upstream SMTP Server Refused Sender Value'
        return '250 Message Accepted For Delivery'

    def filter_ip(self, ip):
        try:
            exploded = str(ip.group('ip')).split('.')
            return f'x.x.{exploded[2]}.{exploded[3]}'
        except Exception:
            return 'x.x.x.x'

    def filter_ticket(self, matchobj):
        try:
            ticket = matchobj.group('ticket')
            return f'<a href="https://vajira.max.gov/browse/{ticket.upper()}">{ticket}</a>'
        except Exception:
            return matchobj.group('ticket')

if __name__ == "__main__":
    # Setup config vals
    parser = argparse.ArgumentParser(description='BIP Mail Transfer Agent')
    parser.add_argument('-s', '--server', default=os.environ.get('BMTA_SERVER', 'smtp.va.gov'), help='upstream SMTP host to forward emails to')
    parser.add_argument('-p', '--port', default=os.environ.get('BMTA_PORT', 25), help='upstream SMTP port to forward emails to')
    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s :: %(levelname)s :: %(module)s :: %(message)s',
        level=logging.INFO,
        stream=sys.stdout,
    )
    handler = MailHandler(args.server, args.port)
    factory = partial(SMTP, handler, decode_data=True, hostname='bmta', ident='v1.0')

    loop = asyncio.get_event_loop()
    with suppress(NotImplementedError):
        loop.add_signal_handler(signal.SIGINT, loop.stop)
    try:
        server = loop.create_server(factory, port=2525)
        server_loop = loop.run_until_complete(server)
        logging.info('Starting asyncio loop. Ready for connections.')
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info('Received Interupt Signal. Shutting down service.')
    finally:
        server_loop.close()
        logging.info('Stopping asyncio loop.')
        loop.run_until_complete(server_loop.wait_closed())
        loop.close()
