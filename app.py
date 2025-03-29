from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import openai
import os
from dotenv import load_dotenv
import json
from docx import Document
import io
from PyPDF2 import PdfReader

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studyapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

db = SQLAlchemy(app)

# Database Models
class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    questions = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, nullable=True)

class UserStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quizzes_completed = db.Column(db.Integer, default=0)
    total_stars = db.Column(db.Integer, default=0)
    current_level = db.Column(db.Integer, default=1)
    current_streak = db.Column(db.Integer, default=0)
    last_quiz_date = db.Column(db.DateTime, nullable=True)

def extract_text_from_file(file):
    try:
        if file.filename.endswith('.txt'):
            content = file.read().decode('utf-8')
            file.seek(0)  # Reset file pointer
            return content
        elif file.filename.endswith('.pdf'):
            # Process PDF files
            pdf_reader = PdfReader(io.BytesIO(file.read()))
            file.seek(0)  # Reset file pointer
            
            # Extract text from all pages
            text_content = []
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            return '\n'.join(text_content)
        elif file.filename.endswith('.docx'):
            # Process DOCX files
            doc = Document(io.BytesIO(file.read()))
            file.seek(0)  # Reset file pointer
            full_text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():  # Only add non-empty paragraphs
                    full_text.append(paragraph.text)
            return '\n'.join(full_text)
        return None
    except Exception as e:
        print(f"Error extracting text from file: {str(e)}")
        return None

def allowed_file(filename):
    allowed_extensions = {'txt', 'pdf', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        print("No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        print("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    try:
        for file in files:
            if file and allowed_file(file.filename):
                print(f"Processing file: {file.filename}")
                content = extract_text_from_file(file)
                if content:
                    print(f"Successfully extracted content from {file.filename}")
                    study_material = StudyMaterial(
                        filename=file.filename,
                        content=content
                    )
                    db.session.add(study_material)
                else:
                    print(f"Failed to extract content from {file.filename}")
            else:
                print(f"File not allowed: {file.filename}")
        
        db.session.commit()
        print("Files uploaded successfully")
        return jsonify({'message': 'Files uploaded successfully'}), 200
    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/files', methods=['GET'])
def get_files():
    try:
        files = StudyMaterial.query.order_by(StudyMaterial.created_at.desc()).all()
        return jsonify({
            'files': [{
                'id': file.id,
                'filename': file.filename,
                'created_at': file.created_at.isoformat()
            } for file in files]
        })
    except Exception as e:
        print(f"Error fetching files: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    try:
        file = StudyMaterial.query.get_or_404(file_id)
        db.session.delete(file)
        db.session.commit()
        return jsonify({'message': 'File deleted successfully'})
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        # Get the most recent study material
        study_material = StudyMaterial.query.order_by(StudyMaterial.created_at.desc()).first()
        
        if not study_material:
            return jsonify({'error': 'No study material found. Please upload a file first.'}), 404

        print(f"Generating quiz from content: {study_material.content[:100]}...")  # Print first 100 chars for debugging

        # Generate quiz using OpenAI
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a quiz generator. Create multiple choice questions based on the provided content. Each question should have 4 options with one correct answer. Format the response as a JSON array of questions, where each question has 'question', 'options', and 'correct_answer' fields. Example format: [{\"question\": \"What is X?\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct_answer\": 0}]"},
                    {"role": "user", "content": f"Create a quiz with 5 multiple choice questions based on this content: {study_material.content}"}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            # Print the raw response for debugging
            print(f"Raw response: {response.choices[0].message['content']}")
            
            try:
                quiz_data = json.loads(response.choices[0].message['content'])
                print(f"Generated quiz data: {json.dumps(quiz_data, indent=2)}")  # Print generated quiz for debugging
                
                # Create quiz in database
                quiz = Quiz(questions=quiz_data)
                db.session.add(quiz)
                db.session.commit()

                return jsonify({
                    'quiz': quiz_data,
                    'quiz_id': quiz.id
                }), 200
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {str(e)}")
                print(f"Failed to parse response: {response.choices[0].message['content']}")
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
                'quizzes_completed': user_stats.quizzes_completed,
                'next_level_requirement': user_stats.current_level * 5,
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
            current_level = user_stats.current_level
            next_level_requirement = current_level * 5  # 5 quizzes per level
            
            if user_stats.quizzes_completed >= next_level_requirement:
                user_stats.current_level += 1
            
            # Save changes
            db.session.commit()
            
            return jsonify({
                'current_level': user_stats.current_level,
                'quizzes_completed': user_stats.quizzes_completed,
                'next_level_requirement': user_stats.current_level * 5,
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