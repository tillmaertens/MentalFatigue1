from otree.api import *
from .models import C, ensure_all_roles_assigned, get_vacancy_info, get_applicants_data_for_vacancy, \
    load_metadata_criteria
import random
from docx import Document
import os


# ===== NEW VACANCY SELECTION & TRANSITION PAGES =====

class VacancySelection(Page):
    form_model = 'player'
    form_fields = ['selected_first_vacancy']

    def is_displayed(self):
        return self.player.round_number == C.VACANCY_1_START_ROUND
    def vars_for_template(self):
        return {
            'total_rounds': C.NUM_ROUNDS,
        }


class TransitionChoice(Page):
    form_model = 'player'
    form_fields = ['continue_to_second_vacancy']

    def is_displayed(self):
        return self.player.round_number == C.TRANSITION_ROUND

    def vars_for_template(self):
        # Get which vacancy they just completed
        selection_player = self.player.in_round(C.VACANCY_1_START_ROUND)
        first_vacancy = selection_player.selected_first_vacancy or 1
        completed_vacancy = first_vacancy
        next_vacancy = 2 if first_vacancy == 1 else 1

        return {
            'completed_vacancy': completed_vacancy,
            'next_vacancy': next_vacancy,
        }


# ===== BASELINE & SETUP PAGES =====

class Consent(Page):

    def is_displayed(self):
        return self.player.round_number == C.VACANCY_1_START_ROUND


class BaselineCognitiveTestInstructions(Page):
    template_name = 'applicants/CognitiveTestInstructions.html'
    timeout_seconds = 20

    def is_displayed(self):
        # Show at start of each vacancy
        return (self.player.round_number == C.VACANCY_1_START_ROUND or
                self.player.round_number == C.VACANCY_2_START_ROUND)

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': 0,  # This is baseline, not a session
            'vacancy_number': vacancy_number
        }


class BaselineCognitiveTest(Page):
    template_name = 'applicants/CognitiveTest.html'
    form_model = 'player'
    form_fields = ['cognitive_test_score', 'cognitive_test_reaction_time', 'cognitive_test_errors']
    timeout_seconds = 30

    def is_displayed(self):
        # Show at start of each vacancy
        return (self.player.round_number == C.VACANCY_1_START_ROUND or
                self.player.round_number == C.VACANCY_2_START_ROUND)

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

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
            'session_number': 0,  # This is baseline, not a session
            'vacancy_number': vacancy_number
        }


class BaselineCognitiveTestResults(Page):
    template_name = 'applicants/CognitiveTestResults.html'
    timeout_seconds = 20

    def is_displayed(self):
        # Show at start of each vacancy
        return (self.player.round_number == C.VACANCY_1_START_ROUND or
                self.player.round_number == C.VACANCY_2_START_ROUND)

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': 0,  # This is baseline, not a session
            'vacancy_number': vacancy_number,
            'score': self.player.cognitive_test_score or 0,
            'reaction_time': self.player.cognitive_test_reaction_time or 0,
            'errors': self.player.cognitive_test_errors or 0,
            'total_items': 20
        }


class RoleSelection(Page):
    form_model = 'player'
    form_fields = ['selected_role']

    def is_displayed(self):
        return self.should_show_vacancy_session()

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            transition_player = self.player.in_round(C.TRANSITION_ROUND)
            return getattr(transition_player, 'continue_to_second_vacancy', False)
        return False

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'total_sessions': 6  # Always 6 sessions per vacancy
        }

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1


class WaitForRoles(WaitPage):
    """Wait for all players to select roles"""

    def after_all_players_arrive(group):
        ensure_all_roles_assigned(group)


# ===== MAIN TASK PAGES =====

