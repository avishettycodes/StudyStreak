from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import openai
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studyapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

db = SQLAlchemy(app)

# Database Models
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    questions = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, nullable=True)
    course_name = db.Column(db.String(255), nullable=False)
    completed_date = db.Column(db.Date, nullable=True)
    total_questions = db.Column(db.Integer, nullable=True)
    user_answers = db.Column(db.JSON, nullable=True)

class UserStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quizzes_completed = db.Column(db.Integer, default=0)
    total_stars = db.Column(db.Integer, default=0)
    current_level = db.Column(db.Integer, default=1)
    current_streak = db.Column(db.Integer, default=0)
    last_quiz_date = db.Column(db.DateTime, nullable=True)

    def get_level_name(self):
        level_names = {
            1: "Novice Learner",
            2: "Knowledge Seeker",
            3: "Study Enthusiast",
            4: "Academic Explorer",
            5: "Learning Champion",
            6: "Study Master",
            7: "Knowledge Guardian",
            8: "Academic Legend",
            9: "Study Sage",
            10: "Learning Oracle"
        }
        return level_names.get(self.current_level, f"Level {self.current_level} Master")

    def get_next_level_requirement(self):
        level_requirements = {
            1: 1,    # 1 quiz for level 2
            2: 5,    # 5 quizzes for level 3
            3: 15,   # 15 quizzes for level 4
            4: 25,   # 25 quizzes for level 5
            5: 40,   # 40 quizzes for level 6
            6: 60,   # 60 quizzes for level 7
            7: 85,   # 85 quizzes for level 8
            8: 115,  # 115 quizzes for level 9
            9: 150,  # 150 quizzes for level 10
            10: 300  # 300 quizzes for max level
        }
        return level_requirements.get(self.current_level, 300)

class CompletedCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(255), nullable=False)
    completion_date = db.Column(db.DateTime, nullable=False)
    total_score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    days_to_complete = db.Column(db.Integer, nullable=False)
    quizzes_completed = db.Column(db.Integer, nullable=False)
    quizzes_per_day = db.Column(db.Integer, nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.get_json()
        topic = data.get('topic', '')
        days_to_complete = data.get('daysToComplete', 1)
        quizzes_per_day = data.get('quizzesPerDay', 1)
        questions_per_quiz = data.get('questionsPerDay', 10)
        additional_info = data.get('additionalInfo', '')
        
        if not topic:
            return jsonify({'error': 'Please provide a topic for the course.'}), 400

        print(f"Generating quiz for topic: {topic}")
        print(f"Additional info: {additional_info}")

        # Check if user has already completed their daily quizzes
        today = datetime.utcnow().date()
        course_quizzes = Quiz.query.filter(
            Quiz.course_name == topic,
            Quiz.completed_date >= today
        ).count()

        if course_quizzes >= quizzes_per_day:
            return jsonify({
                'error': f'You have already completed {quizzes_per_day} quiz{"es" if quizzes_per_day > 1 else ""} for this course today. Please try again tomorrow.'
            }), 429

        # Generate quiz content using OpenAI
        try:
            # Create a more detailed prompt that includes the additional info
            prompt = f"""Create {questions_per_quiz} multiple choice questions about {topic}.
            {additional_info if additional_info else ''}
            
            Format the response as a JSON object with a 'questions' array, where each question has:
            - 'question': The question text
            - 'options': Array of 4 possible answers
            - 'correct_answer': The index (0-3) of the correct answer
            
            Make sure the questions are challenging and scenario-based if possible.
            Ensure the correct_answer is always a valid index (0-3) and matches one of the options exactly."""

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert quiz creator. Create multiple choice questions that test understanding of the topic. Make sure the correct_answer field is always a valid index (0-3) and matches one of the options exactly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            print(f"Raw response: {response.choices[0].message.content}")
            
            try:
                quiz_data = json.loads(response.choices[0].message.content)
                print(f"Generated quiz data: {json.dumps(quiz_data, indent=2)}")
                
                # Validate the quiz data
                for question in quiz_data['questions']:
                    if not isinstance(question['correct_answer'], int) or question['correct_answer'] < 0 or question['correct_answer'] >= len(question['options']):
                        raise ValueError(f"Invalid correct_answer index: {question['correct_answer']}")
                
                # Add course details to the first question
                quiz_data['questions'][0]['course_details'] = {
                    'daysToComplete': days_to_complete,
                    'quizzesPerDay': quizzes_per_day,
                    'questionsPerQuiz': questions_per_quiz
                }
                
                # Create quiz in database
                quiz = Quiz(
                    questions=quiz_data['questions'],
                    course_name=topic,
                    completed_date=today
                )
                db.session.add(quiz)
                db.session.commit()

                return jsonify({
                    'quiz': quiz_data['questions'],
                    'quiz_id': quiz.id
                }), 200
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {str(e)}")
                print(f"Failed to parse response: {response.choices[0].message.content}")
                return jsonify({'error': 'Invalid quiz format received. Please try again.'}), 500
                
        except Exception as api_error:
            print(f"OpenAI API error: {str(api_error)}")
            return jsonify({'error': f'Failed to generate quiz: {str(api_error)}'}), 500
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/complete-quiz', methods=['GET', 'POST'])
def complete_quiz():
    if request.method == 'GET':
        try:
            # Get user stats
            user_stats = UserStats.query.first()
            if not user_stats:
                user_stats = UserStats()
                db.session.add(user_stats)
                db.session.commit()
            
            return jsonify({
                'current_level': user_stats.current_level,
                'level_name': user_stats.get_level_name(),
                'quizzes_completed': user_stats.quizzes_completed,
                'next_level_requirement': user_stats.get_next_level_requirement(),
                'total_stars': user_stats.total_stars,
                'current_streak': user_stats.current_streak
            })
        except Exception as e:
            print(f"Error getting user stats: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            quiz_id = data.get('quiz_id')
            user_answers = data.get('answers', [])
            score = data.get('score', 0)
            total_questions = data.get('totalQuestions', 0)
            
            if not quiz_id:
                return jsonify({'error': 'Quiz ID is required'}), 400
            
            quiz = Quiz.query.get(quiz_id)
            if not quiz:
                return jsonify({'error': 'Quiz not found'}), 404
            
            # Get course details from the first question
            course_details = quiz.questions[0].get('course_details', {})
            days_to_complete = course_details.get('daysToComplete', 1)
            quizzes_per_day = course_details.get('quizzesPerDay', 1)
            questions_per_quiz = course_details.get('questionsPerQuiz', 10)
            total_required_quizzes = days_to_complete * quizzes_per_day
            
            # Update quiz with completion data
            quiz.completed = True
            quiz.score = score
            quiz.total_questions = total_questions
            quiz.user_answers = user_answers
            quiz.completed_date = datetime.utcnow()
            
            # Get all completed quizzes for this course
            completed_quizzes = Quiz.query.filter_by(
                course_name=quiz.course_name,
                completed=True
            ).all()
            
            total_completed = len(completed_quizzes)
            total_score = sum(q.score for q in completed_quizzes)
            total_questions_answered = sum(q.total_questions for q in completed_quizzes)
            
            # Check if course already exists in CompletedCourse
            existing_completed_course = CompletedCourse.query.filter_by(
                course_name=quiz.course_name
            ).first()
            
            # Calculate course completion
            if total_completed >= total_required_quizzes and not existing_completed_course:
                print(f"Creating completed course entry for {quiz.course_name}")
                print(f"Total completed: {total_completed}, Required: {total_required_quizzes}")
                print(f"Total score: {total_score}, Total questions: {total_questions_answered}")
                
                # Create CompletedCourse entry
                completed_course = CompletedCourse(
                    course_name=quiz.course_name,
                    completion_date=datetime.utcnow(),
                    total_score=total_score,
                    total_questions=total_questions_answered,
                    days_to_complete=days_to_complete,
                    quizzes_completed=total_completed,
                    quizzes_per_day=quizzes_per_day
                )
                db.session.add(completed_course)
                print(f"Added completed course to session: {completed_course.course_name}")
            
            # Get user stats
            user_stats = UserStats.query.first()
            if not user_stats:
                user_stats = UserStats()
                db.session.add(user_stats)
            
            # Update user stats
            user_stats.quizzes_completed += 1
            user_stats.total_stars += score
            
            # Update streak
            current_date = datetime.utcnow()
            if user_stats.last_quiz_date:
                last_date = user_stats.last_quiz_date.date()
                current_date_only = current_date.date()
                if (current_date_only - last_date).days == 1:
                    user_stats.current_streak += 1
                elif (current_date_only - last_date).days > 1:
                    user_stats.current_streak = 1
                elif (current_date_only - last_date).days == 0:
                    # Same day, don't update streak
                    pass
                else:
                    user_stats.current_streak = 1
            else:
                user_stats.current_streak = 1
            
            # Always update last_quiz_date
            user_stats.last_quiz_date = current_date
            
            # Check for level up
            next_level_requirement = user_stats.get_next_level_requirement()
            if user_stats.quizzes_completed >= next_level_requirement and user_stats.current_level < 10:
                user_stats.current_level += 1
            
            try:
                # Save changes
                db.session.commit()
                print(f"Successfully committed changes to database")
            except Exception as commit_error:
                print(f"Error committing to database: {str(commit_error)}")
                db.session.rollback()
                raise commit_error
            
            return jsonify({
                'message': 'Quiz completed successfully',
                'score': score,
                'totalQuestions': total_questions
            }), 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error completing quiz: {str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/api/completed-courses', methods=['GET', 'DELETE'])
def get_completed_courses():
    try:
        if request.method == 'DELETE':
            data = request.get_json()
            course_name = data.get('name')
            if not course_name:
                return jsonify({'error': 'Course name is required'}), 400

            # Delete completed course and all its quizzes
            CompletedCourse.query.filter_by(course_name=course_name).delete()
            Quiz.query.filter_by(course_name=course_name).delete()
            db.session.commit()
            return jsonify({'message': 'Course deleted successfully'})

        # Handle GET request
        completed_courses = CompletedCourse.query.all()
        print(f"Found {len(completed_courses)} completed courses")
        
        courses_data = []
        for course in completed_courses:
            # Calculate statistics
            correct_answers = course.total_score
            total_questions = course.total_questions
            wrong_answers = total_questions - correct_answers
            average_score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            course_data = {
                'name': course.course_name,
                'totalQuizzes': course.quizzes_completed,
                'correctAnswers': correct_answers,
                'wrongAnswers': wrong_answers,
                'averageScore': average_score,
                'completedDate': course.completion_date.isoformat(),
                'daysToComplete': course.days_to_complete,
                'quizzesCompleted': course.quizzes_completed
            }
            courses_data.append(course_data)
            print(f"Added completed course: {course.course_name} with stats: {course_data}")
        
        return jsonify(courses_data)
    except Exception as e:
        print(f"Error handling completed courses: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Initialize database
with app.app_context():
    # Create tables if they don't exist
    db.create_all()
    
    # Check if default user stats exist
    if not UserStats.query.first():
        # Create default user stats
        default_stats = UserStats(
            quizzes_completed=0,
            total_stars=0,
            current_level=1,
            current_streak=0,
            last_quiz_date=None
        )
        db.session.add(default_stats)
        db.session.commit()
        print("Created default user stats")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4444, debug=True) 