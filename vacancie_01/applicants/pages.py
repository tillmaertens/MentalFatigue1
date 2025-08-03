from otree.api import *  # Core oTree framework
from .models import C, get_vacancy_info, get_applicants_data_for_vacancy, \
    load_metadata_criteria, should_show_vacancy_session, get_applicant_ids, \
    assign_rotating_role, get_vacancy_session_number    # imports from models.py
import random  # for StroopTest Items
from docx import Document  # Word -> HTML converting
import os  # file paths
import json


class Consent(Page):

    def is_displayed(self):
        return self.player.round_number == 1  # only shown in the very first round


# MAIN TASK PAGES

class Recruiter(Page):
    """
    Reviews applicant information including CVs, job references, and cover letters.

    Data Processing Flow:
    1. Get current vacancy configuration (vacancy 1 or 2)
    2. Load basic applicant data (names, document paths)
    3. Load and convert Word documents to HTML for each applicant
    4. Calculate session numbering and progress indicators
    5. Assemble all data for template rendering

    Returns:
    dict: Template variables containing:
        - applicants: List of applicant objects with HTML content
        - session_number: Current session within vacancy (1-6)

        Same for all player Classes:
        - vacancy_number: Which vacancy is active (1 or 2)
        - remaining_time: Session timeout in seconds
        - static_path: Path to static files (PDFs, images)
        - total_sessions: Total sessions per vacancy (6)
    """

    def is_displayed(self):
        """
        Only shown during active vacancy sessions.
        Automatically assigns rotating roles and checks if player has Recruiter role.
        """
        if not should_show_vacancy_session(self.player.round_number):
            return False

        # AUTOMATIC ROLE ASSIGNMENT
        assign_rotating_role(self.player)
        return self.player.is_recruiter()

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info[
            'duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS  # Calcultes timeout based on Vacancie number

    timeout_seconds = property(get_timeout_seconds)  # Convert method to property for oTree

    def vars_for_template(self):
        """
        Loads and processes all data needed for the recruiter interface.
        """
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        applicants_with_content = []
        doc_suffix = vacancy_info['doc_suffix'] if vacancy_info else '1'

        for applicant in applicants_data:
            # Create copy to avoid modifying original data
            applicant_data = applicant.copy()
            applicant_data['description'] = self.get_word_content(applicant['id'], doc_suffix)
            applicants_with_content.append(applicant_data)

        session_number = get_vacancy_session_number(self.player.round_number)
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'applicants': applicants_with_content,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'remaining_time': vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS,
            'static_path': C.STATIC_APPLICANTS_PATH,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }

    def get_word_content(self, applicant_id, doc_suffix='1'):
        """
        Loads recruiter mask Word document.

        Args:
            applicant_id (str): Applicant identifier ('a', 'b', or 'c')
            doc_suffix (str): Vacancy-specific suffix ('1' or '2')

        Returns:
            str: HTML content for web display, or error message if file not found
        """
        try:
            # Build absolute path to Word document
            current_dir = os.path.dirname(os.path.abspath(__file__))

            doc_path = os.path.join(
                current_dir,
                '..',
                '_static',
                'applicants',
                f'recruiter_maske_{applicant_id}{doc_suffix}.docx'
            )

            # Normalize path for cross-platform compatibility
            doc_path = os.path.normpath(doc_path)

            # Load Word document and convert to HTML
            document = Document(doc_path)
            html_content = self.convert_docx_to_html(document)
            return html_content

        except Exception as e:
            return f"<p><em>Error loading document: {str(e)}</em></p>"

    def convert_docx_to_html(self, document):
        """
        Processes Word document content and converts it to styled HTML.

        Args:
        document: python-docx Document object

        Returns:
        str: HTML content with styling ready for web display
        """
        html_parts = []

        # Process paragraphs and headings
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                # Convert Word headings to HTML heading tags
                if paragraph.style.name.startswith('Heading'):
                    level = 3
                    if 'Heading 1' in paragraph.style.name:
                        level = 2
                    elif 'Heading 2' in paragraph.style.name:
                        level = 3
                    html_parts.append(f'<h{level}>{text}</h{level}>')
                else:
                    # Regular paragraphs with bold text detection
                    if any(run.bold for run in paragraph.runs):
                        html_parts.append(f'<p><strong>{text}</strong></p>')
                    else:
                        html_parts.append(f'<p>{text}</p>')

        # Process tables with styling and header detection
        for table in document.tables:
            html_parts.append('<table style="width:100%; border-collapse: collapse; margin: 10px 0;">')

            for row_idx, row in enumerate(table.rows):
                html_parts.append('<tr>')
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    # Style header cells differently
                    if row_idx == 0 or any(run.bold for para in cell.paragraphs for run in para.runs):
                        html_parts.append(
                            f'<td style="border: 1px solid #ddd; padding: 5px; font-weight: bold; background-color: #f5f5f5;">{cell_text}</td>')
                    else:
                        html_parts.append(f'<td style="border: 1px solid #ddd; padding: 5px;">{cell_text}</td>')
                html_parts.append('</tr>')

            html_parts.append('</table>')

        if not html_parts:
            return "<p><em>The Word document is empty or could not be read.</em></p>"

        # Combine all HTML parts into final output
        return ''.join(html_parts)


