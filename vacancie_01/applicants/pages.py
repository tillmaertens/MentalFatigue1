from otree.api import *
from .models import C
import time


class ApplicantSelection(Page):
    """Main selection page"""
    form_model = 'player'
    form_fields = ['selected_player']

    def before_next_page(self, timeout_happened=False):
        """Set page start time when role is selected"""
        self.player.page_start_time = time.time()


class Recruiter(Page):
    """Recruiter interface page with pie chart"""

    def vars_for_template(self):
        return {
            'applicants': C.APPLICANTS,
        }

    def is_displayed(self):
        return self.player.selected_player == 'Recruiter'


class BusinessPartner(Page):
    """Business Partner interface page"""

    def is_displayed(self):
        return self.player.selected_player == 'Business-Partner'


class HRCoordinator(Page):
    """HR Coordinator interface page - simplified without metadata"""

    def is_displayed(self):
        return self.player.selected_player == 'HR-Coordinator'

    def vars_for_template(self):
        """Pass simple data to template"""
        return {
            'applicants': C.APPLICANTS,
            'min_score': C.MIN_SCORE,
            'max_score': C.MAX_SCORE,
        }


# Page sequence
page_sequence = [
    ApplicantSelection,
    Recruiter,
    BusinessPartner,
    HRCoordinator
]