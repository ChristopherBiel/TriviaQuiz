import random
import boto3
import openai
import os
from db import get_all_questions, add_question

# Initialize AWS Client
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
ssm = boto3.client("ssm", region_name=AWS_REGION)
OPENAI_API_KEY = ssm.get_parameter(Name="/TriviaQuiz/OpenAI_APIkey", WithDecryption=True)["Parameter"]["Value"]

openai.api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)

def sample_questions(n=3):
    """Fetches n random reviewed questions from the database."""
    all_questions = [q for q in get_all_questions() if q.get("review_status") is True]
    return random.sample(all_questions, min(n, len(all_questions)))

def build_prompt(sampled_questions):
    """Constructs a prompt for ChatGPT from sampled questions."""
    prompt = """
You are an AI trivia question generator. Below are some examples of trivia questions.
Each question includes optional media references. Based on these examples, generate new trivia questions with similar structure and tone, but with completely new content.

Format:
- question: [text]
- answer: [text]
- tags: [list of tags]
- media_reference: [optional description or leave blank]

Examples:
"""
    for q in sampled_questions:
        prompt += f"""
- question: {q['question']}
- answer: {q['answer']}
- tags: {q.get('tags', [])}
- media_reference: {q.get('media_path', '')}
"""
    prompt += """
Now generate 3 new trivia questions in the same format:
"""
    return prompt

def generate_new_questions(prompt):
    """Calls OpenAI API to generate new questions."""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a trivia question generator."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=1000,
    )
    return response.choices[0].message.content

def parse_generated_text(text):
    """Parses the raw text from ChatGPT into structured question dictionaries."""
    questions = []
    chunks = text.strip().split("- question:")
    for chunk in chunks[1:]:
        lines = chunk.strip().split("\n")
        try:
            question = lines[0].strip()
            answer = lines[1].replace("- answer:", "").strip()
            tags = eval(lines[3].replace("- tags:", "").strip())
            media = lines[4].replace("- media_reference:", "").strip() if len(lines) > 4 else None

            questions.append({
                "question": question,
                "answer": answer,
                "tags": tags,
                "media_path": media if media else None
            })
        except Exception as e:
            print(f"Skipping malformed entry: {e}")
    return questions

def save_generated_questions(parsed_questions):
    """Saves generated questions to the DB with review_status=False and added_by='ChatGPT'."""
    for q in parsed_questions:
        add_question(
            question=q["question"],
            answer=q["answer"],
            tags=q.get("tags"),
            media_file=None,  # Handle real media processing separately if needed
            review_status=False,
            added_by="ChatGPT",
            question_topic="General"
        )

def generate_and_save_ai_questions(n=3):
    sampled = sample_questions(n)
    prompt = build_prompt(sampled)
    generated_text = generate_new_questions(prompt)
    parsed = parse_generated_text(generated_text)
    save_generated_questions(parsed)
    print(f"Successfully added {len(parsed)} AI-generated questions.")

if __name__ == "__main__":
    generate_and_save_ai_questions(n=3)
