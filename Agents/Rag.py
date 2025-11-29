import chromadb 
from huggingface_hub import InferenceClient
import streamlit as st
import re

class Rag:

    def __init__(self):
         
        token = st.secrets["HF_token"]
        self.client = InferenceClient(
            # provider="hf-inference",
            api_key=token,
        )
        client_db = chromadb.CloudClient(
            api_key= st.secrets["Chromadb_token"],
            tenant='2c00d764-53a9-4bad-9e5e-4f1bce13358d',
            database='Edu_KB'
                )
        self.K_db = client_db.get_collection(name="books")


    # call the model
    def call_model(self, prompt, model_name = "HuggingFaceTB/SmolLM3-3B",  temperature=0.5, top_p = 0.5, stream = False): 
        completion = self.client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature= temperature,
        top_p= top_p,
        stream=stream, # send wonce finished
        )
        raw_output = completion.choices[0].message.content
        return raw_output
        
    def explain(self, query:str): 

        def gen_prompt(reterival : str, query: str):
            
            prompt = f""" You are a english teaching assistant, 
            you should help explaining english concepts like grammer in an easy, 
            explicit way using clear communication.
            using this context : {reterival} , answer the following question {query}"""

            return prompt
        
        # retreving context
        reterival = self.K_db.query(
        query_texts = [query],
        n_results = 1 
        )
        book = reterival["metadatas"][0][0]["file_name"]
        #print(''.join(reterival["documents"][0]), "\n")
        reterival = ''.join(reterival["documents"][0])
        prompt =  gen_prompt(reterival, query)
        messages = [
        {"role": "user", "content": prompt},
        ]


        completion = self.client.chat.completions.create(
            # model="zai-org/GLM-4.6:novita",
            model = "HuggingFaceTB/SmolLM3-3B",
            messages=messages)
        
        # completion.choices[0].message
        content = completion.choices[0].message.content 
        if "<think>" in content:
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return  (content+
                f"\n\n:blue-background[The answer was driven from :violet[{book}]]")


