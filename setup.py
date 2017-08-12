import configparser
filename = 'properties.ini'
defaultValues = {'bot_token': '','server_id': '', 'rsvp_channel_id': '', 'bot_only_channels': '', 'raid_channel_id':''}
config = configparser.ConfigParser()
config.read(filename)

for key in defaultValues.keys():
    if key not in config['DEFAULT']:
        config['DEFAULT'][key] = defaultValues[key]

with open(filename, 'w') as configFile:
    config.write(configFile)
