# Project 1 --- AI Customer Support Copilot

**Timeline:** Summer 2023\
**Level:** LLM fundamentals\
**Goal:** Build a practical first-generation GenAI application that
demonstrates understanding of LLM APIs, prompt engineering,
conversational context, REST APIs, persistence, and basic production
practices.

------------------------------------------------------------------------

## 1. Project Overview

The AI Customer Support Copilot is a backend application that helps
customer-service teams answer common customer questions using an LLM.

A user sends a natural-language support question such as:

> "My order was supposed to arrive yesterday. What should I do?"

The application identifies the general intent, builds a structured
prompt, sends it to an LLM, and returns a concise customer-friendly
response.

The project deliberately avoids advanced RAG and agentic architecture.
Its purpose is to demonstrate the fundamentals of building an
LLM-powered application.

### Core capabilities

-   Natural-language customer questions
-   Intent classification
-   Prompt templates
-   LLM response generation
-   Conversation/session history
-   REST API
-   PostgreSQL persistence
-   Basic validation and error handling
-   Request/response logging
-   Simple evaluation dataset

------------------------------------------------------------------------

## 2. Why This Project Fits Summer 2023

This should look like the beginning of your AI journey.

The technical progression should be:

``` text
Traditional Backend
      ↓
LLM API
      ↓
Prompt Engineering
      ↓
Structured LLM Application
      ↓
Persistent Conversations
```

Do **not** introduce LangGraph, Kafka, vector databases, RAG, or complex
autonomous agents here.

Those technologies should appear naturally in later projects.

------------------------------------------------------------------------

## 3. Suggested Technology Stack

### Backend

-   Python
-   FastAPI
-   Pydantic
-   Uvicorn

### AI

-   OpenAI API
-   Prompt engineering
-   Structured prompting
-   Basic intent classification

### Database

-   PostgreSQL
-   SQLAlchemy

### Development

-   Docker
-   Git/GitHub
-   pytest

------------------------------------------------------------------------

## 4. High-Level Architecture

``` text
                    ┌──────────────────┐
                    │   Client / UI    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    FastAPI       │
                    │   REST API       │
                    └────────┬─────────┘
                             │
                  ┌──────────┴──────────┐
                  │                     │
                  ▼                     ▼
          ┌───────────────┐     ┌───────────────┐
          │ Intent /      │     │ PostgreSQL    │
          │ Prompt Logic  │     │ Conversation  │
          └───────┬───────┘     │ History       │
                  │             └───────────────┘
                  ▼
          ┌───────────────┐
          │  OpenAI API   │
          │      LLM      │
          └───────┬───────┘
                  │
                  ▼
          ┌───────────────┐
          │ Final Support │
          │ Response      │
          └───────────────┘
```

------------------------------------------------------------------------

## 5. Main Request Flow

### Step 1 --- Customer submits a question

Example:

``` json
{
  "customer_id": "C10291",
  "message": "I was charged twice for my order.",
  "conversation_id": "conv-1001"
}
```

### Step 2 --- Validate the request

FastAPI/Pydantic validates:

-   customer ID
-   message length
-   conversation ID
-   supported request format

### Step 3 --- Determine intent

The application can classify requests into categories such as:

-   ORDER_STATUS
-   DELIVERY_DELAY
-   REFUND
-   PAYMENT_PROBLEM
-   CANCEL_ORDER
-   PRODUCT_INFORMATION
-   GENERAL_SUPPORT

For an early project, this can be implemented using an LLM prompt rather
than a machine-learning classifier.

### Step 4 --- Build the response prompt

Example:

``` text
System:
You are a helpful customer support assistant.
Be concise, professional, and empathetic.
Do not invent company policies.
If the available information is insufficient, say so.

Customer intent:
PAYMENT_PROBLEM

Conversation:
...

Customer:
I was charged twice for my order.

Generate a helpful response.
```

### Step 5 --- Call the LLM

Send the structured prompt to the OpenAI API.

### Step 6 --- Persist the interaction

Store:

-   conversation ID
-   customer ID
-   user message
-   detected intent
-   assistant response
-   timestamp
-   latency
-   model name

### Step 7 --- Return response

``` json
{
  "conversation_id": "conv-1001",
  "intent": "PAYMENT_PROBLEM",
  "response": "I'm sorry about the duplicate charge. Please check..."
}
```

------------------------------------------------------------------------

## 6. Database Design

### conversations

