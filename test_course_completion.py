import unittest
from app import app, db, Quiz, UserStats
from datetime import datetime
import json

class TestCourseCompletion(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_course_completion(self):
        # Create a test course with 2 days and 2 quizzes per day (total 4 quizzes)
        course_name = "Test Course"
        days_to_complete = 2
        quizzes_per_day = 2
        total_required_quizzes = days_to_complete * quizzes_per_day

        # Create test quizzes
        for i in range(total_required_quizzes):
            quiz = Quiz(
                questions=[{"question": "Test", "options": ["A", "B", "C", "D"], "correct_answer": 0}],
                course_name=course_name,
                completed=True,
                score=1,
                completed_date=datetime.utcnow()
            )
            db.session.add(quiz)
        db.session.commit()

        # Create user stats
        user_stats = UserStats()
        db.session.add(user_stats)
        db.session.commit()

        # Test course completion
        response = self.client.post('/api/complete-quiz', json={
            'correct_answers': 1,
            'course_name': course_name,
            'quiz_id': 1,
            'course_details': {
                'daysToComplete': days_to_complete,
                'quizzesPerDay': quizzes_per_day
            }
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify course completion status
        self.assertTrue(data['is_course_completed'])
        self.assertEqual(data['completed_quizzes'], total_required_quizzes)
        self.assertEqual(data['total_required_quizzes'], total_required_quizzes)

    def test_partial_course_completion(self):
        # Create a test course with 3 days and 2 quizzes per day (total 6 quizzes)
        course_name = "Test Course"
        days_to_complete = 3
        quizzes_per_day = 2
        total_required_quizzes = days_to_complete * quizzes_per_day

        # Create only 3 completed quizzes (half of required)
        for i in range(3):
            quiz = Quiz(
                questions=[{"question": "Test", "options": ["A", "B", "C", "D"], "correct_answer": 0}],
                course_name=course_name,
                completed=True,
                score=1,
                completed_date=datetime.utcnow()
            )
            db.session.add(quiz)
        db.session.commit()

        # Create user stats
        user_stats = UserStats()
        db.session.add(user_stats)
        db.session.commit()

        # Test partial completion
        response = self.client.post('/api/complete-quiz', json={
            'correct_answers': 1,
            'course_name': course_name,
            'quiz_id': 1,
            'course_details': {
                'daysToComplete': days_to_complete,
                'quizzesPerDay': quizzes_per_day
            }
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify course is not completed yet
        self.assertFalse(data['is_course_completed'])
        self.assertEqual(data['completed_quizzes'], 3)
        self.assertEqual(data['total_required_quizzes'], total_required_quizzes)

if __name__ == '__main__':
    unittest.main() 