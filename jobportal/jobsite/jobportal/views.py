from django.shortcuts import render
from jobportal.models import ScrapedJob

def job_search(request):
    # Get filter values from the request
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

    context = {
        'jobs': jobs,
        'keyword': keyword,
        'platform': platform,
        'employment_type': employment_type,
        'remote_option': remote_option,
    }
    return render(request, 'jobportal/job_search.html', context)