class Recruiter(Page):

    def is_displayed(self):
        if not self.player.is_recruiter():
            return False
        return self.should_show_vacancy_session()

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            # Only show if user chose to continue
            transition_player = self.player.in_round(C.TRANSITION_ROUND)
            return getattr(transition_player, 'continue_to_second_vacancy', False)
        return False

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS

    timeout_seconds = property(get_timeout_seconds)

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        applicants_with_content = []
        doc_suffix = vacancy_info['doc_suffix'] if vacancy_info else '1'

        for applicant in applicants_data:
            applicant_data = applicant.copy()
            applicant_data['description'] = self.get_word_content(applicant['id'], doc_suffix)
            applicants_with_content.append(applicant_data)

        # Calculate session number within vacancy
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'applicants': applicants_with_content,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'remaining_time': vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS
        }

    def get_vacancy_session_number(self):
        """Calculate session number within the current vacancy (1-6)"""
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def get_word_content(self, applicant_id, doc_suffix='1'):
        """Load and convert word doc to html"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))

            doc_path = os.path.join(
                current_dir,
                '..',
                '_static',
                'applicants',
                f'recruiter_maske_{applicant_id}{doc_suffix}.docx'  # Updated filename
            )

            doc_path = os.path.normpath(doc_path)
            document = Document(doc_path)
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
    form_fields = ['criteria_added_this_session', 'validation_data_json']

    def is_displayed(self):
        if not self.player.is_hr_coordinator():
            return False
        return self.should_show_vacancy_session()

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            # Only show if user chose to continue
            transition_player = self.player.in_round(C.TRANSITION_ROUND)
            return getattr(transition_player, 'continue_to_second_vacancy', False)
        return False

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS

    timeout_seconds = property(get_timeout_seconds)

    def get_vacancy_session_number(self):
        """Calculate session number within the current vacancy (1-6)"""
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

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

            # Load vacancy-specific metadata
            metadata = load_metadata_criteria(self.player.round_number, self.player)
            metadata_criteria = metadata['criteria']

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
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        # Load vacancy-specific metadata
        metadata = load_metadata_criteria(self.player.round_number, self.player)

        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'applicants': applicants_data,
            'min_score': C.MIN_SCORE,
            'max_score': C.MAX_SCORE,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'remaining_time': vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS,
            'criteria_data': metadata['criteria'],
            'categories': metadata['categories'],
            'criteria_by_category': metadata['criteria_by_category'],
            'relevance_factors': C.RELEVANCE_FACTORS
        }


class BusinessPartner(Page):

    def is_displayed(self):
        if not self.player.is_business_partner():
            return False
        return self.should_show_vacancy_session()

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            # Only show if user chose to continue
            transition_player = self.player.in_round(C.TRANSITION_ROUND)
            return getattr(transition_player, 'continue_to_second_vacancy', False)
        return False

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS

    timeout_seconds = property(get_timeout_seconds)

    def get_vacancy_session_number(self):
        """Calculate session number within the current vacancy (1-6)"""
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        # Load vacancy-specific metadata
        metadata = load_metadata_criteria(self.player.round_number, self.player)

        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'applicants': applicants_data,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'remaining_time': vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS,
            'criteria_data': metadata['criteria'],
            'categories': metadata['categories'],
            'criteria_by_category': metadata['criteria_by_category'],
        }


class SelfAssessment(Page):
    form_model = 'player'
    form_fields = ['fatigue_level', 'mental_effort', 'concentration_difficulty', 'motivation_level']

    def is_displayed(self):
        return self.should_show_vacancy_session()

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            transition_player = self.player.in_round(C.TRANSITION_ROUND)
            return getattr(transition_player, 'continue_to_second_vacancy', False)
        return False

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'role_played': self.player.selected_role
        }


class CognitiveTestInstructions(Page):
    timeout_seconds = 20

    def is_displayed(self):
        return self.should_show_vacancy_session()

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            transition_player = self.player.in_round(C.TRANSITION_ROUND)
            return getattr(transition_player, 'continue_to_second_vacancy', False)
        return False

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number
        }


class CognitiveTest(Page):
    form_model = 'player'
    form_fields = ['cognitive_test_score', 'cognitive_test_reaction_time', 'cognitive_test_errors']
    timeout_seconds = 30

    def is_displayed(self):
        return self.should_show_vacancy_session()

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            transition_player = self.player.in_round(C.TRANSITION_ROUND)
            return getattr(transition_player, 'continue_to_second_vacancy', False)
        return False

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

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
            'session_number': session_number,
            'vacancy_number': vacancy_number
        }


class CognitiveTestResults(Page):
    timeout_seconds = 20

    def is_displayed(self):
        return self.should_show_vacancy_session()

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            transition_player = self.player.in_round(C.TRANSITION_ROUND)
            return getattr(transition_player, 'continue_to_second_vacancy', False)
        return False

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
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
        # Determine which vacancy to show results for (the last completed one)
        transition_player = self.player.in_round(C.TRANSITION_ROUND)
        completed_second_vacancy = getattr(transition_player, 'continue_to_second_vacancy', False)

        if completed_second_vacancy:
            # Show results from second vacancy (rounds 9-14)
            start_round = C.VACANCY_2_START_ROUND
            end_round = C.VACANCY_2_END_ROUND
            results_vacancy = 2 if self.player.in_round(C.VACANCY_1_START_ROUND).selected_first_vacancy == 1 else 1
        else:
            # Show results from first vacancy (rounds 2-7)
            start_round = C.VACANCY_1_START_ROUND
            end_round = C.VACANCY_1_END_ROUND
            results_vacancy = self.player.in_round(C.VACANCY_1_START_ROUND).selected_first_vacancy or 1

        # Compile results from the appropriate vacancy rounds
        all_sessions_data = []
        for round_num in range(start_round, end_round + 1):
            try:
                round_player = self.player.in_round(round_num)
                session_data = {
                    'session': round_num - start_round + 1,  # Display as 1-6
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

        # Calculate trends
        fatigue_trend = [s['fatigue_level'] for s in all_sessions_data if s['fatigue_level']]
        cognitive_trend = [s['cognitive_score'] for s in all_sessions_data if s['cognitive_score']]

        return {
            'all_sessions': all_sessions_data,
            'results_vacancy': results_vacancy,
            'total_sessions_completed': len(all_sessions_data),
            'average_fatigue': sum(fatigue_trend) / len(fatigue_trend) if fatigue_trend else 0,
            'fatigue_increase': fatigue_trend[-1] - fatigue_trend[0] if len(fatigue_trend) >= 2 else 0,
            'cognitive_decline': cognitive_trend[0] - cognitive_trend[-1] if len(cognitive_trend) >= 2 else 0
        }


page_sequence = [
    # Round 1: Vacancy Selection
    VacancySelection,

    # Rounds 2-7: First Vacancy
    Consent,
    BaselineCognitiveTestInstructions,
    BaselineCognitiveTest,
    BaselineCognitiveTestResults,
    RoleSelection,
    WaitForRoles,
    Recruiter,
    HRCoordinator,
    BusinessPartner,
    SelfAssessment,
    CognitiveTestInstructions,
    CognitiveTest,
    CognitiveTestResults,

    # Round 8: Transition Choice
    TransitionChoice,

    # Rounds 9-14: Second Vacancy (conditional)
    BaselineCognitiveTestInstructions,
    BaselineCognitiveTest,
    BaselineCognitiveTestResults,
    RoleSelection,
    WaitForRoles,
    Recruiter,
    HRCoordinator,
    BusinessPartner,
    SelfAssessment,
    CognitiveTestInstructions,
    CognitiveTest,
    CognitiveTestResults,

    # Round 14: Final Results
    FinalResults
]