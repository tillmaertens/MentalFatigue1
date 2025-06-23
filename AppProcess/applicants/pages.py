from otree.api import Page
import os
from . import models

C = models.C


class ApplicantPage(Page):
    def vars_for_template(self):
        selected = self.request.query_params.get('selected_applicant', 'a')
        self.player.selected_applicant = selected

        applicants = C.APPLICANTS
        selected_upper = selected.upper()

        folder = os.path.join(C.BASE_PATH, f"applicant_{selected}")
        pdf_paths = {
            'cv': os.path.join(folder, f"cv_{selected}.pdf"),
            'cover_letter': os.path.join(folder, f"cover_letter_{selected}.pdf"),
            'job_reference': os.path.join(folder, f"job_reference_{selected}.pdf"),
        }

        return dict(
            selected=selected,
            selected_upper=selected_upper,
            applicants=applicants,
            pdf_paths=pdf_paths,
        )

    def before_next_page(self, timeout_happened):
        pass

page_sequence = [ApplicantPage]
