import re
from groq import Groq
from app.config import Config
import os

client = Groq(api_key=Config.get_groq_api_keys()[0])


system_prompt = "You are helpful assistant that answers users question based on data fetched from vector database. You will get best fitting chunks for question, and your job is to answer user question as best as you can with data you got from vector database."
def construct_prompt(data_from_vdb, question):
    template_question = f"""
    Here is data from vector database:

    {data_from_vdb}

    And here is user question: {question}
    Answer this question based on vector database and if you have your knowledge about topic you can use it but only if data from vector database is not enough.
    But if you use your knowlage, please tell it to user that data from vector database was not enough. DO NOT HALLUCINATE if you don't have information about topic.
    """
    return template_question


def construct_messages(data_from_vdb, question):
    template_question = construct_prompt(data_from_vdb, question)
    try:
        
        print(f"Question: {question}")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{template_question}"},
        ]
        
        return messages
    except Exception as ex:
        print(f"Error in ask_question: {ex}")
        return "Sorry, something went wrong while processing your request."
    

def send_to_groq(data_from_vdb, question):
    """Send a list of messages to the Groq API and return the response, prompt tokens, completion tokens, and total tokens."""
    
    #fetch messages
    messages = construct_messages(data_from_vdb, question)
    
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct", 
        messages=messages
    )
    answer = completion.choices[0].message.content
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    total_tokens = completion.usage.total_tokens
    
    
    return answer, prompt_tokens, completion_tokens, total_tokens