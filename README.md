# SHL Assessment Recommender

A FastAPI-based conversational recommender for SHL assessments.

## Deployed API

Base URL:

https://shl-assessment-recommender-vxtp.onrender.com

## Endpoints

GET /health

POST /chat

## Example Request

POST /chat

{
  "messages": [
    {
      "role": "user",
      "content": "I am hiring a senior backend engineer with Core Java, Spring, SQL, AWS and Docker experience"
    }
  ]
}

## Run Locally

pip install -r requirements.txt
uvicorn app.main:app --reload

## Docker

docker build -t shl-recommender .
docker run -p 8000:8000 shl-recommender