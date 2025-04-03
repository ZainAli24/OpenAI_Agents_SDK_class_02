import chainlit as cl
from agents import Agent, RunConfig, AsyncOpenAI, OpenAIChatCompletionsModel, Runner
from agents.run import RunConfig
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
from agents import ItemHelpers, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from agents.tool import function_tool
weather_api = os.getenv("WEATHER_API_KEY")
import requests  



@function_tool
def calculate_expression(expression: str) -> str:
  """
    This tool evaluates a mathematical expression.
  """
  try:
    result = eval(expression)
    return f"The result of {expression} is {result}"
  except Exception as e:
    return f"Error in calculation : {str(e)}"

@function_tool("get_weather")
def fetch_weather(city: str):
    """
    This tool fetches the weather for a given city using an API.
    """
    api_key = weather_api
    if not api_key:
        return "Error: Weather API key not found!"

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Agar request fail hoti hai toh error raise hoga
        data = response.json()

        weather_description = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        return f"The weather in {city} is {weather_description} with a temperature of {temperature} °C."
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {str(e)}"


external_client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_API_BASE_URL"),
)

model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=external_client,
)

# config : Defined at Run Level
config = RunConfig(
    model=model,
    model_provider=external_client,
    tracing_disabled=True,
)

agent1 = Agent(
    name="Assistant", 
    # instructions="You are a helpful AI assistant. First, ask the user for their name. If the user's name is 'Zain', proceed to answer their questions by addressing them as 'Zain'. If the user provides any other name, politely decline to answer.",
    instructions="You are a helpful AI assistant. For each query, decide if a tool is needed (e.g., for calculations or weather). If so, call the tool; otherwise, answer directly.",
    model=model,
    tools=[calculate_expression, fetch_weather],
)

# userinput = input('Enter your question: ')
# result = Runner.run_sync(
#     starting_agent=agent1, 
#     input=userinput, 
#     run_config=config
# )

# print("\nCALLING AGENT\n")
# print(result.final_output)

# ----------------------------------------------------------------

# integretion with chainlit:
@cl.on_chat_start
async def start():
    cl.user_session.set("history", [])
    await cl.Message(
        content="Hello! I am your assistant. How can I help you today?"
    ).send()



# # Run with async method:
# @cl.on_message
# async def main(message: cl.Message):
#     history = cl.user_session.get("history")

#     history.append({"role": "user", "content": message.content})

#     result = await Runner.run(   # Runner mien .run method by defualt async hota hai.
#         starting_agent=agent1, 
#         input=history,
#         run_config=config
#     )
#     history.append({"role": "assistant", "content": result.final_output})
#     cl.user_session.set("history", history)
#     await cl.Message(content=result.final_output).send() 

# cl.user_session.set("history", history)
# Jab naya message add ho jata hai (chahe user ka ho ya assistant ka), updated history ko dobara session mein
# set kar diya jata hai. Is se next messages ke liye conversation context barqarar rehta hai.


# ----------------------------------------------------------------


# run with streaming method:
# @cl.on_message
# async def main(message: cl.Message):
#     # Pehle session se conversation history load karain
#     history = cl.user_session.get("history")

#     # User ka message history mein add karain
#     history.append({"role": "user", "content": message.content})
#     msg = cl.Message(content="")
#     await msg.send()

#     # Streamed run call karke assistant se response hasil karain
#     result = Runner.run_streamed(   # Runner mein .run method by default async hota hai.
#         starting_agent=agent1, 
#         input=history,
#         run_config=config
#     )
#     async for event in result.stream_events():
#         if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
#                 await msg.stream_token(event.data.delta)

#     msg.content = result.final_output
#     await msg.update()


#     history.append({"role": "assistant", "content": result.final_output})
#     cl.user_session.set("history", history)


# ----------------------------------------------------------------
# run with streaming method + function tools:
@cl.on_message
async def main(message: cl.Message):
    # Pehle session se conversation history load karain
    history = cl.user_session.get("history")

    # User ka message history mein add karain
    history.append({"role": "user", "content": message.content})
    msg = cl.Message(content="")
    await msg.send()

    # Streamed run call karke assistant se response hasil karain
    result = Runner.run_streamed(   # Runner mein .run method by default async hota hai.
        starting_agent=agent1, 
        input=history,
        run_config=config
    )
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                await msg.stream_token(event.data.delta)

    msg.content = result.final_output
    await msg.update()


    history.append({"role": "assistant", "content": result.final_output})
    cl.user_session.set("history", history)
