#! /usr/bin/env python
# -*- coding: utf-8 -*-
from django.shortcuts import HttpResponseRedirect,render
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from .forms import LoginUserForm
def login(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    if request.method == 'GET' and request.GET.has_key('next'):
        next_page = request.GET['next']
    else:
        next_page = '/'
    if next_page == "/logout/":
        next_page = '/'
    if request.method == "POST":
        form = LoginUserForm(request, data=request.POST)
        if form.is_valid():
            auth.login(request, form.get_user())


            return HttpResponseRedirect(request.POST['next'])
    else:
        form = LoginUserForm(request)
    kwargs = {
        'request': request,
        'form': form,
        'next': next_page,
    }
    return render(request, 'login.html', kwargs)

@login_required
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def index(request):

    return render(request, 'index.html', locals())


def page_not_found(request):
    return render(request, 'pages-404.html', {}, status=404)


def page_not_permission(request):
    return render(request, 'pages-403.html', {}, status=403)


def internl_error(request):
    return render(request, 'pages-500.html', {}, status=500)


def bad_request(request):
    return render(request, 'pages-400.html', {}, status=400)