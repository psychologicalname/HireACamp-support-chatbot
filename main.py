from textbase import bot, Message
from typing import List
import openai
import json
from urllib.request import urlopen
import os

openai.api_type = "azure"
openai.api_base = os.environ.get('API_BASE')
openai.api_version = "2023-08-01-preview"
openai.api_key = os.environ.get('API_KEY')
#openai.api_key = "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"

f = open('data.json')
data = json.load(f)
f.close()

# Example dummy function hard coded to return the same weather
# In production, this could be your backend API or an external API
def get_cities_in_state(location):
    response = urlopen("https://www.hireacamp.com/api/external/ai/search?limit=10&params=%7B%22filter%22:[%22type=city%22,%22state="+location+"%22],%22sort%22:[%22_count:desc%22],%22attributesToRetrieve%22:%20[%22name%22,%22uname%22,%22price%22,%22state%22]%7D")
    cities = json.loads(response.read())
    print(cities)
    return json.dumps(cities)
def top_stays(location):
    response = urlopen("https://www.hireacamp.com/api/external/ai/search?limit=10&params=%7B%22filter%22:[%22type=package%22],%22sort%22:[%22_count:desc%22],%22attributesToRetrieve%22:%20[%22fancyname%22,%22uname%22,%22price%22,%22city%22,%22state%22]%7D")
    stays = json.loads(response.read())
    return json.dumps(stays)

# Return list of values of content.
def get_contents(message: Message, data_type: str):
    return [
        {
            "role": message["role"],
            "content": content["value"]
        }
        for content in message["content"]
        if content["data_type"] == data_type
    ]

def run_conversation(message_history: list[Message]):
    # Step 1: send the conversation and available functions to GPT
    messages = data
    functions = [
        {
            "name": "get_cities_in_state",
            "description": "Get cities in a state",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The state in India, e.g. Maharashtra",
                    },
                },
                "required": ["location"],
            },
        },
        {
            "name": "top_stays",
            "description": "Top Stays on Hire A Camp. The uname key is used to generate url eg: https://www.hireacamp.com/[value of uname key]",
            "parameters": {
                 "type": "object",
                "properties": {
                }
            }
        }
    ]

    filtered_messages = []
    for message in message_history:
            #list of all the contents inside a single message
            contents = get_contents(message, "STRING")
            if contents:
                filtered_messages.extend(contents)

    response = openai.ChatCompletion.create(
        engine="hirey",
        messages=[*data,
                  *map(dict, filtered_messages)
        ],
        functions=functions,
        function_call="auto",
    )
    response_message = response["choices"][0]["message"]


        # Step 2: check if GPT wanted to call a function
    if response_message.get("function_call"):
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "get_cities_in_state": get_cities_in_state,
            "top_stays": top_stays
        }  # only one function in this example, but you can have multiple
        function_name = response_message["function_call"]["name"]
        fuction_to_call = available_functions[function_name]
        function_args = json.loads(response_message["function_call"]["arguments"])
        function_response = fuction_to_call(
            location=function_args.get("location"),
        )

        # Step 4: send the info on the function call and function response to GPT
        #messages.append(response_message)  # extend conversation with assistant's reply
        messages.append(
            {
                "role": "function",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response
        print(messages)
        second_response = openai.ChatCompletion.create(
            engine="hirey",
            messages=messages,
        )  # get a new response from GPT where it can see the function response

        return second_response["choices"][0]["message"]
    else:
         return response_message
@bot()
def on_message(message_history: List[Message], state: dict = None):
    # Mimic user's response
    bot_response = run_conversation(message_history)

    response = {
        "data": {
            "messages": [
                {
                    "data_type": "STRING",
                    "value": bot_response["content"]
                }
            ],
            "state": state
        },
        "errors": [
            {
                "message": bot_response
            }
        ]
    }

    return {
        "status_code": 200,
        "response": response
    }