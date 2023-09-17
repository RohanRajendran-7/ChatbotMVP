from flask import Flask, render_template, request, redirect, url_for, session
from flask_ngrok import run_with_ngrok
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random
from langchain.chains import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.callbacks import get_openai_callback
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from pdf_processor import process_file
import threading
app = Flask(__name__)
app.secret_key = 'super secret key'
# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatlog.db'
db = SQLAlchemy(app)
run_with_ngrok(app)


template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, please think rationally answer from your own knowledge base 
{context}
Question: {question}
"""
QA_CHAIN_PROMPT = PromptTemplate.from_template(template)


bg_file_path = "D:/stridec/langchain/BreadGarden.pdf"
bg_vectorstore = process_file(bg_file_path)
print(bg_vectorstore, "hello")

class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_message = db.Column(db.String(255))
    bot_response = db.Column(db.String(255))
    username = db.Column(db.String(255))  

#openAI query
# def bgquery(user_query):
#     if user_query:
#         print("in")
#         llm = OpenAI(temperature=0.5)
#         docs = bg_vectorstore.similarity_search(query=user_query, k=3)
#         print(docs)
#         qa_chain = RetrievalQA.from_chain_type(
#             llm,
#             chain_type='stuff',
#             retriever=bg_vectorstore.as_retriever(),
#             chain_type_kwargs={"prompt": QA_CHAIN_PROMPT,"memory": ConversationBufferMemory(
#             memory_key="history",
#             input_key="question"),}
#         )

#         # print(docs)
#         chain_bg = load_qa_chain(llm=llm, chain_type="stuff")
#         # chain_bg = qa_chain
#         with get_openai_callback() as cb:
#             response = chain_bg.run(input_documents=docs, question=user_query)
#             result = qa_chain({"query": user_query})
#             print(result,cb,response)
#         return response

running_queries = {}

# Lock to synchronize access to the running_queries dictionary
running_queries_lock = threading.Lock()

#openAI query
def bgquery(user_query, username):
    if user_query:
        print("in")
        llm = OpenAI(temperature=0.5)
        docs = bg_vectorstore.similarity_search(query=user_query, k=3)
        print(docs)
        qa_chain = RetrievalQA.from_chain_type(
            llm,
            chain_type='stuff',
            retriever=bg_vectorstore.as_retriever(),
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT,"memory": ConversationBufferMemory(
            memory_key="history",
            input_key="question"),}
        )

        # print(docs)
        chain_bg = load_qa_chain(llm=llm, chain_type="stuff")
        # chain_bg = qa_chain
        with get_openai_callback() as cb:
            response = chain_bg.run(input_documents=docs, question=user_query)
            result = qa_chain({"query": user_query})
            print(result,cb,response)
        
        # Check if the query should be stopped
        with running_queries_lock:
            if username in running_queries and running_queries[username]:
                print(f"Query for {username} should be stopped.")
                return None
        
        return response

def toggle_query(username):
    # Set the flag to stop the query for the specified user
    with running_queries_lock:
        running_queries[username] = False

def simple_chatbot(user_message):
    user_message = user_message.lower()
    response = bgquery(user_message)
    return response

@app.before_request
def before_request():
    db.create_all()

@app.route('/')
def home():
    # Check if it's the user's first interaction (no username in session)
    if 'username' not in session:
        return render_template('get_username.html')

    return render_template('index.html', username=session['username'])

@app.route('/set_username', methods=['POST'])
def set_username():
    # Get the username from the form
    username = request.form['username']
    
    # Store the username in the session
    session['username'] = username
    
    return redirect(url_for('home'))

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.form['user_message']
    
    # Check if it's the user's first interaction (no username in session)
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session['username']
    
    # Start the query for this user
    with running_queries_lock:
        running_queries[username] = True
    
    bot_response = bgquery(user_message, username)
    
    # Stop the query for this user
    toggle_query(username)
    
    if bot_response is None:
        bot_response = "Query stopped by user request."
    
    chatlog = ChatLog(user_message=user_message, bot_response=bot_response, username=username)
    db.session.add(chatlog)
    db.session.commit()

    return bot_response

@app.route('/chat_history')
def chat_history():
    # Check if the user is logged in (has a username in session)
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session['username']

    # Query the database for chat history associated with the user's username
    chat_history = ChatLog.query.filter_by(username=username).all()

    return render_template('chat_history.html', chat_history=chat_history)

# @app.route('/admin/conversations')
# def view_conversations():
#     conversations = ChatLog.query.all()
#     return render_template('admin/conversations.html', conversations=conversations)

@app.route('/admin/conversations')
def admin_conversations():
    # Query the database to get distinct usernames
    distinct_usernames = db.session.query(ChatLog.username).distinct().all()
    conversations = ChatLog.query.all()
    usernames = [row[0] for row in distinct_usernames]

    return render_template('admin/conversations.html', usernames=usernames, conversations=conversations)

@app.route('/admin/conversations/<username>')
def user_conversations(username):
    # Query the database for conversations associated with the selected username
    conversations = ChatLog.query.filter_by(username=username).all()
    
    return render_template('admin/user_conversations.html', username=username, conversations=conversations)

@app.route('/admin/reply/<int:conversation_id>', methods=['POST'])
def admin_reply(conversation_id):
    # Get the admin's reply from the form
    admin_reply = request.form['admin_reply']
    print(admin_reply, "admin reply")
    # Create a SQLAlchemy session
    session = db.session
    
    # Retrieve the corresponding conversation using Session.get()
    conversation = session.get(ChatLog, conversation_id)
    print(conversation, type(conversation))
    if conversation is not None:
        # Update the conversation with the admin's reply
        print("inside the result")
        conversation.bot_response = admin_reply
        session.commit()
    
    return redirect(url_for('admin_conversations'))


if __name__ == '__main__':
    app.run()