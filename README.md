# StudyStreak - AI-Powered Learning Platform
By Avanish Shetty and Vlad Zalutsky

StudyStreak is an innovative learning platform that helps students master their subjects through AI-generated quizzes and personalized learning paths. The platform features a gamified learning experience with streaks, levels, and rewards to keep students motivated.

## Features

* **AI-Powered Quiz Generation**: Create custom courses with AI-generated quizzes based on your study materials
* **Progress Tracking**: Monitor your learning journey with detailed statistics and progress bars
* **Gamification Elements**:  
   * Learning streaks to maintain daily study habits  
   * Level progression system (Novice Learner to Learning Oracle)  
   * Star rewards for completing quizzes  
   * Achievement badges
* **Course Management**:  
   * Create custom courses with flexible parameters  
   * Set daily quiz limits and completion goals  
   * Track progress across multiple courses
* **Interactive UI**:  
   * Modern, responsive design  
   * Dark/Light mode support  
   * Mobile-friendly interface  
   * Real-time feedback on quiz answers

## Tech Stack

* **Backend**: Python, Flask
* **Frontend**: HTML, TailwindCSS
* **Database**: SQLite with SQLAlchemy
* **AI Integration**: OpenAI GPT-3.5
* **Additional Libraries**: python-dotenv, openai

## Setup

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Set up your environment variables in `.env`
5. Run the application: `python app.py`

The application will be available at `http://127.0.0.1:4444`

## Level Progression

1. Novice Learner (Level 1)
2. Knowledge Seeker (Level 2) - 1 quiz
3. Study Enthusiast (Level 3) - 5 quizzes
4. Academic Explorer (Level 4) - 15 quizzes
5. Learning Champion (Level 5) - 25 quizzes
6. Study Master (Level 6) - 40 quizzes
7. Knowledge Guardian (Level 7) - 60 quizzes
8. Academic Legend (Level 8) - 85 quizzes
9. Study Sage (Level 9) - 115 quizzes
10. Learning Oracle (Level 10) - 300 quizzes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

* OpenAI for providing the GPT-3.5 API
* TailwindCSS for the beautiful UI components
* All contributors who have helped shape StudyStreak 
