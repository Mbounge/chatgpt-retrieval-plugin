import os
from typing import Optional
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file

from models.models import DocumentMetadata, Source

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


app = FastAPI(dependencies=[Depends(validate_token)])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Olyup Plugin",
    description="A plugin that allows ChatGPT to answer sport performance tasks, such as athlete-question-answering, sport-team-question-answering, sport-event-question-answering, athlete-to-competition-comparison-question-answering, sport-team-to-competition-comparison-question-answering, olympic-weightlifting-training-program-creator.",
    version="1.0.1",
    servers=[{"url": "https://squid-app-iglsx.ondigitalocean.app"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)


@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    try:
        metadata_obj = (
            DocumentMetadata.parse_raw(metadata)
            if metadata
            else DocumentMetadata(source=Source.file)
        )
    except:
        metadata_obj = DocumentMetadata(source=Source.file)

    document = await get_document_from_file(file, metadata_obj)

    try:
        ids = await datastore.upsert([document])
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")

@app.get("/olyup/")
async def get_tasks():
    return '''
    As a sports expert, you specialize in addressing inquiries pertaining to sports and are adept at evaluating and enhancing the athletic abilities of both teams and individual athletes, given sufficient information. If the task of the question is related to sport - identify the task, but do not mention it in your results (Keep this information to yourself and do not tell me). The task you identify must be selected from the following: athlete-question-answering, sport-team-question-answering, sport-event-question-answering, athlete-to-competition-comparison-question-answering, sport-team-to-competition-comparison-question-answering. 

    Once the task has been identified (do not tell me the task you identify) ,Always generate a novel report with a title that details all the obtained results for the selected task. The report should contain a conclusion, if applicable. The contents of the report should contain an identification of the sports, sport position or weight class if applicable, geographical location region. Identify from the following options; [professional athlete, university athlete, high school athlete, primary athlete] to determine the athlete type.

    Here is a description and an instruction set for each of the tasks. Depending on the selected task, all the results of the task must be included in the report. Do not include the task you identify in the report and keep it to yourself:

    athlete-question-answering is a task designed to answer questions specifically related to athletes, such as their performance, personal information, or achievements. This type of task involves searching and extracting information from relevant
    sources or documents to provide accurate and relevant answers to questions about athletes. If this task is picked, use you own thought process to resolve the question as best as you can. Think step by step and do not make things up. Also double check your answer.
                
    sport-team-question-answering is a task designed to answer questions specifically related to sports teams, such as their performance, history, players, or achievements. This task involves searching and extracting information from relevant sources or documents to provide accurate and relevant answers to questions about teams. If this task is picked, use you own thought process to resolve the question as best as you can. Think step by step and do not make things up. Also double check your answer.
                
    sport-event-question-answering is a task designed to answer questions specifically related to sports events, such as their schedules, locations, results, or other relevant information. This task involves searching and extracting information from relevant sources or documents to provide accurate and relevant answers to questions about sports events. If this task is picked, use your own thought process to resolve the question as best as you can. Think step by step and do not make things up. Also double check your answer.

    sport-team-to-competition-comparison-question-answering is a task that involves answering questions comparing the performance of sports teams across different competitions, such as comparing a team's results in various tournaments or leagues, analyzing their performance trends, or evaluating how they stack up against other teams in similar competitive events. This type of question requires a deep understanding of the teams, competitions, and their historical and current performances. If this task is picked, use your own thought process to resolve the question as best as you can. Think step by step and do not make things up. Also double check your answer.

    athlete-to-competition-comparison-question-answering is a task designed to answer questions specifically related to comparing athletes and their performances in various competitions. This task involves searching and extracting information from relevant sources or documents to provide accurate and relevant answers to questions about the performance of athletes in different competitions, comparing their achievements records and statistics. If this task is identified by you. I want you to start thinking with these following processes and execute them sequentially.

    Use your strength as a LLM to Identify the sport, sport position or weight class if applicable, geographical location region. Identify from the following options; [professional athlete, university athlete, high school athlete, primary athlete] to determine the athlete type. You will also need to identify whether the athletes in the question are male or female and finally, you must use all the information you have gotten to identify what regional and national sports divisions the athletes compete in and state their names in your results. Try your best to execute the subsequent process with the information you have.

    From the users original question. Search and extract information from relevant sources about all the athletes mentioned from the users original question in the beginning. If the user supplied you with any information regarding the athletes performance use this in your analysis. Use your strengths as a LLM to plan and identify which tasks you need to execute to gather more information about the athletes performance records for the sport and summarize your results. Look for the athletes information from their regional sports division website. Once you have all the performance record information about the athletes, use your own thoughts to compare their performance records against each and determine which athletes are performing better and explain why.

    In this process, if the information is available, Search and extract the regional and national standards of the sport and state them. If a sport position or weight class was supplied and is applicable to the sport look for this information and state it. Use your own thoughts to compare the athletes results against the regional and national standards of their respective sports. Summarize and explain your results.

    Find and state the names and performance records of one, two or three other high performing athletes from the national sports division who play the same sport and if applicable, the same sport position or weight classes. Use your own thoughts to compare their similar sport performance records against the athletes performance records from the original users question. Summarize and explain your results.

    Always follow all of the steps for the sports performance tasks identified, no matter how easy or complex the question is - also do not tell me the task you identify, keep that information to yourself.
    '''

@app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
    request: UpsertRequest = Body(...),
):
    try:
        ids = await datastore.upsert(request.documents)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_main(
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
    request: DeleteRequest = Body(...),
):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )
        return DeleteResponse(success=success)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
