# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-23 21:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orm', '0017_merge_20170923_1603'),
    ]

    operations = [
        migrations.AddField(
            model_name='guildconfig',
            name='raid_category',
            field=models.BigIntegerField(null=True),
        ),
    ]