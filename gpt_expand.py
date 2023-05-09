'''
It may be possible to use OpenAI's models to help us expand the case titles
It it a rather difficult linguistic task and got may be able to handle it well

Maverick Reynolds
04.19.2023
UCF Crimes
'''

from configparser import ConfigParser
import openai
import json

main_config = ConfigParser()
main_config.read('config.ini')

# Prompt engineering for the model
# It seems to work pretty well even without the examples so that will be an option for us
def generate_prompt(title: str, provide_examples=True):
    with open('gpt_expansions.json') as f:
        previous_responses = json.load(f)

    # Start with instruction
    prompt = 'Here is some text from a case notification system that has some abbreviations. Can you expand the text and include prepositions while still keeping it uppercase?'
    prompt += '\n\n'

    # List previous_examples
    if provide_examples:
        for resp in previous_responses:
            if resp['verified_example']:
                prompt += f"Example: {resp['raw']}\nAnswer: {resp['expanded']}\n\n"
    
        prompt += 'Example: '
    
    # Give current message
    prompt += title.upper() # Just in case

    # Continue formatting if examples are listed
    if provide_examples:
        prompt += '\nAnswer:'

    return prompt.strip()   # Beneficial to start and end without leading/trailing spaces



# Use model to expand the titles of cases
def gpt_title_expand(formatted_title, provide_examples=True):
    API_KEY = main_config.get("DISCORD", "OPENAI_KEY")
    openai.api_key=API_KEY
    model='gpt-3.5-turbo' # Because this is way cheaper!

    # Build the prompt using verified examples and the title
    prompt = generate_prompt(formatted_title, provide_examples=provide_examples)

    messages=[{'role': 'user', 'content': prompt}]
    response = openai.ChatCompletion.create(model=model, messages=messages)

    return response['choices'][0]['message']['content'].strip('.') # Remove period if generated