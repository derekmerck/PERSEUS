import logging
import requests
import json
import textwrap
import yaml
import smtplib
import os
from twilio.rest import TwilioRestClient

# Lookup credentials from either os.env or shadow.yaml
shadow = None
with file("shadow.yaml") as f:
    shadow_env = yaml.load(f)
os.environ.update(shadow_env)


class Messenger(object):

    def message(self, msg, **kwargs):
        raise NotImplementedError


class EmailSMSMessenger(Messenger):

    services = textwrap.dedent('''
        # Sender relay servers
        gmail.com: 'smtp.gmail.com:587'

        ---
        # Receiver device gateways
        alltel:     message.alltel.com
        att:        txt.att.net
        boost:      myboostmobile.com
        nextel:     messaging.sprintpcs.com
        sprint:     messaging.sprintpcs.com
        t-mobile:   tmomail.net
        uscellular: email.uscc.net
        verizon:    vtext.com
        virgin:     vmobl.com
        ''')

    relays, gateways = yaml.load_all(services)

    def __init__(self):
        self.relay_user = os.environ['EMAIL_RELAY_USER']
        self.relay_pword = os.environ['EMAIL_RELAY_PWORD']
        self.from_name = os.environ['EMAIL_RELAY_NAME']

        tmp = self.relay_user.split('@')
        self.relay_user_name = tmp[0]
        self.relay_server = self.relays[tmp[1]]
        self.logger = logging.getLogger('EmailSMSMessenger')

        if self.from_name:
            self.from_addr = '{0} <{1}>'.format(self.from_name, self.relay_user)
        else:
            self.from_addr = self.relay_user

    def message(self, msg, number=None, carrier=None):
        if not number or not carrier:
            self.logger.debug("No number or carrier provided")
            return
        to_addr = '%s@%s' % (number, self.gateways[carrier])
        EmailSMSMessenger.send_message(self.relay_server, self.relay_user, self.relay_pword, self.from_addr, to_addr, msg)

    @staticmethod
    def send_message(relay_server, relay_username, relay_password, from_addr, to_addr, msg):
        server = smtplib.SMTP(relay_server)
        server.starttls()
        server.login(relay_username, relay_password)
        logging.debug(from_addr)
        logging.debug(to_addr)
        logging.debug(msg.encode(encoding='UTF-8'))
        server.sendmail(from_addr, to_addr, msg.encode(encoding='UTF-8'))
        server.quit()


class TwilioMessenger(Messenger):

    def __init__(self):
        # Your Account Sid and Auth Token from twilio.com/user/account
        account_sid = os.environ['TWILIO_SID']
        auth_token  = os.environ['TWILIO_AUTH']
        self.client = TwilioRestClient(account_sid, auth_token)
        self.number = os.environ['TWILIO_NUMBER']
        self.logger = logging.getLogger('TwilioMessenger')

    def message(self, msg, number=None):
        if not number:
            self.logger.debug("No number provided")
            return
        msg_obj = self.client.messages.create(body=msg, to=number, from_=self.number)
        self.logger.debug(msg_obj.sid)


class SlackMessenger(Messenger):

    def __init__(self):
        self.url = os.environ['SLACK_URL']

    def message(self, msg, channel=None):
        payload = {'text': msg}
        if channel:
            payload['channel'] = channel
        headers = {'content-type': 'application/json'}
        requests.post(self.url, json.dumps(payload), headers=headers)


def test_twilio_messenger():

    phone_number = os.environ['SMS_TEST_NUMBER']

    twilio = TwilioMessenger()
    twilio.message('Have a great day!', phone_number)


def test_slack_messenger():

    slack = SlackMessenger()
    slack.message('Have a great day!')
#    slack.message('Have a great day!', '@lkobayashi')


def test_email_sms_messenger():

    phone_number = os.environ['SMS_TEST_NUMBER']
    carrier = os.environ['SMS_TEST_NUMBER_CARRIER']

    m = EmailSMSMessenger()
    m.message( 'Have a great day!', phone_number, carrier)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    test_twilio_messenger()