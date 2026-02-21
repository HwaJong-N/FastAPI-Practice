from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(content=jsonable_encoder({"result": "fail", "detail": exc.errors(), "body": exc.body}), status_code=422)

@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request, exc):
    return JSONResponse(content={"result": "fail", "detail": "StarletteHTTPException", "body": str(exc.detail)}, status_code=exc.status_code)

@app.exception_handler(HTTPException)
def http_exception_handler(request,exc):
    return JSONResponse(content={"result": "fail", "detail": "HTTPException", "body":str(exc.detail)},status_code=exc.status_code)

@app.exception_handler(Exception)
def exception_handler(request,exc):
    return JSONResponse(content={"result": "fail", "detail": "Exception", "body":str(exc)}, status_code=500)
