# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-15 03:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orm', '0007_raidzone_filter_pokemon_by_raid_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='raidzone',
            name='server',
            field=models.BigIntegerField(default=0),
            preserve_default=False,
        ),
    ]