class HRCoordinator(Page):
    """
    Prepares all data needed for HR Coordinator interface.

    Data Processing Flow:
    1. Get current vacancy configuration
    2. Load basic applicant data (names, document paths)
    3. Load evaluation metadata for interactive criteria system
    4. Calculate session numbering and progress indicators
    5. Assemble evaluation interface data for template rendering

    Returns:
        dict: Template variables containing:
            - applicants: Full applicant data for evaluation table
            - criteria_data: All criteria for modal selection system
            - categories/criteria_by_category: Criteria organization for modal
            - relevance_factors: Scoring multipliers (low:1, normal:2, high:3)
            - applicant_colors: Colors for live pie chart display
            - job_desc_file: PDF file for job description access
            - min_score/max_score: Score range for evaluation dropdowns (0-8)
            - applicant_ids: List for score validation (['a', 'b', 'c'])

    Form Fields:
        - criteria_added_this_session: Count of criteria added by player
        - validation_data_json: Hidden field containing criteria data for validation
    """
    form_model = 'player'
    form_fields = ['criteria_added_this_session', 'validation_data_json']

    def is_displayed(self):
        """
        Display logic and automatic role assignment.
        Uses the same rotating role assignment as other task pages.
        """
        if not should_show_vacancy_session(self.player.round_number):
            return False

        # AUTOMATIC ROLE ASSIGNMENT
        assign_rotating_role(self.player)
        return self.player.is_hr_coordinator()

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS

    timeout_seconds = property(get_timeout_seconds)

    def before_next_page(self):
        """
        Validates player's criteria data against correct answers before proceeding.
        Takes JSON data from frontend, compares it with metadata, and counts how many criteria were evaluated correctly vs incorrectly.
        """
        import json

        try:
            # Get criteria data from hidden form field (sent by JavaScript)
            validation_data_str = self.player.validation_data_json or '{}'

            if not validation_data_str or validation_data_str == '{}':
                self.player.criteria_correct_this_session = 0
                self.player.criteria_incorrect_this_session = 0
                return

            # Parse JSON data from frontend
            criteria_data = json.loads(validation_data_str)
            correct_count = 0
            incorrect_count = 0

            # Load correct answers from metadata files
            metadata = load_metadata_criteria(self.player.round_number, self.player)
            metadata_criteria = metadata['criteria']

            # Check each criterion the player evaluated
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
                    for applicant_id in get_applicant_ids():
                        entered_score = data['scores'].get(applicant_id, 0)
                        correct_score = criterion_metadata['scores'].get(f'applicant_{applicant_id}', 0)

                        if int(entered_score or 0) != int(correct_score):
                            scores_correct = False
                            break

                    # Validate relevance level
                    entered_relevance = data.get('relevance', 'normal')
                    correct_relevance = criterion_metadata.get('relevance', 'normal')
                    relevance_correct = entered_relevance == correct_relevance

                    # Count correct or incorrect
                    if scores_correct and relevance_correct:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                else:
                    # Criterion not found in metadata = incorrect
                    incorrect_count += 1

            # Save results to player fields for later analysis
            self.player.criteria_correct_this_session = correct_count
            self.player.criteria_incorrect_this_session = incorrect_count

        except Exception as e:
            self.player.criteria_correct_this_session = 0
            self.player.criteria_incorrect_this_session = 0

    def vars_for_template(self):
        """
        Prepares all data needed for HR Coordinator interface.
        """
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        # Load evaluation criteria and categories from Excel metadata
        metadata = load_metadata_criteria(self.player.round_number, self.player)

        # Calculate session progress
        session_number = get_vacancy_session_number(self.player.round_number)
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
            'relevance_factors': C.RELEVANCE_FACTORS,
            'job_desc_file': vacancy_info['job_desc_file'] if vacancy_info else 'job_description_1.pdf',
            'static_path': C.STATIC_APPLICANTS_PATH,
            'applicant_colors': C.APPLICANT_COLORS,
            'applicant_ids': get_applicant_ids(),
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class BusinessPartner(Page):
    """
    Prepares data for Business Partner requirements catalog interface.

    Data Processing Flow:
    1. Get current vacancy configuration
    2. Load basic applicant data (not used directly in interface)
    3. Load criteria metadata for requirements catalog
    4. Calculate session numbering and progress indicators
    5. Assemble catalog data for template rendering

    Returns:
        dict: Template variables containing:
            - criteria_data: All evaluation criteria for catalog browsing
            - categories: Criteria categories for navigation
            - criteria_by_category: Grouped criteria for category selection
            - min_score/max_score: Score range for criteria viewing (0-8)
    """

    def is_displayed(self):
        if should_show_vacancy_session(self.player.round_number):
            assign_rotating_role(self.player)
            return self.player.is_business_partner()
        return False

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS

    timeout_seconds = property(get_timeout_seconds)

    def vars_for_template(self):
        """
        Prepares data for Business Partner requirements catalog interface.
        """
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        metadata = load_metadata_criteria(self.player.round_number, self.player)

        session_number = get_vacancy_session_number(self.player.round_number)
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'applicants': applicants_data,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'remaining_time': vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS,
            'criteria_data': metadata['criteria'],
            'categories': metadata['categories'],
            'criteria_by_category': metadata['criteria_by_category'],
            'static_path': C.STATIC_APPLICANTS_PATH,
            'min_score': C.MIN_SCORE,
            'max_score': C.MAX_SCORE,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class SelfAssessment(Page):
    """
    Post-session questionnaire for measuring mental fatigue and subjective workload.

    Form Fields:
        - fatigue_level: Self-reported fatigue (1=not tired, 10=extremely tired)
        - mental_effort: Mental effort required (1=very low, 10=very high)
        - concentration_difficulty: Difficulty concentrating (1=easy, 10=difficult)
        - motivation_level: Current motivation (1=very low, 10=very high)
    """
    form_model = 'player'
    form_fields = ['fatigue_level', 'mental_effort', 'concentration_difficulty', 'motivation_level']

    def is_displayed(self):
        """
        Shown to ALL players after task sessions, no role assignment needed.
        Only displayed during active vacancy rounds.
        """
        if not should_show_vacancy_session(self.player.round_number):
            return False
        return True

    def vars_for_template(self):
        """
        Prepares session information for self-assessment form.
        """
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = get_vacancy_session_number(self.player.round_number)
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'role_played': self.player.selected_role,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class CognitiveTestInstructions(Page):
    """
    Instructions page for cognitive test before actual test execution.
    """
    timeout_seconds = 20

    def is_displayed(self):
        if not should_show_vacancy_session(self.player.round_number):
            return False
        return True

    def vars_for_template(self):
        """
        Prepares session information for test instructions.
        """
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = get_vacancy_session_number(self.player.round_number)
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class CognitiveTest(Page):
    """
    Stroop test for measuring cognitive load and performance changes over sessions.

    Data Processing Flow:
    1. Get current vacancy configuration
    2. Generate random Stroop test items (word-color mismatches)
    3. Create color mapping for answer validation
    4. Calculate session numbering and progress indicators
    5. Assemble test data for interactive interface

    Returns:
    dict: Template variables containing:
        - test_items: List of 20 random Stroop test items
        - test_duration: Test time limit (30 seconds)

    Form Fields:
        - cognitive_test_score: Number of correct answers
        - cognitive_test_reaction_time: Average reaction time in milliseconds
        - cognitive_test_errors: Number of incorrect answers
    """
    form_model = 'player'
    form_fields = ['cognitive_test_score', 'cognitive_test_reaction_time', 'cognitive_test_errors']
    timeout_seconds = 30

    def is_displayed(self):
        """
        Shown to ALL players after task sessions, no role assignment needed.
        Only displayed during active vacancy rounds.
        """
        if not should_show_vacancy_session(self.player.round_number):
            return False
        return True

    def vars_for_template(self):
        """
        Generates random Stroop test items and prepares test interface.
        """
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = get_vacancy_session_number(self.player.round_number)
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
            'vacancy_number': vacancy_number,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class CognitiveTestResults(Page):
    """
    Displays results of the completed Stroop test to participants.

    Returns:
        dict: Template variables containing:
            - score: Number of correct answers (0-20)
            - reaction_time: Average reaction time in milliseconds
            - errors: Number of incorrect answers
            - total_items: Total test items (20)
    """
    timeout_seconds = 20

    def is_displayed(self):
        """
        Shown to ALL players after cognitive test completion.
        Only displayed during active vacancy rounds.
        """
        if not should_show_vacancy_session(self.player.round_number):
            return False
        return True

    def vars_for_template(self):
        """
        Loads cognitive test results and prepares results display.
        """
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = get_vacancy_session_number(self.player.round_number)
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'score': self.player.field_maybe_none('cognitive_test_score') or 0,
            'reaction_time': self.player.field_maybe_none('cognitive_test_reaction_time') or 0,
            'errors': self.player.field_maybe_none('cognitive_test_errors') or 0,
            'total_items': 20,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class FinalResults(Page):
    """
    Comprehensive results analysis after completing vacancy sessions.

    Data Processing Flow:
    1. Determine which vacancy results to show (1 or 2)
    2. Collect historical data from all completed sessions
    3. Extract player performance metrics with null safety
    4. Calculate fatigue and performance trends over time
    5. Compute statistical summaries and averages
    6. Assemble complete results for charts and analysis

    Returns:
        dict: Template variables containing:
            - all_sessions: Complete session-by-session data
            - results_vacancy: Which vacancy results are shown (1 or 2)
            - total_sessions_completed: Number of completed sessions
            - average_fatigue: Mean fatigue level across sessions
            - fatigue_increase: Change from first to last session
            - cognitive_decline: Performance change over time
            - average_effort: Mean mental effort reported
            - average_concentration: Mean concentration difficulty
            - average_motivation: Mean motivation level
            - show_next_button: Whether to show continue button (vacancy 1 only)
            - is_vacancy_1_results: Boolean for template logic
    """

    def is_displayed(self):
        """
        Shown after completing all sessions of a vacancy (rounds 7 and 14).
        """
        return (self.player.round_number == C.VACANCY_1_RESULTS_ROUND or
                self.player.round_number == C.FINAL_RESULTS_ROUND)

    def vars_for_template(self):
        """
        Compiles comprehensive results analysis from all completed sessions.
        """
        is_vacancy_1_results = self.player.round_number == C.VACANCY_1_RESULTS_ROUND
        show_next_button = is_vacancy_1_results

        if is_vacancy_1_results:
            start_round = C.VACANCY_1_START_ROUND  # 1
            end_round = C.VACANCY_1_END_ROUND  # 6
            results_vacancy = 1
        else:
            start_round = C.VACANCY_2_START_ROUND  # 8
            end_round = C.VACANCY_2_END_ROUND  # 13
            results_vacancy = 2

        # Compile results with null safety
        all_sessions_data = []
        for round_num in range(start_round, end_round + 1):
            try:
                round_player = self.player.in_round(round_num)

                # Safe access with try-except for oTree fields
                def safe_get(field_func, default=0):
                    try:
                        value = field_func()
                        return value if value is not None else default
                    except:
                        return default

                session_data = {
                    'session': round_num - start_round + 1,  # Display as 1-6
                    'role': safe_get(lambda: round_player.selected_role, 'Unknown'),
                    'fatigue_level': safe_get(lambda: round_player.fatigue_level),
                    'mental_effort': safe_get(lambda: round_player.mental_effort),
                    'concentration_difficulty': safe_get(lambda: round_player.concentration_difficulty),
                    'motivation_level': safe_get(lambda: round_player.motivation_level),
                    'cognitive_score': safe_get(lambda: round_player.cognitive_test_score),
                    'cognitive_reaction_time': safe_get(lambda: round_player.cognitive_test_reaction_time),
                    'criteria_added': safe_get(lambda: round_player.criteria_added_this_session),
                    'criteria_correct': safe_get(lambda: round_player.criteria_correct_this_session),
                    'criteria_incorrect': safe_get(lambda: round_player.criteria_incorrect_this_session),
                }
                all_sessions_data.append(session_data)
            except Exception as e:
                # Skip sessions with data access errors
                continue

        # Extract valid values for trend calculations with null safety
        fatigue_values = [s['fatigue_level'] for s in all_sessions_data if
                          s['fatigue_level'] and s['fatigue_level'] > 0]
        cognitive_values = [s['cognitive_score'] for s in all_sessions_data if
                            s['cognitive_score'] and s['cognitive_score'] > 0]
        effort_values = [s['mental_effort'] for s in all_sessions_data if s['mental_effort'] and s['mental_effort'] > 0]
        concentration_values = [s['concentration_difficulty'] for s in all_sessions_data if
                                s['concentration_difficulty'] and s['concentration_difficulty'] > 0]
        motivation_values = [s['motivation_level'] for s in all_sessions_data if
                             s['motivation_level'] and s['motivation_level'] > 0]

        # Safe calculations
        average_fatigue = sum(fatigue_values) / len(fatigue_values) if fatigue_values else 0
        fatigue_increase = fatigue_values[-1] - fatigue_values[0] if len(fatigue_values) >= 2 else 0
        cognitive_decline = cognitive_values[0] - cognitive_values[-1] if len(cognitive_values) >= 2 else 0

        # Additional averages
        average_effort = sum(effort_values) / len(effort_values) if effort_values else 0
        average_concentration = sum(concentration_values) / len(concentration_values) if concentration_values else 0
        average_motivation = sum(motivation_values) / len(motivation_values) if motivation_values else 0

        result = {
            # Raw session data for detailed tables and charts
            'all_sessions': all_sessions_data,

            'results_vacancy': results_vacancy,
            'total_sessions_completed': len(all_sessions_data),
            'average_fatigue': average_fatigue,
            'fatigue_increase': fatigue_increase,
            'cognitive_decline': cognitive_decline,
            'average_effort': average_effort,
            'average_concentration': average_concentration,
            'average_motivation': average_motivation,
            'show_next_button': show_next_button,
            'is_vacancy_1_results': is_vacancy_1_results
        }
        return result

#Page Sequence of the experiment
page_sequence = [
    Consent,
    Recruiter,
    HRCoordinator,
    BusinessPartner,
    SelfAssessment,
    CognitiveTestInstructions,
    CognitiveTest,
    CognitiveTestResults,
    FinalResults
]
