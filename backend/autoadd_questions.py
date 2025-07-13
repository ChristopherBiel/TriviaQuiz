import random
import boto3
from openai import OpenAI
import os
from db import get_all_questions, add_question

# Initialize AWS Client
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
ssm = boto3.client("ssm", region_name=AWS_REGION)
OPENAI_API_KEY = ssm.get_parameter(Name="/TriviaQuiz/OpenAI_APIkey", WithDecryption=True)["Parameter"]["Value"]

client = OpenAI(api_key=OPENAI_API_KEY)

def sample_questions(n=3):
    """Fetches n random reviewed questions from the database."""
    all_questions = [q for q in get_all_questions() if q.get("review_status") is True]
    # For now we do not use questions with media
    all_questions = [q for q in all_questions if not q.get("media_path")]
    return random.sample(all_questions, min(n, len(all_questions)))

def build_prompt(sampled_questions, n=3):
    """Constructs a prompt for ChatGPT from sampled questions."""
    prompt = """
You are an AI trivia question generator. Below are some examples of trivia questions.
Each question includes a source for the answer. Based on these examples, generate new trivia questions with similar structure and tone, but with completely new content.

Format:
- question: [text]
- answer: [text]
- tags: [list of tags]
- answer source: [weblink]

Examples:
"""
    for q in sampled_questions:
        prompt += f"""
- question: {q['question']}
- answer: {q['answer']}
- tags: {q.get('tags', [])}
- answer source: {q.get('answer_source', '')}
"""
    prompt += f"""
Now generate {n} new trivia questions in the same format:
"""
    return prompt

def generate_new_questions(prompt):
    """Calls OpenAI API to generate new questions."""
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a trivia question generator."},
            {"role": "user", "content": prompt}
        ],
    )
    return completion.choices[0].message.content

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
            answer_source = lines[4].replace("- answer source:", "").strip() if len(lines) > 4 else None

            questions.append({
                "question": question,
                "answer": answer,
                "tags": tags,
                "answer_source": answer_source if answer_source else None
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
            question_source="AI-generated",
            answer_source=q.get("answer_source"),
            review_status=False,
            added_by="ChatGPT",
            question_topic="General",
            language="English",
        )

def generate_and_save_ai_questions(n=3):
    sampled = sample_questions(n)
    print(f"Sampled {len(sampled)} questions for AI generation.")
    prompt = build_prompt(sampled, n)
    print("Prompt for AI generation:")
    print(prompt)
    try:
        generated_text = generate_new_questions(prompt)
    except Exception as e:
        print(f"Error generating questions: {e}")
        return
    print("")
    print("Generated text from AI:")
    print(generated_text)
    parsed = parse_generated_text(generated_text)
    save_generated_questions(parsed)
    print(f"Successfully added {len(parsed)} AI-generated questions.")

if __name__ == "__main__":
    generate_and_save_ai_questions(n=3)
