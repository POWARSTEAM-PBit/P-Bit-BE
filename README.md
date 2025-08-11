## Executing FastAPI Backend

Firstly, create a python virtual environment. This is an isloated environment which is common across all OS and architecture.

```python
python3 -m venv env
```

Secondly, activate the virtual environment

```python
pip install -r requirements.txt
```

Then, execute the following command to start the fast-api backend:

```python
uvicorn main:app
```


## API Documentation 

To view auto-generated documentation, visit:

http://localhost:8000/docs

The following page will show the generated documentation for the current API.