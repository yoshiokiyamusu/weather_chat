import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from agent import agent
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

@app.route('/')
def home():
    session['thread_id'] = str(uuid.uuid4())  # Generate a unique thread ID for each session
    if 'messages' not in session:
        session['messages'] = []
    return render_template('chat.html', messages=session['messages'])

@app.route('/send', methods=['POST'])
def send():
    user_message = request.form['message']
    user_lat = request.form.get('latitude')
    user_lon = request.form.get('longitude')
    print(user_lat, user_lon)

    if user_lat and user_lon:
        session['user_location'] = {'lat': user_lat, 'lon': user_lon}

    response1 = agent.invoke({"messages": [{"role": "user", "content": user_message}]},{"configurable": {"thread_id": session['thread_id']}})
    
    ai_response = response1['messages'][-1].content
    print(f"Thread: {session['thread_id']}")
    print(f"User message: {user_message}")
    print(f"AI: {ai_response}")
    #print(response1)

    # Check if 'messages' exists, if not, create it
    if 'messages' not in session:
        session['messages'] = []
    session['messages'].append({"type": "human", "content": user_message})
    session['messages'].append({"type": "ai", "content": ai_response})
    session.modified = True
    return redirect(url_for('home'))

@app.route('/clear')
def clear_session():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    # CHANGE 2: Read Render's assigned port dynamically
    # app.run(debug=True, port=8180, use_reloader=False) #This is only for localhost testing
    port = int(os.getenv("PORT", 8180))
    app.run(host="0.0.0.0", port=port)
    