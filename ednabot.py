import logging

from slixmpp import ClientXMPP
from slixmpp.exceptions import IqError, IqTimeout

import config

### set up logging ###
logging.basicConfig(level=config.LOG_LEVEL)
log = logging.getLogger(__name__)

class EdnaBot(ClientXMPP):

    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        # If you wanted more functionality, here's how to register plugins:
        # self.register_plugin('xep_0030') # Service Discovery
        # self.register_plugin('xep_0199') # XMPP Ping

        # Here's how to access plugins once you've registered them:
        # self['xep_0030'].add_feature('echo_demo')

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

        # Most get_*/set_* methods from plugins use Iq stanzas, which
        # can generate IqError and IqTimeout exceptions
        #
        # try:
        #     self.get_roster()
        # except IqError as err:
        #     logging.error('There was an error getting the roster')
        #     logging.error(err.iq['error']['condition'])
        #     self.disconnect()
        # except IqTimeout:
        #     logging.error('Server is taking too long to respond')
        #     self.disconnect()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            msg.reply("You said:\n%(body)s" % msg).send()

if __name__ == '__main__':
    xmpp = EdnaBot(config.JID, config.PASSWORD)
    if xmpp.connect():
        log.info("Connected successfully. Starting event loop...")
        try:
            # Run the slixmpp event loop forever
            xmpp.loop.run_forever()
        except KeyboardInterrupt:
            # Gracefully shut down on CTRL-c
            log.info("Bot stopped manually.")
            xmpp.disconnect()
    else:
        log.error("Unable to connect to XMPP server.")

