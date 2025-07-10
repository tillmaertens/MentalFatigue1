from otree.api import *
from .models import C, ensure_all_roles_assigned
import time
import random
from docx import Document
import os


# ===== BASELINE & SETUP PAGES =====

class Consent(Page):
    """Consent form for mental fatigue experiment"""

    def is_displayed(self):
        return self.player.round_number == 1


class BaselineCognitiveTestInstructions(Page):
    """Baseline cognitive test instructions"""

    template_name = 'applicants/CognitiveTestInstructions.html'
    timeout_seconds = 20

    def is_displayed(self):
        return self.player.round_number == 1

    def vars_for_template(self):
        return {
            'session_number': self.player.round_number
        }


class BaselineCognitiveTest(Page):
    """Baseline cognitive test"""

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
    """Show baseline cognitive test results"""

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
    """Players select their role for this session"""

    form_model = 'player'
    form_fields = ['selected_role']

    def vars_for_template(self):
        return {
            'session_number': self.player.round_number,
            'total_sessions': C.NUM_ROUNDS
        }

    def before_next_page(self):
        self.player.session_start_timestamp = time.time()


class WaitForRoles(WaitPage):
    """Wait for all players to select roles"""

    def after_all_players_arrive(group):
        # Use utility function to ensure all roles are assigned
        ensure_all_roles_assigned(group)


# ===== MAIN TASK PAGES =====

class Recruiter(Page):
    """Recruiter interface with tracking"""

    def is_displayed(self):
        return self.player.is_recruiter()  # Cleaner than checking string

    timeout_seconds = C.SESSION_DURATION_SECONDS

    def vars_for_template(self):
        # Ihre bestehenden Applicants aus C.APPLICANTS laden und erweitern
        applicants_with_content = []

        for applicant in C.APPLICANTS:
            # Kopieren Sie die bestehenden Daten
            applicant_data = applicant.copy()

            # Word-Dokument-Inhalt hinzufügen
            applicant_data['description'] = self.get_word_content(applicant['id'])

            applicants_with_content.append(applicant_data)

        return {
            'applicants': applicants_with_content,
            'session_number': self.player.round_number,
            'remaining_time': C.SESSION_DURATION_SECONDS
        }

    def get_word_content(self, applicant_id):
        """Load Word document and convert to HTML"""
        try:
            # Get the current directory (where pages.py is located)
            current_dir = os.path.dirname(os.path.abspath(__file__))

            # Go up to the project root, then navigate to the correct path
            doc_path = os.path.join(
                current_dir,  # This is vacancie_01/applicants/
                '..',  # Go up to vacancie_01/
                '_static',  # Go to _static/
                'applicants',  # Go to applicants/
                f'recruiter_maske_{applicant_id}.docx'
            )

            # Normalize the path to handle '..' correctly
            doc_path = os.path.normpath(doc_path)

            # Check if file exists
            if not os.path.exists(doc_path):
                return f"<p><em>Word document for Applicant {applicant_id.upper()} not found</em></p>"

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
            if text:  # Only non-empty paragraphs
                # Keep simple formatting
                if paragraph.style.name.startswith('Heading'):
                    level = 3  # Default H3
                    if 'Heading 1' in paragraph.style.name:
                        level = 2
                    elif 'Heading 2' in paragraph.style.name:
                        level = 3
                    html_parts.append(f'<h{level}>{text}</h{level}>')
                else:
                    # Check for bold text (simplified)
                    if any(run.bold for run in paragraph.runs):
                        html_parts.append(f'<p><strong>{text}</strong></p>')
                    else:
                        html_parts.append(f'<p>{text}</p>')

        # Process tables (if any)
        for table in document.tables:
            html_parts.append('<table style="border-collapse: collapse; width: 100%; margin: 10px 0;">')
            for row in table.rows:
                html_parts.append('<tr>')
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    html_parts.append(f'<td style="padding: 8px; border: 1px solid #ddd;">{cell_text}</td>')
                html_parts.append('</tr>')
            html_parts.append('</table>')

        # If no content was found
        if not html_parts:
            return "<p><em>The Word document is empty or could not be read.</em></p>"

        return ''.join(html_parts)


class HRCoordinator(Page):
    """HR Coordinator interface with metadata-based criteria"""

    def is_displayed(self):
        return self.player.is_hr_coordinator()

    timeout_seconds = C.SESSION_DURATION_SECONDS

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
    """Business Partner interface with tracking"""

    def is_displayed(self):
        return self.player.is_business_partner()  # Cleaner than checking string

    timeout_seconds = C.SESSION_DURATION_SECONDS

    def vars_for_template(self):
        return {
            'applicants': C.APPLICANTS,
            'session_number': self.player.round_number,
            'remaining_time': C.SESSION_DURATION_SECONDS
        }


class SessionComplete(WaitPage):
    """Wait for all players to complete the session"""

    def after_all_players_arrive(group):
        # Record session end time
        group.session_end_time = time.time()

        # Calculate session metrics
        group.calculate_session_metrics()

        # Update player end timestamps
        for player in group.get_players():
            player.session_end_timestamp = time.time()


class SelfAssessment(Page):
    """Self-assessment questionnaire after each session"""

    form_model = 'player'
    form_fields = ['fatigue_level', 'mental_effort', 'concentration_difficulty', 'motivation_level']

    def vars_for_template(self):
        # Calculate session duration for this player
        session_duration = 0
        if self.player.session_start_timestamp and self.player.session_end_timestamp:
            session_duration = round((self.player.session_end_timestamp - self.player.session_start_timestamp) / 60, 1)

        return {
            'session_number': self.player.round_number,
            'session_duration_minutes': session_duration,
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
    """Cognitive load test after each session"""

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
    """Show cognitive test results"""

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


class SessionResults(Page):
    """Show brief results and prepare for next session"""

    def is_displayed(self):
        return True

    def vars_for_template(self):
        # Get current session performance
        current_performance = {
            'criteria_added': self.player.criteria_added_this_session,
            'scores_entered': self.player.scores_entered_this_session,
            'role_played': self.player.selected_role
        }

        # Get fatigue trend - useful for showing progress
        fatigue_trend = self.player.get_cumulative_fatigue_trend()

        return {
            'session_number': self.player.round_number,
            'total_sessions': C.NUM_ROUNDS,
            'current_performance': current_performance,
            'fatigue_trend': fatigue_trend,
            'is_final_session': self.player.round_number == C.NUM_ROUNDS
        }

    timeout_seconds = 15


# ===== FINAL RESULTS =====

class FinalResults(Page):
    """Final results and debriefing"""

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
                    'scores_entered': round_player.scores_entered_this_session
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
    SessionComplete,
    SelfAssessment,
    CognitiveTestInstructions,
    CognitiveTest,
    CognitiveTestResults,
    SessionResults,

    # Final round only: Results
    FinalResults
]
