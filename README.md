![Deployment to EC2](https://github.com/ChristopherBiel/TriviaQuiz/actions/workflows/deploy.yml/badge.svg)




New File structure:

TriviaQuiz/
│
├── backend/
│   ├── api/                    # FastAPI/Flask route definitions (organized by domain)
│   │   ├── __init__.py
│   │   ├── questions.py
│   │   ├── events.py
│   │   ├── multiplayer.py
│   │   └── media.py
│   │
│   ├── services/              # Business logic layer
│   │   ├── __init__.py
│   │   ├── question_service.py
│   │   ├── event_service.py
│   │   ├── user_service.py
│   │   └── multiplayer_service.py
│   │
│   ├── models/                # Data models & schemas (Pydantic / Marshmallow)
│   │   ├── __init__.py
│   │   ├── question.py
│   │   ├── event.py
│   │   ├── user.py
│   │   └── media.py
│   │
│   ├── db/                    # Database interface (DynamoDB/S3 utils)
│   │   ├── __init__.py
│   │   ├── dynamodb.py
│   │   ├── s3.py
│   │   └── utils.py
│   │
│   ├── core/                  # Configuration, constants, logging
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── settings.py
│   │
│   └── main.py                # Entry point for backend (e.g., FastAPI app)
│
├── frontend/                  # Web frontend (e.g., React, Vue)
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/               # Calls to backend API
│   │   ├── styles/
│   │   └── App.js
│   └── package.json
│
├── tests/                     # Unit and integration tests
│   ├── api/
│   ├── services/
│   ├── db/
│   └── conftest.py
│
├── scripts/                   # One-off scripts, seeders, migrations, etc.
│   ├── seed_data.py
│   └── setup_dynamodb.py
│
├── docker/                    # Docker-related config
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── .github/                   # GitHub Actions, workflows
│   └── workflows/
│
├── requirements.txt
├── README.md
└── .env                       # Environment variables













# TriviaQuiz
Hosts a webpage which serves trivia questions from a database.
The webservice is aimed at being deployed on an AWS EC2 instance with a dynamoDB and S3 backend.

## Getting started
Setup a dynamoDB table, S3 bucket and EC2 instance.


Running `app.py`

# Functionality

## Database Handling

The project utilizes AWS DynamoDB and Amazon S3 to store and manage trivia questions efficiently. Below is an overview of how the database operations are handled.

### DynamoDB (TriviaQuestions Table)
The trivia questions are stored in a DynamoDB table named `TriviaQuestions`. Each question is stored as an item with the following attributes:

- **id** (String, Primary Key): A unique identifier generated using `uuid.uuid4()`.
- **question** (String): The trivia question.
- **answer** (String): The correct answer to the question.
- **added_by** (String): The user who added the question.
- **question_topic** (String, Optional): The category or topic of the question.
- **question_source** (String, Optional): The source from which the question was obtained.
- **answer_source** (String, Optional): The source of the answer.
- **media_path** (String, Optional): A reference to an associated media file stored in S3.
- **language** (String, Optional): The language of the question.
- **incorrect_answers** (List, Optional): A list of incorrect answers for multiple-choice questions.
- **tags** (List, Optional): Tags related to the question.
- **timestamp** (String): The timestamp when the question was added.

### Amazon S3 (Media Storage)
If a question includes an associated media file (image, audio, or video), it is uploaded to an S3 bucket. The following process is followed:

1. The media file is uploaded to the S3 bucket specified in the `AWS_S3_BUCKET` environment variable.
2. The function `upload_file_to_s3(media_file)` handles the file upload and generates a public or private URL.
3. The generated S3 URL is stored in the `media_path` attribute in DynamoDB.

### Adding a Question
To add a new trivia question, the `add_question()` function is used. It follows these steps:
1. Generates a unique `id`.
2. Uploads the media file to S3 (if provided) and retrieves its URL.
3. Constructs an item with all attributes.
4. Saves the item in the `TriviaQuestions` table using DynamoDB.

### Retrieving Questions
Questions can be retrieved using their `id` via DynamoDB queries. Additionally, filters can be applied based on topics, tags, or languages.

This structure ensures scalable and efficient management of trivia questions while allowing the integration of multimedia content stored securely in S3.

