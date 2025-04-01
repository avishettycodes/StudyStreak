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
    name = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    days_to_complete = db.Column(db.Integer, nullable=False)
    quizzes_per_day = db.Column(db.Integer, nullable=False)
    questions_per_quiz = db.Column(db.Integer, nullable=False)
    additional_info = db.Column(db.Text)
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
        topic = data.get('topic')
        additional_info = data.get('additionalInfo', '')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
            
        # Get course details
        course = Course.query.filter_by(name=topic).first()
        if not course:
            # Create a new course if it doesn't exist
            course = Course(
                name=topic,
                content=additional_info,
                days_to_complete=data.get('daysToComplete', 1),
                quizzes_per_day=data.get('quizzesPerDay', 1),
                questions_per_quiz=data.get('questionsPerDay', 5),
                additional_info=additional_info
            )
            db.session.add(course)
            db.session.commit()
            
        # Check daily quiz limit
        today = datetime.utcnow().date()
        completed_today = Quiz.query.filter(
            Quiz.course_name == topic,
            Quiz.completed == True,
            Quiz.completed_date == today
        ).count()
        
        if completed_today >= course.quizzes_per_day:
            return jsonify({'error': 'Daily quiz limit reached. You have already completed your quizzes for today.'}), 429
            
        # Create a more specific prompt using course details
        prompt = f"""Generate a quiz about {topic} with the following specifications:
        - Number of questions: {course.questions_per_quiz}
        - Difficulty: Challenging
        - Format: Multiple choice with 4 options
        - Additional context: {additional_info}
        
        The quiz should be based on the following course details:
        - Course Name: {course.name}
        - Days to Complete: {course.days_to_complete}
        - Quizzes per Day: {course.quizzes_per_day}
        - Questions per Quiz: {course.questions_per_quiz}
        
        Please generate questions that are:
        1. Based on the course content and additional information provided
        2. Challenging but fair
        3. Include real-world scenarios
        4. Have clear, unambiguous answers
        5. Test understanding rather than memorization
        
        Format each question as:
        {{
            "question": "Question text",
            "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
            "correct_answer": 0  // Index of correct answer (0-3)
        }}
        
        Return the response as a JSON object with a "questions" array containing the questions.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a quiz generation expert. Generate challenging, scenario-based questions based on the provided course content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse the response
        try:
            quiz_data = json.loads(response.choices[0].message.content)
            questions = quiz_data.get('questions', [])
            
            # Store the quiz in the database
            quiz = Quiz(
                course_name=course.name,
                questions=json.dumps(questions),
                created_at=datetime.utcnow()
            )
            db.session.add(quiz)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'quiz': questions,
                'quiz_id': quiz.id
            })
            
        except json.JSONDecodeError:
            return jsonify({'error': 'Failed to parse quiz data'}), 500
            
    except Exception as e:
        print(f"Error generating quiz: {str(e)}")
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
            correct_answers = data.get('correct_answers', 0)
            total_questions = data.get('totalQuestions', 0)
            course_name = data.get('course_name')
            
            if not quiz_id:
                return jsonify({'error': 'Quiz ID is required'}), 400
            
            quiz = Quiz.query.get(quiz_id)
            if not quiz:
                return jsonify({'error': 'Quiz not found'}), 404
            
            # Get course details
            course_details = data.get('course_details', {})
            days_to_complete = course_details.get('daysToComplete', 1)
            quizzes_per_day = course_details.get('quizzesPerDay', 1)
            total_required_quizzes = days_to_complete * quizzes_per_day
            
            # Update quiz with completion data
            quiz.completed = True
            quiz.score = correct_answers
            quiz.total_questions = total_questions
            quiz.user_answers = user_answers
            quiz.completed_date = datetime.utcnow().date()
            
            # Get all completed quizzes for this course
            completed_quizzes = Quiz.query.filter_by(
                course_name=course_name,
                completed=True
            ).all()
            
            total_completed = len(completed_quizzes)
            total_score = sum(q.score or 0 for q in completed_quizzes)
            total_questions_answered = sum(q.total_questions or 0 for q in completed_quizzes)
            
            # Check if course already exists in CompletedCourse
            existing_completed_course = CompletedCourse.query.filter_by(
                course_name=course_name
            ).first()
            
            is_course_completed = total_completed >= total_required_quizzes and not existing_completed_course
            
            # Calculate course completion
            if is_course_completed:
                print(f"Creating completed course entry for {course_name}")
                print(f"Total completed: {total_completed}, Required: {total_required_quizzes}")
                print(f"Total score: {total_score}, Total questions: {total_questions_answered}")
                
                # Create CompletedCourse entry
                completed_course = CompletedCourse(
                    course_name=course_name,
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
            user_stats.total_stars += (5 + correct_answers)  # Base stars + correct answers
            
            # Update streak
            current_date = datetime.utcnow()
            if user_stats.last_quiz_date:
                last_date = user_stats.last_quiz_date.date()
                current_date_only = current_date.date()
                days_diff = (current_date_only - last_date).days
                
                if days_diff == 1:
                    # Increment streak for consecutive days
                    user_stats.current_streak += 1
                elif days_diff > 1:
                    # Reset streak if more than one day gap
                    user_stats.current_streak = 1
                # Keep current streak if same day
            else:
                # First quiz ever
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
                'totalQuestions': total_questions,
                'is_course_completed': is_course_completed,
                'completed_quizzes': total_completed,
                'total_required_quizzes': total_required_quizzes
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

@app.route('/api/courses', methods=['POST'])
def create_course():
    try:
        # Get form data
        course_name = request.form.get('name')
        days_to_complete = int(request.form.get('daysToComplete', 1))
        quizzes_per_day = int(request.form.get('quizzesPerDay', 1))
        questions_per_quiz = int(request.form.get('questionsPerQuiz', 10))
        additional_info = request.form.get('additionalInfo', '')

        # Validate required fields
        if not course_name:
            return jsonify({'error': 'Course name is required'}), 400

        # Validate numeric fields
        if not (1 <= days_to_complete <= 365):
            return jsonify({'error': 'Days to complete must be between 1 and 365'}), 400
        if not (1 <= quizzes_per_day <= 5):
            return jsonify({'error': 'Quizzes per day must be between 1 and 5'}), 400
        if not (1 <= questions_per_quiz <= 50):
            return jsonify({'error': 'Questions per quiz must be between 1 and 50'}), 400

        # Process uploaded files
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'At least one file is required'}), 400

        # Combine file contents
        combined_content = []
        for file in files:
            if file.filename:
                # Read file content based on file type
                if file.filename.endswith('.txt'):
                    content = file.read().decode('utf-8')
                elif file.filename.endswith('.pdf'):
                    # Handle PDF files (you'll need to add PDF processing logic)
                    content = "PDF content processing not implemented yet"
                elif file.filename.endswith('.docx'):
                    # Handle DOCX files (you'll need to add DOCX processing logic)
                    content = "DOCX content processing not implemented yet"
                else:
                    return jsonify({'error': 'Unsupported file type'}), 400
                
                combined_content.append(content)

        # Create new course
        course = Course(
            name=course_name,
            content='\n'.join(combined_content),
            days_to_complete=days_to_complete,
            quizzes_per_day=quizzes_per_day,
            questions_per_quiz=questions_per_quiz,
            additional_info=additional_info
        )
        
        db.session.add(course)
        db.session.commit()

        # Return course data for frontend
        course_data = {
            'id': course.id,
            'name': course.name,
            'daysToComplete': course.days_to_complete,
            'quizzesPerDay': course.quizzes_per_day,
            'questionsPerQuiz': course.questions_per_quiz,
            'additionalInfo': course.additional_info,
            'progress': 0,
            'quizzesCompleted': 0,
            'createdAt': course.created_at.isoformat()
        }

        return jsonify({
            'message': 'Course created successfully',
            'course': course_data
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating course: {str(e)}")
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