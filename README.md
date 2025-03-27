# AI Study App

An intelligent study assistant that helps you learn more effectively. Upload your study materials, and the app will generate quizzes to test your knowledge using AI.

## Features

- Upload study materials (supports .txt, .pdf, and .docx files)
- AI-powered quiz generation based on your study materials
- Track your learning progress
- Simple and intuitive user interface

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd ai-study-app
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your OpenAI API key:
Create a `.env` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

5. Run the application:
```bash
python app.py
```

The application will be available at `http://127.0.0.1:4444`

## Usage

1. Upload your study materials using the upload button
2. Click "Generate Quiz" to create a quiz based on your materials
3. Answer the questions and track your progress

## Technologies Used

- Flask
- SQLAlchemy
- OpenAI GPT-4
- Python-docx
- SQLite 