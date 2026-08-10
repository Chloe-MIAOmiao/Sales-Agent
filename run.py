import uvicorn


def main():
    print("启动 EduTech 课程销售合规与多语言跟进 Agent 系统...")
    print("访问: http://127.0.0.1:8000")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
