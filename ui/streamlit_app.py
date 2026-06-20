import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/chat"

st.title("Financial RAG V1.7")

question = st.text_input("Ask a question")

if question:

    with st.spinner("Thinking..."):

        res = requests.post(API_URL, json={"question": question}).json()

        answer = res["answer"]
        citations = res["citations"]
        mode = res["mode"]

    # streaming模拟
    placeholder = st.empty()
    output = ""

    for char in answer:
        output += char
        placeholder.markdown(output)