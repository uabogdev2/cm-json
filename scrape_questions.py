import json
import random
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

def scrape_quiz_page(url):
    """Scrapes a single quiz page for questions and answers."""
    questions = []
    try:
        response = requests.get(url)
        response.raise_for_status()

        print(response.text) # Print the HTML to see if questions are present

        soup = BeautifulSoup(response.content, 'html.parser')

        quiz_questions = soup.find_all('div', class_='question')

        for q in quiz_questions:
            question_text_element = q.find('p', class_='question-p')
            if question_text_element:
                question_text = question_text_element.text.strip()

                explanations = q.find('div', class_='explications')
                if explanations:
                    correct_answer_element = explanations.find('b')
                    if correct_answer_element:
                        answer_text = correct_answer_element.text.strip()
                    else:
                        answer_text = explanations.get_text(strip=True)
                else:
                    answer_text = ""

                numeric_answer = ''.join(filter(str.isdigit, answer_text))

                if numeric_answer:
                    questions.append({
                        "instruction": question_text,
                        "code": numeric_answer
                    })

    except requests.exceptions.RequestException as e:
        print(f"Error scraping {url}: {e}")

    return questions

def get_quiz_urls(category_url, limit=50):
    """Gets a list of quiz URLs from a category page."""
    urls = []
    base_url = "https://www.culturequizz.com"
    try:
        response = requests.get(category_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        quiz_links = soup.select('a[href*="/quiz/"]')

        for link in quiz_links:
            if len(urls) < limit:
                href = link['href']
                full_url = urljoin(base_url, href)
                if full_url not in urls:
                    urls.append(full_url)
            else:
                break

    except requests.exceptions.RequestException as e:
        print(f"Error getting quiz URLs from {category_url}: {e}")

    return urls

def generate_questions_from_scraping(num_questions):
    """Generates a list of questions by scraping culturequizz.com."""
    all_questions = []

    categories = [
        "https://www.culturequizz.com/culture/culture-generale/",
    ]

    quiz_urls = []
    for category_url in categories:
        quiz_urls.extend(get_quiz_urls(category_url, limit=1)) # Just one for now

    quiz_urls = list(set(quiz_urls))

    question_id = 1

    all_questions.append({
        "id": question_id,
        "name": f"Niveau {question_id}",
        "instruction": "J'ai des villes, mais pas de maisons. J'ai des montagnes, mais pas d'arbres. J'ai de l'eau, mais pas de poissons. Que suis-je ? (réponse en nombre de lettres)",
        "code": "5",
        "codeLength": 1,
        "pointsReward": 20,
        "isLocked": False,
        "timeLimit": 30,
        "additionalHints": [
            "Indice 1 : Pensez de manière créative.",
            "Indice 2 : La réponse est le nombre de lettres du mot."
        ],
        "hintCost": 70
    })
    question_id += 1

    for url in quiz_urls:
        if len(all_questions) >= num_questions:
            break

        scraped_questions = scrape_quiz_page(url)
        for q in scraped_questions:
            if len(all_questions) >= num_questions:
                break

            is_locked = question_id != 1
            code_length = len(q["code"])

            if question_id <= 500: # Easy
                points_reward = random.randint(10, 30)
                time_limit = random.randint(20, 40)
                hint_cost = random.randint(50, 80)
            elif question_id <= 1000: # Medium
                points_reward = random.randint(40, 70)
                time_limit = random.randint(30, 50)
                hint_cost = random.randint(90, 130)
            else: # Difficult
                points_reward = random.randint(60, 100)
                time_limit = random.randint(40, 60)
                hint_cost = random.randint(120, 200)

            all_questions.append({
                "id": question_id,
                "name": f"Niveau {question_id}",
                "instruction": q["instruction"],
                "code": q["code"],
                "codeLength": code_length,
                "pointsReward": points_reward,
                "isLocked": is_locked,
                "timeLimit": time_limit,
                "additionalHints": [
                    "Indice 1 : La réponse est un nombre.",
                    f"Indice 2 : Le premier chiffre est {q['code'][0]}."
                ],
                "hintCost": hint_cost
            })
            question_id += 1

    return all_questions

if __name__ == "__main__":
    generated_questions = generate_questions_from_scraping(1500)

    with open('levels.json', 'w', encoding='utf-8') as f:
        json.dump(generated_questions, f, indent=4, ensure_ascii=False)

    print(f"Generated {len(generated_questions)} questions.")
