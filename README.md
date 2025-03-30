![Deployment to EC2](https://github.com/ChristopherBiel/TriviaQuiz/actions/workflows/deploy.yml/badge.svg)

# TriviaQuiz
Hosts a webpage which serves trivia questions from a database.
The webservice is aimed at being deployed on an AWS EC2 instance with a dynamoDB and S3 backend.

## Getting started
Create a sqlite3 database called `trivia.db` of the form:

> Good question, how is it actually defined? Can I also change thhe definition latern?

Running `app.py`

## Definition of the database structure (sqlite3)
| Column Name | Data Type | Column Constraint | Description |
| ----------- | ----------- | ----------- | ----------- |
| id | integer | primary key autoincrement | unique question id, does not have to be provided when adding an entry to the database |
| question | text | not null | required question text, usually ending in a question mark |
| answer | text | not null | required question answer |
| media_path | text | null | optional path of the stored media file, path is defined as relative to the static/uploads/ folder |
| added_by | text | not null | name of the user who added the question to the database (automatically added by the backend) |
| added_at | date? | not null | date of addition to the database (automatically added by the backend) |
| question_topic | text | null | optional topic for the question, if not null it will only show up when the topic is selected in the main page. To be used for speciality questions which would not be part of a standard trivia round e.g. 'League' for in depth questions about the game |
| question_source | text | null | optional source for the question, e.g. 'Pubquiz Towers, 04.02.25' |
| answer_source | text | null | optional source for the answer, e.g. a wikipedia article which provides more information |
| expiration_date | date? | null | optional date of expiration, for questions which have changing answers, e.g. current F1 champion |
| incorrect_answer | set of? text | null | optional incorrect answers for multiple choice questions |
| times_asked | integer | not null | number of times the question was presented to users |
| times_correctly_answered | integer | not null | number of times the question was correctly answered in a special quiz mode |
| times_incorrectly_answered | integer | not null | number of times the question was incorrectly answered in a special quiz mode |
| last_updated_at | date? | not null | timestamp of the most recent modification to the question |
| language | text | null | specifies the language of the question | 
| review status | boolean | not null | indicates if the question has been peer-reviewed or verified |
| tags | set of? text | null | keyword associated with the question for improved searchability |