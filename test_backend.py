import unittest
from app import app, db, Quiz, UserStats, Course
from datetime import datetime, timedelta
import json

class TestStudyApp(unittest.TestCase):
    def setUp(self):
        """Set up test database and client"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_generate_quiz(self):
        """Test quiz generation endpoint"""
        # Test data
        test_data = {
            'topic': 'Test Course',
            'daysToComplete': 1,
            'quizzesPerDay': 1,
            'questionsPerDay': 5,
            'additionalInfo': 'Test quiz generation'
        }

        # Make request to generate quiz
        response = self.client.post('/api/generate-quiz',
                                  data=json.dumps(test_data),
                                  content_type='application/json')

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify quiz structure
        self.assertIn('quiz', data)
        self.assertIn('quiz_id', data)
        self.assertEqual(len(data['quiz']), 5)  # Should have 5 questions
        
        # Verify question structure
        for question in data['quiz']:
            self.assertIn('question', question)
            self.assertIn('options', question)
            self.assertIn('correct_answer', question)
            self.assertEqual(len(question['options']), 4)
            self.assertIsInstance(question['correct_answer'], int)
            self.assertGreaterEqual(question['correct_answer'], 0)
            self.assertLess(question['correct_answer'], 4)

    def test_complete_quiz(self):
        """Test quiz completion endpoint"""
        # Create a test quiz
        quiz = Quiz(
            questions=[{
                'question': 'Test question',
                'options': ['A', 'B', 'C', 'D'],
                'correct_answer': 0
            }],
            course_name='Test Course',
            completed_date=datetime.utcnow().date()
        )
        db.session.add(quiz)
        db.session.commit()

        # Test data
        test_data = {
            'correct_answers': 1,
            'course_name': 'Test Course',
            'quiz_id': quiz.id,
            'course_details': {
                'daysToComplete': 1,
                'quizzesPerDay': 1
            }
        }

        # Make request to complete quiz
        response = self.client.post('/api/complete-quiz',
                                  data=json.dumps(test_data),
                                  content_type='application/json')

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify quiz completion
        self.assertTrue(data['is_course_completed'])
        self.assertEqual(data['completed_quizzes'], 1)
        self.assertEqual(data['total_required_quizzes'], 1)
        
        # Verify user stats update
        user_stats = UserStats.query.first()
        self.assertEqual(user_stats.quizzes_completed, 1)
        self.assertEqual(user_stats.total_stars, 6)  # 5 base stars + 1 correct answer

    def test_daily_quiz_limit(self):
        """Test daily quiz limit enforcement"""
        # Create a test quiz for today
        quiz = Quiz(
            questions=[{
                'question': 'Test question',
                'options': ['A', 'B', 'C', 'D'],
                'correct_answer': 0
            }],
            course_name='Test Course',
            completed_date=datetime.utcnow().date()
        )
        db.session.add(quiz)
        db.session.commit()

        # Test data
        test_data = {
            'topic': 'Test Course',
            'daysToComplete': 1,
            'quizzesPerDay': 1,
            'questionsPerDay': 5
        }

        # Try to generate another quiz for the same day
        response = self.client.post('/api/generate-quiz',
                                  data=json.dumps(test_data),
                                  content_type='application/json')

        # Check response
        self.assertEqual(response.status_code, 429)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('already completed', data['error'].lower())

    def test_user_stats(self):
        """Test user stats tracking"""
        # Create initial user stats
        user_stats = UserStats()
        db.session.add(user_stats)
        db.session.commit()

        # Test GET request for user stats
        response = self.client.get('/api/complete-quiz')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify initial stats
        self.assertEqual(data['current_level'], 1)
        self.assertEqual(data['quizzes_completed'], 0)
        self.assertEqual(data['total_stars'], 0)
        self.assertEqual(data['current_streak'], 0)

    def test_streak_calculation(self):
        """Test streak calculation logic"""
        # Create user stats with a quiz from yesterday
        user_stats = UserStats(
            last_quiz_date=datetime.utcnow() - timedelta(days=1)
        )
        db.session.add(user_stats)
        db.session.commit()

        # Complete a quiz today
        test_data = {
            'correct_answers': 1,
            'course_name': 'Test Course',
            'quiz_id': 1,
            'course_details': {'daysToComplete': 1, 'quizzesPerDay': 1}
        }

        response = self.client.post('/api/complete-quiz',
                                  data=json.dumps(test_data),
                                  content_type='application/json')

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify streak increased
        self.assertEqual(data['current_streak'], 1)

if __name__ == '__main__':
    unittest.main() 