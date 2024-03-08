from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain.llms.openai import OpenAI
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain.memory import ConversationBufferMemory
from pprint import pprint

import configparser
import pinecone
import warnings
warnings.filterwarnings('ignore')

# Setup
config = configparser.ConfigParser()
config.read('config.ini')

class Rachel_langchain():
    def __init__(self):
        self.openai = OpenAI(api_key=config.get('OpenAI','api_key'), organization=config.get('OpenAI','organization'), temperature=0)
        self.embeddings_model = OpenAIEmbeddings(openai_api_key=config.get('OpenAI','api_key'))
        self.similarity_matches = []
        self.memory = ConversationBufferMemory(memory_key="chat_history", input_key="question")

    def decide_db_or_llm(self, question: str, index_name: str, namespace_name: str):
        def init_pinecone(index_name):
            pc = Pinecone(api_key=config.get('pinecone','api_key'), environment='gcp-starter')
            return pc.Index(index_name)

        def get_embedding(question):
            return self.embeddings_model.embed_query(question)
            
        def search_from_pinecone(index, query_embedding, k):
            return index.query(vector=query_embedding, top_k=k, include_metadata=True, namespace=namespace_name)
        
        # Decide db or llm
        index = init_pinecone(index_name)
        query_embedding = get_embedding(question)
        qa_results = search_from_pinecone(index, query_embedding, k=1)
        
        self.similarity_matches = [{'answer': info['metadata']['text']} for info in qa_results['matches'] if info['score'] >= 0.81]
        
        return 'db' if self.similarity_matches else 'ai'

    def process_by_db(self, question: str, answer_by_llm=True):
        template = """你是很會說故事的人，請用繁體中文回答以下問題，並回答20個字左右
        ######################################################
        {chat_history}
        內容:{context}
        問題: {question}
        專業的答案:"""
        PROMPT = PromptTemplate(template=template, input_variables=["chat_history", "context", "question"])

        all_text_from_similarity = ' '.join([i['answer'] for i in self.similarity_matches])
        documents = [Document(page_content=all_text_from_similarity)]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        docs = text_splitter.split_documents(documents)
        chain = load_qa_chain(llm=self.openai, chain_type="stuff", prompt=PROMPT, memory=self.memory)
        response = chain.run(input_documents=docs, question=question)

        return response if answer_by_llm else self.similarity_matches[0]['answer']
    
    def process_by_llm(self, question: str):
        template = """你是一個很會說故事的人
        ######################################################
        {chat_history}
        問題: {question}
        答案:"""
        PROMPT = PromptTemplate(template=template, input_variables=["chat_history", "question"])
        
        llm_chain = LLMChain(llm=self.openai, prompt=PROMPT, memory=self.memory)
        return llm_chain.run(question)

    def answer_question(self, question: str, index_name: str, namespace_name: str):
        if self.decide_db_or_llm(question, index_name, namespace_name) == 'db':
            return self.process_by_db(question, True)
        else:
            return self.process_by_llm(question)
        
    def __repr__(self):
        return self.memory.load_memory_variables({})['chat_history']
