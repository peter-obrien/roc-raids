import configparser

config = configparser.ConfigParser()
config['DEFAULT'] = {'bot_token': '','server_id': '', 'rsvp_channel_id': ''}
with open('properties.ini', 'w') as configFile:
    config.write(configFile)
