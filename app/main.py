from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.auth import read_session_token
from app.config import BASE_DIR
from app.db import init_db
from app.routes import analysis, auth, drafts, reports, tasks
from app.templating import templates


app = FastAPI(title="EduTech 课程销售合规与多语言跟进 Agent 系统")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


@app.get("/")
def root(request: Request):
    if getattr(getattr(request, "state", None), "session", {}).get("username"):
        return RedirectResponse("/analysis", status_code=303)
    return RedirectResponse("/login", status_code=303)


@app.get("/favicon.ico")
def favicon():
    return RedirectResponse("/static/img/favicon.svg", status_code=301)


@app.middleware("http")
async def load_session(request: Request, call_next):
    token = request.cookies.get("session")
    if token:
        data = read_session_token(token)
        if data:
            request.state.user = data
            request.state.session = data
    else:
        request.state.user = None
        request.state.session = {}
    response = await call_next(request)
    return response


@app.on_event("startup")
def startup():
    from app.routes.auth import ensure_seed_users

    init_db()
    ensure_seed_users()


app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(drafts.router)
app.include_router(reports.router)
app.include_router(tasks.router)
