# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-22 00:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orm', '0013_auto_20170920_2216'),
    ]

    operations = [
        migrations.AddField(
            model_name='raidzone',
            name='name',
            field=models.CharField(default='Default', max_length=100),
        ),
    ]
