# Generated by Django 2.1.5 on 2019-05-02 12:16

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Analysis',
            fields=[
                ('analysis_id', models.AutoField(primary_key=True, serialize=False)),
                ('analysis_name', models.CharField(max_length=200)),
                ('accuracy', models.FloatField(default=0.0)),
                ('ifthen', models.TextField(default='')),
                ('content', models.TextField(null=True)),
                ('create_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='cretetime')),
            ],
        ),
        migrations.CreateModel(
            name='DataSet',
            fields=[
                ('dataSet_id', models.AutoField(primary_key=True, serialize=False)),
                ('dataSet_name', models.CharField(max_length=200)),
                ('dataSet_type', models.CharField(max_length=200)),
                ('table_name', models.CharField(max_length=200)),
                ('fields', models.TextField(default='')),
                ('size', models.IntegerField(default=0)),
                ('create_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='cretetime')),
            ],
        ),
        migrations.CreateModel(
            name='Tree',
            fields=[
                ('tree_id', models.AutoField(primary_key=True, serialize=False)),
                ('tree_name', models.CharField(max_length=200)),
                ('tree_type', models.CharField(max_length=200)),
                ('data_type', models.CharField(default='', max_length=200)),
                ('optimize_type', models.CharField(max_length=200, null=True)),
                ('tree_dict', models.TextField(default='')),
                ('fields', models.TextField(default='')),
                ('depth', models.IntegerField(default=0)),
                ('nodes_num', models.IntegerField(default=0)),
                ('create_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='cretetime')),
                ('dataSet', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='weixinapi.DataSet')),
            ],
        ),
        migrations.AddField(
            model_name='analysis',
            name='dataSet',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='weixinapi.DataSet'),
        ),
        migrations.AddField(
            model_name='analysis',
            name='tree',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='weixinapi.Tree'),
        ),
    ]
