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
            correct_answers = data.get('correct_answers', 0)
            
            # Calculate stars earned (10 stars per quiz)
            stars_earned = 10
            
            # Get user stats
            user_stats = UserStats.query.first()
            if not user_stats:
                user_stats = UserStats()
                db.session.add(user_stats)
            
            # Update user stats
            user_stats.quizzes_completed += 1
            user_stats.total_stars += stars_earned
            
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
            
            # Save changes
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
            db.session.rollback()
            print(f"Error in complete_quiz: {str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

# Initialize database
with app.app_context():
    # Drop all tables first
    db.drop_all()
    # Create all tables
    db.create_all()
    
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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4444, debug=True) 