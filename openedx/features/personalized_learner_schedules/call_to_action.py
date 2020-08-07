import logging

from crum import get_current_request
from django.urls import reverse
from django.utils.translation import gettext as _

from lms.djangoapps.course_home_api.utils import is_request_from_learning_mfe
from openedx.core.lib.mobile_utils import is_request_from_mobile_app

log = logging.getLogger(__name__)


class PersonalizedLearnerScheduleCallToAction:
    CAPA_SUBMIT_DISABLED = 'capa_submit_disabled'
    VERTICAL_BANNER = 'vertical_banner'

    past_due_class_warnings = set()

    def get_ctas(self, xblock, category):
        """
        Return the calls to action associated with the specified category for the given xblock.

        See the CallToActionService class constants for a list of recognized categories.

        Returns: list of dictionaries, describing the calls to action, with the following keys:
                 link, link_name, form_values, and description.
                 If the category is not recognized, an empty list is returned.

        An example of a returned list:
        [{
            'link': 'localhost:18000/skip',  # A link to POST to when the Call To Action is taken
            'link_name': 'Skip this Problem',  # The name of the action
            'form_values': {  # Any parameters to include with the CTA
                'foo': 'bar',
            },
            # A long-form description to be associated with the CTA
            'description': "If you don't want to do this problem, just skip it!"
        }]
        """
        ctas = []

        # Some checks to disable PLS calls to action until these environments (mobile and MFE) support them natively
        request = get_current_request()
        is_mobile_app = request and is_request_from_mobile_app(request)
        is_learning_mfe = request and is_request_from_learning_mfe(request)
        if is_mobile_app or is_learning_mfe:
            return []

        if category == self.CAPA_SUBMIT_DISABLED:
            # xblock is a capa problem, and the submit button is disabled. Check if it's because of a personalized
            # schedule due date being missed, and if so, we can offer to shift it.
            if self._is_block_shiftable(xblock):
                ctas.append(self._make_reset_deadlines_cta(xblock))

        elif category == self.VERTICAL_BANNER:
            # xblock is a vertical, so we'll check all the problems inside it. If there are any that will show a
            # a "shift dates" CTA under CAPA_SUBMIT_DISABLED, then we'll also show the same CTA as a vertical banner.
            if any(self._is_block_shiftable(item) for item in xblock.get_display_items()):
                ctas.append(self._make_reset_deadlines_cta(xblock))

        return ctas

    @staticmethod
    def _is_block_shiftable(xblock):
        """
        Test if the xblock would be solvable if we were to shift dates.

        Only xblocks with an is_past_due method (e.g. capa and LTI) will be considered possibly shiftable.
        """
        if not hasattr(xblock, 'is_past_due'):
            return False

        if hasattr(xblock, 'attempts') and hasattr(xblock, 'max_attempts'):
            can_attempt = xblock.max_attempts is None or xblock.attempts < xblock.max_attempts
        else:
            can_attempt = True

        if callable(xblock.is_past_due):
            is_past_due = xblock.is_past_due()
        else:
            PersonalizedLearnerScheduleCallToAction._log_past_due_warning(type(xblock).__name__)
            is_past_due = xblock.is_past_due

        return xblock.self_paced and can_attempt and is_past_due

    @staticmethod
    def _log_past_due_warning(name):
        if name in PersonalizedLearnerScheduleCallToAction.past_due_class_warnings:
            return

        log.warning('PersonalizedLearnerScheduleCallToAction has encountered an xblock that defines is_past_due '
                    'as a property. This is supported for now, but may not be in the future. Please change '
                    '%s.is_past_due into a method.', name)
        PersonalizedLearnerScheduleCallToAction.past_due_class_warnings.add(name)

    @staticmethod
    def _make_reset_deadlines_cta(xblock):
        from lms.urls import RESET_COURSE_DEADLINES_NAME
        return {
            'link': reverse(RESET_COURSE_DEADLINES_NAME),
            'link_name': _('Shift due dates'),
            'form_values': {
                'course_id': xblock.scope_ids.usage_id.context_key,
            },
            'description': _('To participate in this assignment, the suggested schedule for your course needs '
                             'updating. Don’t worry, we’ll shift all the due dates for you and you won’t lose '
                             'any of your progress.'),
        }
