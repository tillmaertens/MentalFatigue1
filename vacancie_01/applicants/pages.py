from otree.api import *
from .models import C, ensure_all_roles_assigned
import random
from docx import Document
import os


# ===== BASELINE & SETUP PAGES =====

class Consent(Page):

    def is_displayed(self):
        return self.player.round_number == 1


class BaselineCognitiveTestInstructions(Page):
    template_name = 'applicants/CognitiveTestInstructions.html'
    timeout_seconds = 20

    def is_displayed(self):
        return self.player.round_number == 1

    def vars_for_template(self):
        return {
            'session_number': self.player.round_number
        }


class BaselineCognitiveTest(Page):
    template_name = 'applicants/CognitiveTest.html'
    form_model = 'player'
    form_fields = ['cognitive_test_score', 'cognitive_test_reaction_time', 'cognitive_test_errors']
    timeout_seconds = 30

    def is_displayed(self):
        return self.player.round_number == 1

    def vars_for_template(self):
        # Generate random Stroop test items for baseline
        test_items = []
        color_mapping = {
            '#ff0000': 'red',
            '#0000ff': 'blue',
            '#00ff00': 'green',
            '#ffff00': 'yellow'
        }

        for i in range(20):  # 20 items
            word = random.choice(C.STROOP_WORDS)
            color_hex = random.choice(C.STROOP_COLORS)
            color_name = color_mapping[color_hex]

            test_items.append({
                'word': word,
                'color': color_hex,
                'correct_answer': color_name
            })

        return {
            'test_items': test_items,
            'test_duration': 30,
            'session_number': self.player.round_number
        }


class BaselineCognitiveTestResults(Page):
    template_name = 'applicants/CognitiveTestResults.html'
    timeout_seconds = 20

    def is_displayed(self):
        return self.player.round_number == 1

    def vars_for_template(self):
        return {
            'session_number': self.player.round_number,
            'score': self.player.cognitive_test_score or 0,
            'reaction_time': self.player.cognitive_test_reaction_time or 0,
            'errors': self.player.cognitive_test_errors or 0,
            'total_items': 20
        }


class RoleSelection(Page):
    form_model = 'player'
    form_fields = ['selected_role']

    def vars_for_template(self):
        return {
            'session_number': self.player.round_number,
            'total_sessions': C.NUM_ROUNDS
        }


class WaitForRoles(WaitPage):
    """Wait for all players to select roles"""

    def after_all_players_arrive(group):
        ensure_all_roles_assigned(group)


# ===== MAIN TASK PAGES =====

