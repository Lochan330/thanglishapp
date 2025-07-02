import streamlit as st
import requests
from serpapi import GoogleSearch
from deep_translator import GoogleTranslator
from langdetect import detect
import re

# Load GROQ and SERPAPI keys from Streamlit secrets
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SERPAPI_API_KEY = st.secrets["SERPAPI_API_KEY"]

# Translator
translator = GoogleTranslator(source='auto', target='en')

# Streamlit UI
st.title("Enhanced Mini Perplexity - Advanced Thanglish Support!")
st.write("Ask me anything in English or Thanglish, and I'll generate a response using advanced NLP techniques and up-to-date web information!")

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Detect Thanglish
def is_thanglish(text):
    tamil_chars = re.findall(r'[\u0B80-\u0BFF]', text)
    english_chars = re.findall(r'[a-zA-Z]', text)
    return bool(tamil_chars) and bool(english_chars)

# Translate to English if needed
def translate_if_needed(text):
    try:
        detected_lang = detect(text)
        if detected_lang == 'ta':
            return translator.translate(text)
        return text
    except Exception as e:
        st.error(f"Translation error: {str(e)}")
        return text

# Web search via SerpAPI
def search_web(query):
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": 5
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get("organic_results", [])[:5]

# Format search results
def format_search_results(results):
    formatted_results = [
        f"Title: {result['title']}\nSnippet: {result['snippet']}\nLink: {result['link']}\n"
        for result in results
    ]
    return "\n".join(formatted_results)

# Call GROQ API
def call_groq_gpt4o(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 500
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Main function to call GROQ with logic
def call_gpt4o_api(prompt, include_web_search=False):
    try:
        if is_thanglish(prompt):
            enhanced_prompt = (
                f"Respond in Thanglish naturally with conversational fluency. "
                f"Ensure casual, engaging, and contextually relevant replies. "
                f"User query: {prompt}"
            )
        else:
            translated_prompt = translate_if_needed(prompt)
            if include_web_search:
                search_results = search_web(translated_prompt)
                formatted_results = format_search_results(search_results)
                enhanced_prompt = (
                    f"Based on the web search results and your internal knowledge, answer the question: "
                    f"'{translated_prompt}'\n\nWeb search results:\n{formatted_results}\n\nYour response:"
                )
            else:
                enhanced_prompt = translated_prompt
                search_results = []

        content = call_groq_gpt4o(enhanced_prompt)
        return content, search_results if include_web_search else []

    except Exception as e:
        return f"Error: {str(e)}", []

# Streamlit UI logic
user_input = st.text_input("Enter your question (in English or Thanglish):")
use_web_search = st.checkbox("Enable web search for up-to-date information")

if user_input:
    with st.spinner("Generating response..."):
        response_text, search_results = call_gpt4o_api(user_input, include_web_search=use_web_search)
        st.subheader("AI Response:")
        st.write(response_text)

        if use_web_search and search_results:
            st.subheader("Web Search Results:")
            for idx, result in enumerate(search_results, 1):
                with st.expander(f"Source {idx}: {result['title']}"):
                    st.write(f"*Snippet:* {result['snippet']}")
                    st.write(f"*Link:* {result['link']}")

        st.session_state.chat_history.append({
            "question": user_input,
            "response": response_text,
            "web_results": search_results if use_web_search else []
        })
        st.success("Response generated!")

if st.session_state.chat_history:
    st.write("### Chat History")
    for chat in st.session_state.chat_history:
        st.write(f"*You:* {chat['question']}")
        st.write(f"*Assistant:* {chat['response']}")
        if chat['web_results']:
            st.write("*Web Sources:*")
            for idx, result in enumerate(chat['web_results'], 1):
                st.write(f"{idx}. [{result['title']}]({result['link']})")
        st.write("---")
