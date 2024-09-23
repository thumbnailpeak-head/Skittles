import openai

# Set OpenAI API key
openai.api_key = 'api-key-here'


# Call ChatGPT to get response given prompt
def chat_with_gpt4(prompt: str) -> str:
    try:
        # Call the OpenAI GPT-4 API
        response = openai.Completion.create(
            engine="gpt-4",  # Use the GPT-4 model
            prompt=prompt,
            max_tokens=200,  # Adjust max tokens for the response
            n=1,
            stop=None,
            temperature=0.7  # Adjust the temperature for more or less randomness
        )

        # Extract the response from the API
        gpt_response = response.choices[0].text.strip()
        return gpt_response
    except Exception as e:
        return f"Error: {str(e)}"
