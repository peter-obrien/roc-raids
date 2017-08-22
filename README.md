# roc-raids
Discord bot for Rochester, NY Pokemon Go coordination.

## Setup
This bot uses [discord.py](https://github.com/Rapptz/discord.py) as such requires a compatible version of Python. Please follow their instructions to setup their library.

Other libraries used are:
```
pip install -U pytz
pip install -U Django
pip install -U psycopg2
```
The bot also requires a [PostgreSQL](https://www.postgresql.org/) database.

After the dependencies are loaded. The application needs to be configured.

Please run `python setup.py` to create a properties.ini file that needs to be populated in order for the bot to run.

## Steps to Run
```
python raid-coordinator.py
```
