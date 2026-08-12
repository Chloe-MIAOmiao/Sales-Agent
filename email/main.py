import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI

# 1. 加载 .env 配置文件
load_dotenv()

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY is required")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 2. 定义结构化数据 Schema (来自 agent_pipeline)
class CustomerProfile(BaseModel):
    customer_pain_point: str = Field(description="客户的核心痛点或转行原因")
    budget_sensitivity: str = Field(description="价格敏感度，必须是 'High', 'Medium', 或 'Low'")
    sales_compliance_risk: str = Field(description="销售人员使用的夸大承诺或违规话术（如100%学会、保证20万年薪）")
    deal_probability: str = Field(description="成交概率预测，必须是 'High', 'Medium', 或 'Low'")

# 3. 定义 Agent 使用的真实工具
def create_email_draft_file(recipient_name: str, subject: str, body: str) -> str:
    """在本地写入英文邮件草稿"""
    filename = f"draft_for_{recipient_name.replace(' ', '_')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"To: {recipient_name}\nSubject: {subject}\n\n{body}")
    return filename

def send_email_to_customer(recipient_name: str, filename: str) -> str:
    """模拟真实发送邮件"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        print("\n📧 ================= 正在发送以下内容的邮件 =================")
        print(content)
        print("======================================================================")
        print(f"✅ [SYSTEM] 邮件已成功发送给 {recipient_name}！")
        return "SUCCESS"
    except FileNotFoundError:
        return "ERROR: 未找到草稿文件"

# 4. 主流程逻辑
def run_sales_agent(file_path: str):
    print("🚀 [Step 1/3] 正在读取对话日志并进行合规审计与客户画像提取...")
    with open(file_path, 'r', encoding='utf-8') as f:
        chat_history = f.read()

    # Step 1: 结构化画像与合规分析
    profile_schema = CustomerProfile.model_json_schema()
    step1_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": f"你是一个销售合规与情报分析 Agent。分析对话并只返回符合该 Schema 的 JSON: {json.dumps(profile_schema)}"},
            {"role": "user", "content": chat_history}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    profile_json = step1_response.choices[0].message.content
    print("✅ 客户画像与合规风险分析完成！")
    print(f"📊 分析报告:\n{profile_json}\n")

    # Step 2: 根据分析生成合规的英文跟进邮件
    print("🤖 [Step 2/3] Agent 正在生成针对性的英文 Follow-up 邮件草稿...")
    prompt = f"""
    你是一位高级销售总监。请根据以下客户画像分析，写一封高质量、专业的英文跟进邮件给张女士（Ms. Zhang）。
    注意：在邮件中要安抚她的价格与退款顾虑，但严禁出现任何违规保底承诺（如保证就业、保证20万年薪等）。
    
    客户画像分析数据：
    {profile_json}
    
    直接输出邮件主题和正文即可，格式如下：
    Subject: <主题>
    Body: <正文>
    """
    
    email_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    email_text = email_response.choices[0].message.content
    
    # 解析出 Subject 和 Body
    subject = "Follow-up regarding your Data Analytics Boot Camp inquiry"
    body = email_text
    if "Subject:" in email_text and "Body:" in email_text:
        parts = email_text.split("Body:")
        subject = parts[0].replace("Subject:", "").strip()
        body = parts[1].strip()

    # Step 3: 调用 Tool 写入本地草稿，并提示人类审核 (HITL)
    print("✍️ [Step 3/3] Agent 正在调用工具创建本地草稿...")
    filename = create_email_draft_file("Ms. Zhang", subject, body)
    print(f"📁 草稿已成功生成到本地文件: '{filename}'")

    print("\n================== 👥 HUMAN-IN-THE-LOOP (人工审核节点) ==================")
    print(f"请打开 '{filename}' 查看或微调邮件内容。")
    user_input = input("\n👉 是否批准发送这封邮件？(输入 'y' 发送，输入 'n' 拒绝并仅保留草稿): ").strip().lower()

    if user_input == 'y':
        send_email_to_customer("Ms. Zhang", filename)
    else:
        print("❌ 操作已取消，草稿已保存在本地供后续手动修改。")

if __name__ == "__main__":
    run_sales_agent("sales_chat.txt")