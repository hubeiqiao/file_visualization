from openai import OpenAI

# Initialize the client with your API key
client = OpenAI(api_key='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')

def get_response(question):
    try:
        # Create a chat completion request using the new API
        response = client.chat.completions.create(
            model="gpt-4.5-preview-2025-02-27",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ],
            max_tokens=15000,
            temperature=0.7
        )
        
        # Extract and return the response
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"An error occurred: {str(e)}"

def chat():
    print("Welcome to the Q&A Chat!")
    print("Type 'quit' to exit the chat.")
    
    while True:
        # Get user's question
        question = input("\nYour question: ")
        
        # Check if user wants to quit
        if question.lower() == 'quit':
            print("Goodbye!")
            break
        
        # Get and display the response
        response = get_response(question)
        print("Answer:", response)

# Run the chat
if __name__ == "__main__":
    chat()