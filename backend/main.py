from fastapi import FastAPI

def create_app(database_url=None, config=None):
    return FastAPI()
