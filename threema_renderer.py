from jinja2 import Template,Environment, PackageLoader, select_autoescape
from date_locals_enums import Timezone, Spacer
import logging
import os
import datetime
import sys

locale = 'de_DE'
messages = []


class Message(object):
    def __init__(self, timestamp, direction):
        self.timestamp = timestamp
        self.direction = direction
        self.message = None
        self.quote = None
        return

    def finish(self):
        messages.append(self)
        return

    def add_message(self, message):
        if self.message is None:
            self.message = message
        else:
            self.message = self.message + message
        return

    def add_quote(self, quote):
        if self.quote is None:
            self.quote = quote
        else:
            self.quote = self.quote + quote
        return


def parse_ios_export(path):
    with open(path, 'r') as export:
        current_message = None
        for line in export:
            response = parse_line(line)
            if response['newmessage']:
                if current_message is not None:
                    current_message.finish()
                current_message = Message(timestamp=response['timestamp'], direction=response['direction'])
            if response['type'] is "received" or response['type'] is 'send':
                current_message.add_message(response['message'])
            elif response['type'] is 'message':
                current_message.add_message(response['message'])
            elif response['type'] is 'quote':
                current_message.add_quote(response['message'])


def parse_line(line):
    '''

    :param line:
    :return:
    type:
    - received = Header from received Message
    - sent = Header from sent Message
    - quote = Begin or continuation of Quote
    - message: Continuation od message. Begin is defined by Header.
    '''
    response = {
        'timestamp': None,
        'message': None,
        'type': None,
        'direction': None,
        'newmessage': False
    }
    if line[0:4] == '<<< ':
        # received
        response['direction'] = 'received'
        response['newmessage'] = True
        line = line[4:]
    elif line[0:4] == '>>> ':
        # send
        response['direction'] = 'send'
        line = line[4:]
        response['newmessage'] = True

    # Split date and message
    if response['newmessage']:
        tz_separator = None
        for tz in Timezone[locale].value:
            if tz in line:
                tz_separator = tz
                break
        date, line = line.split(tz_separator)
        # Split date
        day, time = date.split(Spacer[locale].value)
        # Rejoin date and create timestamp

        # Human readable date
        timestamp = day + ' ' + time
        # Unix timestamp
        # timestamp = parser.parse(day + ' ' + time).timestamp()

        response['timestamp'] = timestamp

    if line[0:2] == '> ':
        # Quote
        response['type'] = 'quote'
        response['message'] = line[2:]
        return response
    else:
        response['type'] = 'message'
        response['message'] = line
        return response

    logging.debug(line)
    logging.debug(response['message'])
    return response


def render_html():
    env = Environment(loader=PackageLoader('threema_renderer', 'templates'),
                      autoescape=select_autoescape('html', 'xml'))
    template = env.get_template('chat.html.j2')
    if not os.path.exists('render'):
        os.mkdir('render')
    f = open('./render/chat' + str(datetime.datetime.now().timestamp()) + '.html', 'w+')
    f.write(template.render(messages=messages))
    f.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) is not 2:
        print("Invalid arguments.")
        print('threema_renderer.py <path-to-file.txt>')
        exit(1)
    file = sys.argv[1]
    if os.path.isfile(file):
        parse_ios_export(file)
        render_html()
    else:
        print('File not found.')
        exit(1)
