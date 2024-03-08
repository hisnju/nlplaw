import openai
import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2 import pool


# 遠端連接
connection_string = "dbname= user= password= host= port="
# 创建连接池
connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, connection_string)

# 连接到本地 PostgreSQL 数据库
conn = connection_pool.getconn()
cur = conn.cursor()

# Register pgvector extension
register_vector(conn)

# 缓存 embeddings
embeddings_cache = {}


# 增加一个简单的函数来判断问题是否可能与法律相关
def legal_question(question):
    # 定义一些与法律相关的关键词
    legal_keywords = ['法律', '合同', '條例', '法規', '問題', '侵權', '專利', '違法', '處理', '怎', '怎麼做', '刑法', '民法', '如何', '有效', '重複', '法', '官司', '罰責', '罰', '什麼', '申訴', '歧視', '嗎', '賠', '償', '為何']
    # 如果问题中包含上述关键词之一，则认为它可能是一个法律问题
    return any(keyword in question for keyword in legal_keywords)

# Helper function: Get top 1 most similar documents from the database
def get_top1_similar_docs(query_embedding):
    conn = connection_pool.getconn()
    try:
        cur = conn.cursor()
        embedding_array = np.array(query_embedding)
        cur.execute("SELECT mix FROM embeddings ORDER BY embedding <=> %s LIMIT 1", (embedding_array,))
        top1_docs = cur.fetchall()
        return top1_docs
    finally:
        cur.close()
        connection_pool.putconn(conn)

# Helper function: get text completion from OpenAI API
# Note we're using the latest gpt-3.5-turbo-0613 model
def get_completion_from_messages(messages, model="gpt-3.5-turbo-16k-0613", temperature=0.5, max_tokens=700):
    openai.api_key = ''
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature, 
        max_tokens=max_tokens,
    )
    return response.choices[0].message["content"]

def get_embeddings(text):
    # 检查缓存
    if text in embeddings_cache:
        return embeddings_cache[text]
    else:
        openai.api_key = ''
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=text.replace("\n"," ")
        )
        embedding = response['data'][0]['embedding']
        # 存储到缓存
        embeddings_cache[text] = embedding
        return embedding
    
# Function to process input with retrieval of most similar documents from the database
def process_input_with_retrieval(user_id, user_input, conn):
    # 使用刚才定义的函数来判断用户输入
    if not legal_question(user_input):
        # 如果不是法律问题，直接返回预设回复
        return "很抱歉，我只能回答與法律相關的問題。"
    delimiter = "```"

    # Step 1: Retrieve the last 3 conversation pairs (questions and answers) for the user
    cur.execute("SELECT question, answer FROM conversation WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1", (user_id,))
    conversation_pairs = cur.fetchall()

    # Step 2: Get documents related to the user input from the database
    related_docs = get_top1_similar_docs(get_embeddings(user_input))

    system_message = f"""
    您好！ 我是您的法律助理。
    在提供不提及任何特定的個人名稱任何法律建議之前，我會先評估您的情況是否涉及法律問題：
    - 對於確實涉及法律問題的情況，我會盡力指出相關的法律條款，並給予相應的建議。
    - 如果您的問題超出了我的能力範圍或不涉及法律領域，我可能無法提供滿意的答案。
    請理解，我提供的答案僅基於一般法律知識，並不能取代專業律師的意見。 對於具體的法律問題，建議諮詢專業的法律顧問以獲得更準確的指導。
    謝謝您的體諒與信任！
    """


    # Step 3: Prepare messages to pass to the model, including the recent conversation history
    messages = [{"role": "system", "content": system_message}]
    # Add recent conversation pairs with appropriate roles
    for question, answer in reversed(conversation_pairs):  # Reversed to maintain chronological order
        messages.append({"role": "user", "content": question})
        if answer:  # Only add non-empty answers
            messages.append({"role": "assistant", "content": answer})
    # Add current user input
    messages.append({"role": "user", "content": f"{delimiter}{user_input}{delimiter}"})
    # Add related documents as part of the assistant's response
    messages.append({"role": "assistant", "content": f"相關資訊如下: \n{related_docs[0][0]}"})

    # Step 4: Get the completion from the OpenAI API using the prepared messages
    final_response = get_completion_from_messages(messages)

    return final_response

connection_pool.putconn(conn)


