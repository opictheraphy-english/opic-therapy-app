import random


def generate_test_set(survey_results=None, difficulty=5):
    test_set = [{"id": 1, "type": "Intro", "question": "Let's start the interview now. Tell me a little bit about yourself."}]

    survey_topics = ["Housing", "Movie", "Park", "Jogging"]
    random_topics = ["Recycling", "Furniture", "Technology"]

    selected_survey_topics = []
    if survey_results:
        for key in ("leisure", "interests", "sports", "travel", "hobbies"):
            values = survey_results.get(key, [])
            if isinstance(values, list):
                selected_survey_topics.extend(values)

    # Remove duplicates while keeping original order.
    selected_survey_topics = list(dict.fromkeys(selected_survey_topics))
    first_survey_topic = random.choice(selected_survey_topics) if selected_survey_topics else random.choice(survey_topics)

    second_pool = [topic for topic in (selected_survey_topics + survey_topics) if topic != first_survey_topic]
    second_survey_topic = random.choice(second_pool) if second_pool else first_survey_topic

    topics = [("Survey", first_survey_topic),
              ("Random", random.choice(random_topics)),
              ("Survey", second_survey_topic)]
    random.shuffle(topics)

    for t_cat, t_name in topics:
        test_set.append({"id": len(test_set)+1, "type": t_cat, "topic": t_name, "step": "Description", "question": f"I'd like to know about your [{t_name}]. Describe it in detail."})
        test_set.append({"id": len(test_set)+1, "type": t_cat, "topic": t_name, "step": "Routine", "question": f"Tell me about your typical routine regarding [{t_name}]. What do you usually do?"})
        test_set.append({"id": len(test_set)+1, "type": t_cat, "topic": t_name, "step": "Experience", "question": f"Talk about a memorable experience you had related to [{t_name}]."})

    # Roleplay & Advanced (영어로 교체)
    test_set.append({"id": 11, "type": "Roleplay", "step": "Question", "question": "You want to buy new furniture. Ask the clerk 3-4 questions about it."})
    test_set.append({"id": 12, "type": "Roleplay", "step": "Problem Solving", "question": "There is a problem with the furniture delivered. Call the store, explain the situation, and offer solutions."})
    test_set.append({"id": 13, "type": "Roleplay", "step": "Experience", "question": "Have you ever had a problem when purchasing something in real life?"})

    advanced_level5 = [
        "Compare the homes from your childhood to the homes today. How have they changed?",
        "Compare living alone and living with family. Which do you prefer and why?",
        "Compare apartments and houses in terms of convenience and lifestyle.",
        "Compare city life and suburban life based on your experience.",
    ]
    advanced_level6 = [
        "Compare rental housing and home ownership, focusing on long-term stability, cost, and personal freedom.",
        "Discuss the social impact of rising housing prices. Who is most affected and why?",
        "Compare remote work trends and housing demand. How has remote work changed where people live?",
        "Discuss whether governments should intervene in housing markets. Provide two reasons and one counterargument.",
        "Compare urban redevelopment and community preservation. Which should be prioritized and why?",
    ]

    advanced_pool = advanced_level6 if int(difficulty) == 6 else advanced_level5
    q14 = random.choice(advanced_pool)
    q15_pool = [q for q in advanced_pool if q != q14] or advanced_pool
    q15 = random.choice(q15_pool)

    test_set.append({"id": 14, "type": "Advanced", "step": "Comparison/Issue", "question": q14})
    test_set.append({"id": 15, "type": "Advanced", "step": "Comparison/Issue", "question": q15})

    return test_set
