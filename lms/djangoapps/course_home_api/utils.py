"""Utility functions for course home"""

from django.conf import settings


def get_microfrontend_url(course_key, view_name=None):
    """
    Takes in a course key and view name, returns the appropriate course home mfe route
    """
    mfe_link = '{}/course/{}'.format(settings.LEARNING_MICROFRONTEND_URL, course_key)

    if view_name:
        mfe_link += '/{}'.format(view_name)

    return mfe_link


def is_request_from_learning_mfe(request):
    """
    Returns whether the given request was made by the frontend-app-learning MFE.
    """
    return request.META.get('HTTP_REFERER', '').startswith(settings.LEARNING_MICROFRONTEND_URL)
