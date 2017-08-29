# roc-raids
Discord bot for Rochester, NY Pokemon Go raid coordination.

## Setup
This bot uses [discord.py](https://github.com/Rapptz/discord.py) as such requires a version of Python that is compatible with the library.

Before continuing, please follow their instructions to setup their library.

Other libraries used are:
```
pip install -U pytz
pip install -U Django
pip install -U psycopg2
```
The bot also requires a [PostgreSQL](https://www.postgresql.org/) database.

After Postgres is setup, please create a database and optional user to login to the database.

After the dependencies are loaded. The application needs to be configured and the database models applied.

### Configuration
Please run `python setup.py` to create a properties.ini file that needs to be populated in order for the bot to run.

#### Default
* `bot_token` This is the App Bot User Token for the bot. Can be found [here](https://discordapp.com/developers/applications/me).
* `server_id` This is the ID for the discord server that the bot will run on.
* `rsvp_channel_id` This is the ID of the channel where the RSVP messages will go.
* `bot_only_channels` *(Optional)* Comma separate list of channel IDs where only bot commands are allowed. The bot will delete and PM users if invalid text is entered.
* `raid_src_channel_id` This is the ID of the channel where PokeAlarm raids are processed. 
* `raid_dest_channel_id` This is the ID of the channel where all parsed PokeAlarm raids will go.
* `zones` *(Optional)* Comma separated list of raid zones to send parsed raids. Raid zones are a circle centered on a set of coordinates with a radius in kilometers.
    * Basic format for a raid zone is `destination|latitude|longitude|radius`. After the radius additional arguments can be added to filter by the pokemon number of the raid boss.
        * Pokemon filtering example `12345678900000|70.123456|-40.123456|10|150|151`

#### Databases
* `name` Name of the database to use.
* `user` Name of the user to connect to the database.
* `password` Password for the user to connect to the database.

#### Security
* `secret_key` This is a Django secret key needed to start the application.


### Database
Anytime code is updated, run `python manage.py migrate` to apply any possible changes to the database models.

## Steps to Run
```
python raid-coordinator.py
```
