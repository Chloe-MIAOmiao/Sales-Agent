import os
import json
from openai import OpenAI

# 1. Define the real-world local tools
def create_email_draft_file(recipient_name: str, subject: str, body: str) -> str:
    filename = f"draft_for_{recipient_name.replace(' ', '_')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"To: {recipient_name}\nSubject: {subject}\n\n{body}")
    return f"SUCCESS: Physical email draft written to file '{filename}'"

# 2. Define a tool to simulate sending the email after human approval
def send_email_to_customer(recipient_name: str, filename: str) -> str:
    try:
        # 读取本地最新的文件内容（包括开发者/销售手动修改过的地方）
        with open(filename, 'r', encoding='utf-8') as f:
            latest_content = f.read()
            
        print(f"\n📧 [SYSTEM] Reading the LATEST draft from '{filename}'...")
        print("================== 📨 SENDING THE FOLLOWING CONTENT ==================")
        print(latest_content)
        print("======================================================================")
        print(f"📡 [SIMULATION] Connecting to SMTP Server... Sending to {recipient_name}...")
        print("✅ [SIMULATION] Email delivered successfully with your latest manual updates!")
        return "SUCCESS: Updated email sent."
    except FileNotFoundError:
        return f"ERROR: Draft file '{filename}' was not found. Cannot send."

def run_advanced_agent(file_path: str):
    my_deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not my_deepseek_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")
    client = OpenAI(api_key=my_deepseek_key, base_url="https://api.deepseek.com")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        chat_history = f.read()

    available_tools = {
        "create_email_draft_file": create_email_draft_file,
        "send_email_to_customer": send_email_to_customer
    }

    tools_definition = [
        {
            "type": "function",
            "function": {
                "name": "create_email_draft_file",
                "description": "Call this to generate a local draft. Parameters: recipient_name, subject, body.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recipient_name": { "type": "string" },
                        "subject": { "type": "string" },
                        "body": { "type": "string" }
                    },
                    "required": ["recipient_name", "subject", "body"]
                }
            }
        }
    ]

    # 🧠 INTRODUCING CONTEXT/MEMORY: We use an active memory buffer (History)
    # This keeps track of everything that happens in the session!
    #替换高强度触发的prompt
    session_memory = [
        {
            "role": "system", 
            "content": (
                "You are a proactive Sales Intelligence Agent. Analyze the conversation. "
                "The customer (Ms. Zhang) has a clear pain point and asked about tuition, "
                "which means she is a highly valuable potential customer (Warm Lead). "
                "You MUST call the 'create_email_draft_file' tool to prepare a follow-up email "
                "addressing her career switching goals and clearing up the pricing/refund concerns."
            )
        },
        {"role": "user", "content": f"Here is the log to analyze:\n\n{chat_history}"}
    ]

    print("🤖 Agent is analyzing the chat log...")
    
    # ---- STEP 1: Run decision ----
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=session_memory, # Use memory
        tools=tools_definition,
        tool_choice="auto"
    )
    
    message = response.choices[0].message
    
    # Append Agent's thoughts to session memory to preserve context!
    session_memory.append(message)

    if message.tool_calls:
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "create_email_draft_file":
                print(f"\n✍️ Agent has generated a draft for {function_args['recipient_name']}!")
                
                # Execute the tool physically
                execution_result = create_email_draft_file(**function_args)
                print(f"🖥️ System: {execution_result}")
                
                # 👥 HUMAN-IN-THE-LOOP (HITL)
                print("\n================== 👥 HUMAN-IN-THE-LOOP REQUIRED ==================")
                print(f"Draft file created: 'draft_for_{function_args['recipient_name'].replace(' ', '_')}.txt'")
                print("Please open the file on your disk and review the draft.")
                
                # Ask the user (developer/sales manager) for approval
                user_approval = input("\n👉 Do you approve sending this email? (type 'y' to send, 'n' to reject): ").strip().lower()
                
                if user_approval == 'y':
                    # Agent continues action with context
                    filename = f"draft_for_{function_args['recipient_name'].replace(' ', '_')}.txt"
                    send_result = send_email_to_customer(function_args['recipient_name'], filename)
                    print(send_result)
                else:
                    print("❌ Action aborted by user. The draft remains saved locally for manual edit.")
    else:
        print("🚫 No draft needed.")

if __name__ == "__main__":
    run_advanced_agent("sales_chat.txt")