``` text
id
customer_id
created_at
updated_at
```

### messages

``` text
id
conversation_id
role
content
intent
created_at
```

### model_requests

``` text
id
conversation_id
model
prompt_tokens
completion_tokens
latency_ms
status
created_at
```

The model-request table gives the project a more engineering-oriented
feel and lets you analyze performance and usage later.

------------------------------------------------------------------------

## 7. Prompt Engineering

Create separate prompts for:

### Intent classification

Return only structured intent output.

``` text
Classify the customer request into exactly one of:

ORDER_STATUS
DELIVERY_DELAY
REFUND
PAYMENT_PROBLEM
CANCEL_ORDER
PRODUCT_INFORMATION
GENERAL_SUPPORT
```

### Response generation

Use a separate prompt to generate the final customer-facing response.

This separation demonstrates that you understand that an LLM application
can have multiple logical stages instead of sending one giant prompt.

------------------------------------------------------------------------

## 8. Conversation Memory

Support multi-turn conversations.

Example:

``` text
User:
Where is my order?

Assistant:
Your order is currently in transit.

User:
When should I receive it?

Assistant:
Based on the current delivery status...
```

The backend retrieves recent messages from PostgreSQL and includes
relevant conversation history in the prompt.

Keep the context window deliberately small rather than implementing
sophisticated memory.

------------------------------------------------------------------------

## 9. API Design

### POST /api/v1/chat

Send a customer message.

### GET /api/v1/conversations/{id}

Retrieve conversation history.

### GET /api/v1/health

Application health check.

### GET /api/v1/metrics

Return basic application statistics.

------------------------------------------------------------------------

## 10. Basic Reliability

Implement:

-   Request validation
-   LLM timeout handling
-   Retry for transient failures
-   Maximum prompt/message length
-   Structured error responses
-   Request IDs
-   Logging
-   Database transaction handling

Example:

``` text
Client
  ↓
Request ID
  ↓
Validation
  ↓
LLM request
  ↓
Database persistence
  ↓
Response
```

------------------------------------------------------------------------

## 11. Evaluation

Create a small benchmark containing approximately 50--100 support
questions.

For each question define:

-   expected intent
-   acceptable response characteristics
-   prohibited hallucinations

Measure:

-   Intent classification accuracy
-   Response success rate
-   Average latency
-   LLM API failure rate
-   Percentage of responses requiring fallback

Example target metrics:

``` text
Intent accuracy:        >90%
Successful requests:    >98%
Average latency:        <3 seconds
API failure recovery:   >95%
```

These should be treated as project targets unless actually measured.

------------------------------------------------------------------------

## 12. Testing

### Unit tests

Test:

-   prompt construction
-   intent parsing
-   validation
-   database operations

### Integration tests

Test:

``` text
FastAPI → Service → Database
```

Mock the LLM API where appropriate.

### API tests

Test:

-   valid requests
-   malformed requests
-   missing conversation ID
-   oversized messages
-   LLM failures

------------------------------------------------------------------------

## 13. Suggested Repository Structure

``` text
ai-customer-support-copilot/
├── app/
│   ├── api/
│   │   └── routes.py
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── intent_service.py
│   │   └── conversation_service.py
│   ├── prompts/
│   │   ├── intent.txt
│   │   └── response.txt
│   ├── models/
│   ├── repositories/
│   ├── config.py
│   └── main.py
├── tests/
├── scripts/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

------------------------------------------------------------------------

## 14. Resume Positioning

### Title

**AI Customer Support Copilot**

### Stack

**Python, FastAPI, OpenAI API, PostgreSQL, Docker**

### Resume bullets

-   Built an LLM-powered customer support assistant using Python,
    FastAPI, and OpenAI APIs to generate context-aware responses across
    common support intents.
-   Designed prompt-based intent classification and response-generation
    workflows with PostgreSQL-backed conversation history for multi-turn
    interactions.
-   Added request validation, retry handling, structured logging, and a
    100-query evaluation set to measure intent accuracy, latency, and
    response reliability.

Only use numerical results that you actually measure.

------------------------------------------------------------------------

# Project 1 Success Criteria

By completing this project, you should be able to explain:

1.  How an LLM API works.
2.  How prompts affect output quality.
3.  How to maintain conversation context.
4.  How to expose an LLM through a REST API.
5.  How to persist conversations.
6.  How to handle model failures.
7.  How to evaluate an LLM application.

This creates the foundation for Project 2.
