from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from jobportal.models import ScrapedJob
import threading
import json

# Correct import for scraper functions in jobsite/

# === JOB SEARCH VIEW ===
def job_search(request):
    keyword = request.GET.get('keyword', '')
    platform = request.GET.get('platform', '')
    employment_type = request.GET.get('employment_type', '')
    remote_option = request.GET.get('remote_option', '')

    jobs = ScrapedJob.objects.all()
    if keyword:
        jobs = jobs.filter(job_title__icontains=keyword)
    if platform:
        jobs = jobs.filter(platform=platform)
    if employment_type:
        jobs = jobs.filter(employment_type__icontains=employment_type)
    if remote_option:
        jobs = jobs.filter(remote_option__icontains=remote_option)

    # Dashboard card data
    total_jobs = ScrapedJob.objects.count()
    total_indeed = ScrapedJob.objects.filter(platform='Indeed').count()
    total_linkedin = ScrapedJob.objects.filter(platform='LinkedIn').count()
    total_jobstreet = ScrapedJob.objects.filter(platform='JobStreet').count()
    total_hybrid = ScrapedJob.objects.filter(remote_option='Hybrid').count()
    total_onsite = ScrapedJob.objects.filter(remote_option='On-site').count()
    total_remote = ScrapedJob.objects.filter(remote_option='Remote').count()
    total_seniority = ScrapedJob.objects.exclude(seniority_level="Not specified").count()

    context = {
        'jobs': jobs,
        'keyword': keyword,
        'platform': platform,
        'employment_type': employment_type,
        'remote_option': remote_option,
        'total_jobs': total_jobs,
        'total_indeed': total_indeed,
        'total_linkedin': total_linkedin,
        'total_jobstreet': total_jobstreet,
        'total_hybrid': total_hybrid,
        'total_onsite': total_onsite,
        'total_remote': total_remote,
        'total_seniority': total_seniority,
    }
    return render(request, 'jobportal/job_search.html', context)

# === WEB SCRAPE DASHBOARD VIEW ===
def web_scrape(request):
    return render(request, 'jobportal/web_scrape.html')