class Recruiter(Page):

    def is_displayed(self):
        return self.player.is_recruiter()

    timeout_seconds = C.SESSION_DURATION_SECONDS

    def vars_for_template(self):
        applicants_with_content = []

        for applicant in C.APPLICANTS:
            applicant_data = applicant.copy()
            applicant_data['description'] = self.get_word_content(applicant['id'])
            applicants_with_content.append(applicant_data)

        return {
            'applicants': applicants_with_content,
            'session_number': self.player.round_number,
            'remaining_time': C.SESSION_DURATION_SECONDS
        }

    def get_word_content(self, applicant_id):
        """Load and convert word doc to html"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))

            # Go up to the project root, then navigate to the correct path
            doc_path = os.path.join(
                current_dir,  # This is vacancie_01/applicants/
                '..',  # Go up to vacancie_01/
                '_static',  # Go to _static/
                'applicants',  # Go to applicants/
                f'recruiter_maske_{applicant_id}.docx'
            )

            doc_path = os.path.normpath(doc_path)

            # Load Word document
            document = Document(doc_path)

            # Convert to HTML
            html_content = self.convert_docx_to_html(document)

            return html_content

        except Exception as e:
            return f"<p><em>Error loading document: {str(e)}</em></p>"

    def convert_docx_to_html(self, document):
        """Convert Word document to HTML"""
        html_parts = []

        # Process paragraphs
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                if paragraph.style.name.startswith('Heading'):
                    level = 3  # Default H3
                    if 'Heading 1' in paragraph.style.name:
                        level = 2
                    elif 'Heading 2' in paragraph.style.name:
                        level = 3
                    html_parts.append(f'<h{level}>{text}</h{level}>')
                else:
                    if any(run.bold for run in paragraph.runs):
                        html_parts.append(f'<p><strong>{text}</strong></p>')
                    else:
                        html_parts.append(f'<p>{text}</p>')

        # Process tables
        for table in document.tables:
            html_parts.append('<table style="width:100%; border-collapse: collapse; margin: 10px 0;">')

            for row_idx, row in enumerate(table.rows):
                html_parts.append('<tr>')
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    # Check if it's a header row
                    if row_idx == 0 or any(run.bold for para in cell.paragraphs for run in para.runs):
                        html_parts.append(
                            f'<td style="border: 1px solid #ddd; padding: 5px; font-weight: bold; background-color: #f5f5f5;">{cell_text}</td>')
                    else:
                        html_parts.append(f'<td style="border: 1px solid #ddd; padding: 5px;">{cell_text}</td>')
                html_parts.append('</tr>')

            html_parts.append('</table>')

        if not html_parts:
            return "<p><em>The Word document is empty or could not be read.</em></p>"

        return ''.join(html_parts)


class HRCoordinator(Page):
    form_model = 'player'
    form_fields = ['criteria_added_this_session', 'validation_data_json']  # Add the new field

    def is_displayed(self):
        return self.player.is_hr_coordinator()

    timeout_seconds = C.SESSION_DURATION_SECONDS

    def before_next_page(self):
        """Validation using form data"""
        import json

        try:
            validation_data_str = self.player.validation_data_json or '{}'

            if not validation_data_str or validation_data_str == '{}':
                self.player.criteria_correct_this_session = 0
                self.player.criteria_incorrect_this_session = 0
                return

            criteria_data = json.loads(validation_data_str)
            correct_count = 0
            incorrect_count = 0
            metadata_criteria = C.METADATA['criteria']

            for criterion_name, data in criteria_data.items():
                # Find the criterion in metadata
                criterion_metadata = None
                for criterion in metadata_criteria:
                    if criterion['name'].strip().lower() == criterion_name.strip().lower():
                        criterion_metadata = criterion
                        break

                if criterion_metadata:
                    # Check scores and relevance
                    scores_correct = True
                    relevance_correct = True

                    # Check scores for each applicant
                    for applicant_id in ['a', 'b', 'c']:
                        entered_score = data['scores'].get(applicant_id, 0)
                        correct_score = criterion_metadata['scores'].get(f'applicant_{applicant_id}', 0)

                        if int(entered_score or 0) != int(correct_score):
                            scores_correct = False
                            break

                    # Check relevance
                    entered_relevance = data.get('relevance', 'normal')
                    correct_relevance = criterion_metadata.get('relevance', 'normal')
                    relevance_correct = entered_relevance == correct_relevance

                    # Count correct or incorrect
                    if scores_correct and relevance_correct:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                else:
                    incorrect_count += 1

            # Update Player fields
            self.player.criteria_correct_this_session = correct_count
            self.player.criteria_incorrect_this_session = incorrect_count

        except Exception as e:
            self.player.criteria_correct_this_session = 0
            self.player.criteria_incorrect_this_session = 0

    def vars_for_template(self):
        return {
            'applicants': C.APPLICANTS,
            'min_score': C.MIN_SCORE,
            'max_score': C.MAX_SCORE,
            'session_number': self.player.round_number,
            'remaining_time': C.SESSION_DURATION_SECONDS,
            'criteria_data': C.CRITERIA_DATA,
            'categories': C.CATEGORIES,
            'criteria_by_category': C.CRITERIA_BY_CATEGORY,
            'relevance_factors': C.RELEVANCE_FACTORS
        }


class BusinessPartner(Page):

    def is_displayed(self):
        return self.player.is_business_partner()

    timeout_seconds = C.SESSION_DURATION_SECONDS

    def vars_for_template(self):
        return {
            'applicants': C.APPLICANTS,
            'session_number': self.player.round_number,
            'remaining_time': C.SESSION_DURATION_SECONDS,
            'criteria_data': C.CRITERIA_DATA,
            'categories': C.CATEGORIES,
            'criteria_by_category': C.CRITERIA_BY_CATEGORY,
        }


class SelfAssessment(Page):
    form_model = 'player'
    form_fields = ['fatigue_level', 'mental_effort', 'concentration_difficulty', 'motivation_level']

    def vars_for_template(self):
        return {
            'session_number': self.player.round_number,
            'role_played': self.player.selected_role
        }


class CognitiveTestInstructions(Page):
    timeout_seconds = 20

    def is_displayed(self):
        return self.player.round_number > 0

    def vars_for_template(self):
        return {
            'session_number': self.player.round_number
        }


class CognitiveTest(Page):
    form_model = 'player'
    form_fields = ['cognitive_test_score', 'cognitive_test_reaction_time', 'cognitive_test_errors']
    timeout_seconds = 30

    def is_displayed(self):
        return self.player.round_number > 0

    def vars_for_template(self):
        # Generate random Stroop test items
        test_items = []
        color_mapping = {
            '#ff0000': 'red',
            '#0000ff': 'blue',
            '#00ff00': 'green',
            '#ffff00': 'yellow'
        }

        for i in range(20):
            word = random.choice(C.STROOP_WORDS)
            color_hex = random.choice(C.STROOP_COLORS)
            color_name = color_mapping[color_hex]

            test_items.append({
                'word': word,
                'color': color_hex,
                'correct_answer': color_name
            })

        return {
            'test_items': test_items,
            'test_duration': 30,
            'session_number': self.player.round_number
        }


class CognitiveTestResults(Page):
    timeout_seconds = 20

    def is_displayed(self):
        return self.player.round_number > 0

    def vars_for_template(self):
        return {
            'session_number': self.player.round_number,
            'score': self.player.cognitive_test_score or 0,
            'reaction_time': self.player.cognitive_test_reaction_time or 0,
            'errors': self.player.cognitive_test_errors or 0,
            'total_items': 20
        }


# ===== FINAL RESULTS =====

class FinalResults(Page):

    def is_displayed(self):
        return self.player.round_number == C.NUM_ROUNDS

    def vars_for_template(self):
        # Compile comprehensive results for research analysis
        all_sessions_data = []

        for round_num in range(1, C.NUM_ROUNDS + 1):
            try:
                round_player = self.player.in_round(round_num)
                session_data = {
                    'session': round_num,
                    'role': round_player.selected_role,
                    'fatigue_level': round_player.fatigue_level,
                    'mental_effort': round_player.mental_effort,
                    'concentration_difficulty': round_player.concentration_difficulty,
                    'motivation_level': round_player.motivation_level,
                    'cognitive_score': round_player.cognitive_test_score,
                    'cognitive_reaction_time': round_player.cognitive_test_reaction_time,
                    'criteria_added': round_player.criteria_added_this_session,
                }
                all_sessions_data.append(session_data)
            except:
                continue

        # Calculate overall trends for research
        fatigue_trend = [s['fatigue_level'] for s in all_sessions_data if s['fatigue_level']]
        cognitive_trend = [s['cognitive_score'] for s in all_sessions_data if s['cognitive_score']]

        return {
            'all_sessions': all_sessions_data,
            'total_sessions_completed': len(all_sessions_data),
            'average_fatigue': sum(fatigue_trend) / len(fatigue_trend) if fatigue_trend else 0,
            'fatigue_increase': fatigue_trend[-1] - fatigue_trend[0] if len(fatigue_trend) >= 2 else 0,
            'cognitive_decline': cognitive_trend[0] - cognitive_trend[-1] if len(cognitive_trend) >= 2 else 0
        }


page_sequence = [
    # Round 1 only: Consent and Baseline
    Consent,
    BaselineCognitiveTestInstructions,
    BaselineCognitiveTest,
    BaselineCognitiveTestResults,

    # Every round: Role selection and session
    RoleSelection,
    WaitForRoles,

    # Main task (role-dependent)
    Recruiter,
    HRCoordinator,
    BusinessPartner,

    # Post-session assessment
    SelfAssessment,
    CognitiveTestInstructions,
    CognitiveTest,
    CognitiveTestResults,

    # Final round only: Results
    FinalResults
]
