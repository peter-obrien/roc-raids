## Setup
This bot uses the [discord.py](https://github.com/Rapptz/discord.py/tree/rewrite) rewrite as such requires a version of Python that is compatible with the library.

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
* `raid_src_channel_id` This is the ID of the channel where PokeAlarm raids are processed. 
* `raid_dest_channel_id` This is the ID of the channel where all parsed PokeAlarm raids will go.

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
## Donate
If you'd like to support the work I've done feel free to [donate](https://www.paypal.me/peterobrien5)