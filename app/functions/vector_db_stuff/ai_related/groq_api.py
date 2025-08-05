import time
import logging
import json
import os
from datetime import datetime
from groq import Groq
from app.config import Config

api_keys = Config.get_groq_api_keys()
current_key_index = 0
client = Groq(api_key=api_keys[current_key_index])

logger = logging.getLogger(__name__)
token_count = 0
start_time = None

def reset_token_count():
    global token_count, start_time
    token_count = 0
    start_time = None

def rotate_api_key():
    global current_key_index, client
    # Only rotate if we have multiple keys
    if len(api_keys) > 1:
        current_key_index = (current_key_index + 1) % len(api_keys)
        client = Groq(api_key=api_keys[current_key_index])
        logger.debug(f"Rotated API key to: {current_key_index}")
    else:
        logger.debug("Only one API key available, skipping rotation")

def log_groq_interaction(messages, response, prompt_tokens, completion_tokens, total_tokens, model_name, reasoning_effort=None):
    """Log the complete interaction with Groq API to a structured log file"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "reasoning_effort": reasoning_effort,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "messages": messages,
        "response": response
    }
    
    # Ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file path with date
    log_file = os.path.join(log_dir, f"groq_interactions_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    # Append to log file
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + '\n' + '='*80 + '\n')

def send_to_groq(messages, use_reasoning=True, reasoning_effort="medium"):
    """Send a list of messages to the Groq API using GPT-OSS-120B with reasoning and return the response, prompt tokens, completion tokens, and total tokens."""
    global token_count, start_time

    # If this is the first request, set the start time
    if start_time is None:
        start_time = time.time()

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    if elapsed_time > 60:
        reset_token_count()
        start_time = time.time()

    if token_count >= 6000:
        rotate_api_key()
        reset_token_count()
        start_time = time.time()

    # Prepare completion parameters - simplified to match working example
    completion_params = {
        "model": "openai/gpt-oss-120b",
        "messages": messages,
        "temperature": 1
    }
    
    # Add reasoning effort if requested
    if use_reasoning:
        completion_params["reasoning_effort"] = reasoning_effort
    
    completion = client.chat.completions.create(**completion_params)
    
    answer = completion.choices[0].message.content
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    total_tokens = completion.usage.total_tokens
    
    token_count += total_tokens
    logger.info(f"Total tokens in rotation: {token_count}")
    
    # Log the interaction
    log_groq_interaction(
        messages=messages,
        response=answer,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model_name="openai/gpt-oss-120b",
        reasoning_effort=reasoning_effort if use_reasoning else None
    )
    
    return answer, prompt_tokens, completion_tokens, total_tokens


async def send_to_groq_vision(question, image_url):
    """Send question with picture, return the response, prompt tokens, completion tokens, and total tokens."""
    global token_count, start_time

    # If this is the first request, set the start time
    if start_time is None:
        start_time = time.time()

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    if elapsed_time > 60:
        reset_token_count()
        start_time = time.time()

    if token_count >= 6000:
        rotate_api_key()
        reset_token_count()
        start_time = time.time()
    print(f"Image URL in send to groq funciuons: {image_url}")
    
    completion = client.chat.completions.create(
        #model="llama3-70b-8192", 
        model="meta-llama/llama-4-maverick-17b-128e-instruct", 
        messages=[
            # this groq says tdont work now {"role": "system", "content": "You are Ai-Chan, the mascot of the Bakakats Discord server. You are a prankster who occasionally jokes around instead of helping. You love to troll everyone in the server, making jokes on expense of others and pinging users."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
    )
    answer = completion.choices[0].message.content
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    total_tokens = completion.usage.total_tokens
    
    token_count += total_tokens
    logger.info(f"Total tokens in rotation: {token_count}")   
    return answer, prompt_tokens, completion_tokens, total_tokens
