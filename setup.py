import configparser
filename = 'properties.ini'
defaultValues = {'bot_token': '','server_id': '', 'rsvp_channel_id': '', 'raid_src_channel_id':'', 'raid_dest_channel_id':'', 'command_character':'!'}
databaseValues = {'ENGINE': 'django.db.backends.postgresql', 'NAME': '','USER': '', 'PASSWORD': ''}
securityValues = {'SECRET_KEY': ''}
config = configparser.ConfigParser()
config.read(filename)

for key in defaultValues.keys():
    if key not in config['DEFAULT']:
        config['DEFAULT'][key] = defaultValues[key]

if 'DATABASES' not in config:
    config['DATABASES'] = dict()
for key in databaseValues.keys():
    if key not in config['DATABASES']:
        config['DATABASES'][key] = databaseValues[key]

if 'SECURITY' not in config:
    config['SECURITY'] = dict()
for key in securityValues.keys():
    if key not in config['SECURITY']:
        config['SECURITY'][key] = securityValues[key]

with open(filename, 'w') as configFile:
    config.write(configFile)
