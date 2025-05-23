# Generated by Django 4.2.5 on 2025-05-04 05:54

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ScrapedJob",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("job_title", models.CharField(max_length=255)),
                ("company_name", models.CharField(max_length=255)),
                ("location", models.CharField(max_length=255)),
                ("job_url", models.URLField(unique=True)),
                ("employment_type", models.CharField(max_length=100)),
                ("remote_option", models.CharField(max_length=50)),
                ("posted_date", models.DateField()),
                ("platform", models.CharField(max_length=50)),
                ("keyword", models.CharField(max_length=100)),
                ("seniority_level", models.CharField(max_length=100)),
                ("scraped_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
