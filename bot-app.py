import logging
from autogen import UserProxyAgent, config_list_from_json, GroupChat, GroupChatManager
from custom_gpt_assistant_agent import GPTAssistantAgent
from flask import Flask, request, jsonify
import threading


app = Flask(__name__)

assistant_id = "asst_aqdlz5KLXuZyIRkLXAJoz55p"
vector_store_id = "vs_sKOqqV5MogLYT7Yr3Ic4Id3Q"
assistant_name = "CorpComms-Assistant"

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

config_list_gpt4 = config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4o"],
    },
)

# Define user proxy agent
llm_config = {"config_list": config_list_gpt4, "cache_seed": 45}

assistant_config = {
    "tools": [{"type": "file_search"}],
      "tool_resources": {
        "file_search": {
            "vector_store_ids": [vector_store_id]
        }
    },
}
asst_prompt = "You are an AI Assistant that manages all the corporate communications and the custodian of all Customer Case Studies / Customer Testimonials / Customer Success. Your task is to: 1) Look at the content in the incoming message, determine the area or expertise for which Customer case studies are asked for. 2) With this input, refer to the context available to you and return a well formatted narrative for at least ~ 3 Customer testimonials and also a summary of ~ 3 customer case studies. Format the content before returning the response."



gpt_assistant = GPTAssistantAgent(
    name=assistant_name,
    instructions=asst_prompt,
    llm_config=llm_config,
    assistant_config=assistant_config
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    code_execution_config=False,
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
    human_input_mode="NEVER",
    system_message="Once you are done, please type 'TERMINATE' to end the conversation.",
)



def extract_content(chat_history):
    # chat_history
    extracted_content = ''
    
    for entry in chat_history:
        if entry.get('role') == 'user' and entry.get('name') == 'CorpComms-Assistant':
            extracted_content = entry.get('content')
            break
    return extracted_content

# user_proxy.initiate_chat(gpt_assistant, message="Give me an executive summary of 3 Customer Success stories")
## gpt_assistant.delete_assistant()
# user_query = "Give me 3 case studies of Customer implementations"
# response = user_proxy.initiate_chat(gpt_assistant, message=user_query)
# # print(f"Response: {response}")
# extracted_content = extract_content(response.chat_history)





@app.route('/api/autogen', methods=['POST'])
def handle_autogen_request():
    user_query = request.json.get('query')
    # print(f"Received query: {user_query}")
    groupchat = GroupChat(agents=[user_proxy, gpt_assistant], messages=[], max_round=2)
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    response = user_proxy.initiate_chat(manager, message=user_query)
    # print(f"Response: {response}")
    extracted_content = extract_content(response.chat_history)
    return jsonify({"response": extracted_content})


class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app
        self.port = None

    def run(self):
        self.port = 36919  # Example port
        app.logger.info(f"Service running on: http://127.0.0.1:{self.port}")
        self.app.run(port=self.port)

if __name__ == "__main__":
    server_thread = ServerThread(app)
    server_thread.start()
    try:
        server_thread.join()
    except (KeyboardInterrupt, SystemExit):
        app.logger.info("Shutting down server...")
