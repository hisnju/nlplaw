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
        ######################################################
        self.memory = ConversationBufferMemory(memory_key="chat_history", input_key="question")

    def decide_db_or_llm(self, question: str, index_name: str, namespace_name: str):
        def init_pinecone(index_name):
            pc = pinecone.Pinecone(
                api_key = config.get('pinecone','api_key'),
                environment='gcp-starter'
            )
            index = pc.Index(index_name)
            return index

        def get_embedding(question):
            return self.embeddings_model.embed_query(question)
            
        def search_from_pinecone(index, query_embedding, k):
            return index.query(vector=query_embedding, top_k=k, include_metadata=True, namespace=namespace_name)
        
        # Decide db or llm
        print('Initial pincone...')
        index = init_pinecone(index_name)
        print('Get question embedding...')
        query_embedding = get_embedding(question)
        print('Search similarity from pinecone...')
        qa_results = search_from_pinecone(index, query_embedding, k=1)
        
        self.similarity_matches = []
        for every_info in qa_results['matches']:
            # If score >= 0.81
            if every_info['score'] >= 0.81:
                temp={}
                temp['answer']=every_info['metadata']['text']

                # print(f"question: {every_info['metadata']['question']}")
                # print(f"score: {every_info['score']}")

                self.similarity_matches.append(temp)
        
        if self.similarity_matches==[]:
            return 'ai'
        else:
            return 'db'
        
    def process_by_db(self, question: str, answer_by_llm = True):

        template = """
        你是很會說故事的人，請用繁體中文回答以下問題，並回答20個字左右

        ######################################################
        {chat_history}

        內容:{context}
        問題: {question}

        專業的答案:"""

        ######################################################
        PROMPT = PromptTemplate(template=template, input_variables=["chat_history", "context", "question"])

        if answer_by_llm:
            # Get qa chain input
            print('- Get langchain correct input type...')
            all_text_from_similarity = ' '.join([i['answer'] for i in self.similarity_matches])
            documents = [Document(page_content=all_text_from_similarity)]

            print('- Split text (chunk_size = 500, chunk_overlap = 100)...')
            # Split text to docs
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
            docs = text_splitter.split_documents(documents)

            print('- Get response from similarity topK (chain_type = refine)...')
            # Get response from qa_chain
            ######################################################
            chain = load_qa_chain(llm=self.openai, chain_type="stuff", prompt=PROMPT, memory=self.memory)
            response = chain.run(input_documents=docs, question=question)

            print('ANSWER BY CONTENT:')
            print(self.similarity_matches)

            return response
        else:
            return self.similarity_matches[0]['answer']
    
    def process_by_llm(self, question: str):
        template = """
        你是一個很會說故事的人

        ######################################################
        {chat_history}

        問題: {question}

        答案:"""

        ######################################################
        PROMPT = PromptTemplate(template=template, input_variables=["chat_history", "question"])
        
        ######################################################
        llm_chain = LLMChain(llm=self.openai, prompt=PROMPT, memory=self.memory)
        response = llm_chain.run(question)
        return response

    def answer_question(self, question: str, index_name: str, namespace_name: str):
        if self.decide_db_or_llm(question, index_name, namespace_name) == 'db':
            print('Processing by database (pincone) !!!')
            return self.process_by_db(question, True)
        else:
            print('Processing by llm !!!')
            return self.process_by_llm(question)
        
    def __repr__(self):
        return self.memory.load_memory_variables({})['chat_history']
