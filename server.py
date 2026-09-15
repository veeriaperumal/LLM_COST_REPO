import uvicorn

if __name__ == "__main__":
    # Run the FastAPI app using uvicorn programmatically
    # The string "app.main:app" assumes your FastAPI instance is named `app` in `app/main.py`
    uvicorn.run("app.main:app", host='127.0.0.1', port=9000, reload=True)
