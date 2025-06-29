from otree.api import *
from .models import C


class ApplicantSelection(Page):
    """Main selection page"""
    form_model = 'player'
    form_fields = ['selected_player']


class Recruiter(Page):
    """Recruiter interface page"""

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
    """HR Coordinator interface page"""

    def is_displayed(self):
        return self.player.selected_player == 'HR-Coordinator'


page_sequence = [ApplicantSelection, Recruiter, BusinessPartner, HRCoordinator]