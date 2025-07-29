#!/usr/bin/env python3
"""
Test script for survey-based questions in the chatbot.
"""

from app.integrated import get_groq_response

def test_survey_questions():
    """Test all the survey-based questions."""
    
    test_questions = [
        "Do people in zip code 78201 like public transportation?",
        "Are people in zip code 78201 satisfied with their public transit",
        "Are there opportunities for investment in San Antonio?",
        "What do most citizens in zip code 78201 use for their mode of transportation?",
        "What do most people in San Antonio want to see improved for transportation?",
        "What public services or resources do people in zip code 78201 lack?",
        "Do San Antonians like the city?",
        "Is San Antonio cool?",
        "How accessible are public community spaces in San Antonio?",
        "How accessible are public community spaces in zip code 78201?",
        "How affordable is housing in San Antonio?",
        "How affordable is housing in zip code 78201?",
        "What type of housing do San Antonio?",
        "Do most people live by themselves or with others?"
    ]
    
    print("Testing survey-based questions...")
    print("=" * 50)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Testing: {question}")
        try:
            result = get_groq_response(question)
            response = result[0] if isinstance(result, tuple) else result
            print(f"   ✓ Success! Response length: {len(response)} characters")
            print(f"   Preview: {response[:100]}...")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Survey question testing completed!")

if __name__ == "__main__":
    test_survey_questions() 