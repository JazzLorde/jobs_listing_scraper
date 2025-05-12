from django.db import models

class ScrapedJob(models.Model):
    job_title = models.CharField(max_length=500)
    company_name = models.CharField(max_length=500)
    location = models.CharField(max_length=500)
    job_url = models.URLField(unique=True, max_length=1000)
    employment_type = models.CharField(max_length=500)
    remote_option = models.CharField(max_length=500)
    posted_date = models.DateField(null=True, blank=True)
    platform = models.CharField(max_length=500)
    keyword = models.CharField(max_length=500)
    seniority_level = models.CharField(max_length=500)
    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_title} @ {self.company_name}"
