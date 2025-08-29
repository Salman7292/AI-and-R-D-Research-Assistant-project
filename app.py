# app.py
from flask import Flask, request, jsonify, render_template
from langchain_community.tools import TavilySearchResults
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import json
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load environment variables from .env file
load_dotenv()

# Initialize tools
search = TavilySearchResults(max_results=6)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", api_key=os.getenv("GOOGLE_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/research', methods=['POST'])
def research():
    try:
        # Get user query and search option from request
        data = request.get_json()
        user_query = data['query']
        use_search = data.get('use_search', False)
        
        # If search is enabled, perform Tavily Search
        if use_search:
            results = search.run(user_query)
            
            # Ensure results is list of dicts
            if isinstance(results, str):
                results = json.loads(results)
            
            # Build context for LLM with all results
            context = ""
            for i, r in enumerate(results, start=1):
                title = r.get("title", "No Title")
                url = r.get("url", "")
                content = r.get("content", "")
                context += f"\n---\nResult {i}\nTitle: {title}\nURL: {url}\nContent: {content}\n"
            
            # Prompt for Gemini with search results
            prompt = f"""
            You are a helpful research assistant.
            The user asked: "{user_query}"

            Here are multiple web search results:
            {context}

            Task:
            1. Read and understand all the results.  
            2. Summarize the important findings in detail using proper markdown formatting.
            3. Use **bold** for important terms, *italic* for emphasis, and proper headings for sections.
            4. While explaining, clearly mention *"According to [Title] (Source Link)"* for each reference.
            5. Provide a structured explanation with clear sections so the user knows which information came from which reference.
            6. Use line breaks and spacing to make the response easy to read.
            7. Format your response using markdown syntax for all formatting elements.
            8. At the end, provide a brief assessment of how well these sources address the user's query.
            """
            
            # Get response from LLM
            response = llm.invoke(prompt)
            
            # Extract sources for the sources panel
            sources = []
            for i, r in enumerate(results, start=1):
                sources.append({
                    'title': r.get('title', 'No Title'),
                    'url': r.get('url', ''),
                    'content': r.get('content', '')[:200] + '...' if len(r.get('content', '')) > 200 else r.get('content', '')
                })

            print("Response:", response.content)  # Debugging line
            
            return jsonify({
                'response': response.content,
                'sources': sources,
                'used_search': True
            })
        else:
            # If search is not enabled, use the LLM directly
            prompt = f"""
            You are a helpful research assistant.
            The user asked: "{user_query}"
            
            Task:
            1. Provide a comprehensive answer based on your knowledge.
            2. Use proper markdown formatting with **bold** for important terms and *italic* for emphasis.
            3. Structure your response with clear sections.
            4. If you reference any concepts or information that might come from specific sources, mention that.
            5. Be honest about the limitations of your knowledge if you're uncertain.
            """
            
            response = llm.invoke(prompt)
            
            return jsonify({
                'response': response.content,
                'sources': [],
                'used_search': False
            })
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'response': 'Sorry, there was an error processing your request.',
            'sources': [],
            'used_search': False
        }), 500

if __name__ == '__main__':
    app.run(debug=True)