import time
#from anoteai import PrivateChatbot
from core import PrivateChatbot


if __name__ == "__main__":
    api_key = 'fda24fe24943169bb79a584911df02bb'

    privatechatbot = PrivateChatbot(api_key, is_private=False)
    #privatechatbot = PrivateChatbot(api_key, is_private=True)


    file_paths = ['sample_docs/doc1.pdf', 'sample_docs/doc2.pdf']

    upload_result = privatechatbot.upload(task_type="documents", model_type="gpt", file_paths=file_paths)
    print("output from upload: ", upload_result)
    chat_id = upload_result['id']
    chat_result = privatechatbot.chat(chat_id, "What is this paper classification performance about?")
    print("output from chat: ", chat_result)
    message_id = chat_result['message_id']
    print("output from evaluate:", privatechatbot.evaluate(message_id))



    #PUBLIC
    # file_paths = ['sample_docs/doc1.pdf', 'sample_docs/doc2.pdf', 'https://docs.anote.ai/']
    # chat_id = privatechatbot.upload(task_type="documents", model_type="gpt", file_paths=file_paths)['id']

    # response1 = privatechatbot.chat(chat_id, "Who wrote the paper on Improving Classification performance?")
    # print("Answer:", response1['answer'])
    # print("Sources:", response1['sources'])
    # message_id1 = response1['message_id']

    # print(privatechatbot.evaluate(message_id1))

    # print("-------------------------------------------------")

    # response2 = privatechatbot.chat(chat_id, "What is Private Chatbot?")
    # print("Answer:", response2['answer'])
    # print("Sources:", response2['sources'])
    # message_id2 = response2['message_id']

    # print(privatechatbot.evaluate(message_id2))

    #PRIVATE
    # file_paths = ['sample_docs/doc1.pdf', 'sample_docs/doc2.pdf', 'https://docs.anote.ai/']
    # chat_id = privatechatbot.upload(task_type="documents", model_type="llama", file_paths=file_paths)['id']

    # response1 = privatechatbot.chat(chat_id, "Who are the authors of the paper on Improving Classification performance?")
    # print("Answer:", response1['answer'])
    # print("Sources:", response1['sources'])
    # message_id1 = response1['message_id']

    # print(privatechatbot.evaluate(message_id1))

    # print("-------------------------------------------------")

    # response2 = privatechatbot.chat(chat_id, "What is Private Chatbot?")
    # print("Answer:", response2['answer'])
    # print("Sources:", response2['sources'])
    # message_id2 = response1['message_id']

    # print(privatechatbot.evaluate(message_id2))








