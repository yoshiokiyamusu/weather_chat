import os
from dotenv import load_dotenv
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain.agents import create_agent
import requests
#from langgraph.checkpoint.memory import InMemorySaver
#from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

load_dotenv()

# Define the path to your .env file
# We go up two levels from the current script's directory
# env_path = Path(__file__).resolve().parent.parent / '.env'
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path) # Load the specific .env file
else:
    load_dotenv() # for Render's environment variables settings



gemini_key=os.getenv('GOOGLE_GEMINI_KEY')
DB_URL=os.getenv('SUPABASE_DB_URL')

def get_weather(city: str):
    """Get weather for a given city
    Return the temperature_fahrenheit value in Fahrenheit label for locations such as US, Liberia, Burma"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q":city,
        "appid":api_key,
        'units': 'metric'
    }
    response = requests.get(base_url, params=params)
    data = response.json()
    temperature_celsius = data['main']['temp']
    temperature_fahrenheit = temperature_celsius * 9/5 + 32
    return data, {'temperature_fahrenheit': temperature_fahrenheit}

def get_location():
    """Get user's current location. Use this when the user asks about weather."""
    from flask import session
    lat = session['user_location']['lat']
    lon = session['user_location']['lon']

    response = requests.get(
        f'https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json',
        headers={'User-Agent': 'WeatherAssistant/1.0'},
        timeout=3
    )
    
    data = response.json()
    print(data)
    
    # Extract city (checking for 'city' or 'town' as fallbacks)
    city = data['address'].get('city', data['address'].get('town', 'Unknown'))
    country = data['address'].get('country', '')
    
    return f"{city}, {country}"

   


system_prompt = """
You are a helpful weather assistant. 
YOUR WORKFLOW:
1. If the user asks about weather WITHOUT specifying a location, you MUST:
   - First call get_location() to find their location
   - Then call get_weather(city) with that location
   
2. If the user provides a city, call get_weather(city) directly.

3. Use your knowledge to determine which temperature unit is standard for the given location.

4. Present the weather information including temperature, condition, wind speed, and any other relevant details.

"""
# Initialize the LLM. Gemini Flash 2.5
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite", #gemini-2.5-flash-lite #gemini-2.5-flash #gemini-3.1-flash #gemini-2.5-flash-image
    google_api_key=gemini_key,
    temperature=0.7,
)

# Establish the connection
# Note: We don't use 'with' here because we want the connection 
# to stay alive for the lifetime of the Flask app.

# 1. Create a connection pool manually. 
# This allows us to pass 'prepare_threshold' directly to the driver.
pool = ConnectionPool(
    conninfo=DB_URL, 
    max_size=10, 
    kwargs={"prepare_threshold": None}
)

# 2. Pass the pool to PostgresSaver instead of the connection string
checkpointerdb = PostgresSaver(pool)

try:
    checkpointerdb.setup() # Create the necessary tables if they don't exist
except Exception as e:
    # If it fails because it's already set up or a duplicate, just keep going
    print(f"Setup skipped: {e}")

# Create the agent
agent = create_agent(
    model=llm,
    tools=[get_weather, get_location],
    system_prompt=system_prompt,
    checkpointer=checkpointerdb
)

