from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_userprofile_filter_stop_words'),
    ]

    operations = [
        migrations.AddField(
            model_name='word',
            name='part_of_speech',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='word',
            name='phonetic',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='word',
            name='audio_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='word',
            name='example_sentence',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='word',
            name='synonyms',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='word',
            name='antonyms',
            field=models.JSONField(blank=True, default=list),
        ),
    ]

