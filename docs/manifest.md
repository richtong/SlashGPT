# Manifest File Is All You Need

**Author:** Satoshi Nakajima

I started writing LLM applications on top of GPT3.5 in April 2023, inspired by
my son's open source project,
[BabyAGI](https://github.com/yoheinakajima/babyagi).

I was aware of the popular library among developers called
[LangChain](https://github.com/langchain-ai/langchain). However, I chose to
write directly on top of OpenAI's API due to its simplicity and
straightforwardness.

I also felt that LangChain's helper-API-based approach is not the right
direction. I strongly believe that the "Declarative" approach is more suitable
for LLM applications, especially for enterprise applications where each company
or even each division needs to have its own application.

Since I wanted to create multiple LLM applications quickly, I started it as an
open source project, [SlashGPT](https://github.com/snakajima/SlashGPT), as my
playground (this name came from "slash commands", which allows me to switch
among AI agents from the terminal).

The design goal of this project was very clear from the beginning.

1. It allows developers to create various LLM applications very quickly.
2. It allows developers to define the behavior of each *AI agent*
   **declaratively** by simply creating a *manifest* file (without writing
   code).
3. It enables complex applications, which involves embedded database and code
   execution.

I am a big fan of "Declarative Programming", because it will significantly
simplify the application development and test process, enabling web-based app
creation (by non-developers) or even fully automated app creation. You can
think of it as a part of the no-code movement.

If we want to build a scalable LLM application business targeting tens of
thousands of enterprise customers, it does not make sense to write custom code
for each customer. The "Declarative Programming" is the only way to scale such
a business.

## Terminology

- **LLM Application**: A LLM-based application which consists of a collection
  of AI agents, the front-end (the user interface) and associated tools.
- **AI Agent**: A chatbot, which has a specific behavior for a particular
  purpose.
- **Manifest File**: A static file (either in YAML or JSON), which defines the
  behavior of an AI agent, which includes the prompt, templates, and
  definitions of function, REST API, database schema, and embedding database.

## Manifest File

In order to create an AI agent, we need to create a manifest file.

Here is a simple example, which defines a "Brand Manager" agent.

```yaml
title: Brand Manager
prompt:
- You are an experienced marketing person with thirty years of experience.
- You help companies to come up with attractive vision & mission statements,
  and even company names.
```

The *title* defines the title of the agent (for the user). The *prompt* defines
the system prompt to LLM.

When the user select this agent, SlashGPT creates a new chat session with this
manifest file and wait for user's input. When the user enters a question, it
sends that question to GPT 3.5 (which is the default LLM) along with a system
prompt specified in the manifest file, and presents the response to the user.

## Code Interpreter

Here is a slightly complicated example, which defines the "Code Interpreter"
agent on top of Code Llama2.

```yaml
title: Code Interpreter with code_llama
model: code_llama
temperature: 0
form: Write some Python code to {question} (surround it with ```).
notebook: true
prompt:
- You are a data scientist who runs Python code to analyze data.
- When you write code, make sure you explicitly import all necessary libraries,
  such as numpy and matplotlib
```

- The *model* specifies the LLM to use (such as gpt3.5, gpt4, llama2 and palm2).
- The *temperature* defines the temperature for LLM (between 0 and 1.0)
- The *form* defines the template to modify user's question.
- The *notebook* defines if we want to record the interaction in Jupyter
  Notebook or not.

If the user enters a question, "Graph 4 year stock price of apple and tesla
using yfinance", the agent generates the following code.

```py
import yfinance as yf
import matplotlib.pyplot as plt

# Get the stock data for Apple
apple = yf.Ticker('AAPL')
apple_data = apple.history(period='4y')

# Get the stock data for Tesla
tesla = yf.Ticker('TSLA')
tesla_data = tesla.history(period='4y')

# Plot the stock prices
plt.figure(figsize=(12, 6))
plt.plot(apple_data['Close'], label='Apple')
plt.plot(tesla_data['Close'], label='Tesla')
plt.title('4 Year Stock Price of Apple and Tesla')
plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.show()
```

SlashGPT executes this code, and generates the graph below.

![Stock Chart](https://satoshi.blogs.com/mag2/chart_stock.png)

## Plug-ins

SlashGPT also supports plug-ins, which is API compatible with OpenAI's
plug-ins.

Here is an example, which uses an external API to convert currencies.

```yaml
title: Currency Converter
description: Converts currency
temperature: 0
prompt:
- You convert currency values based on the latest exchange rates.
functions:
- description: Convert one currency to another
  name: convert
  parameters:
    properties:
      amount:
        description: Amount to convert
        type: string
      from:
        description: The currency to convert from
        type: string
      to:
        description: The currency to convert to
        type: string
    required:
    - from
    - to
    - amount
    type: object
actions:
  convert:
    type: rest
    url: https://today-currency-converter.oiconma.repl.co/currency-converter?from={from}&to={to}&amount={amount}
```

- The *description* specifies the role of agent (to other agents, not to the user)
- The *functions* defines a set of functions to be called.
- The *actions* defines the implementations of those functions

When the user enters "Please convert 1USD into JPY", the LLM indicates that it
needs to call the following function:

```py
convert(amount=1, from="USD", to="JPY")
```

SlashGPT accesses the REST API specified in the *action* attributes, passes the
result (in JSON) back to the LLM, and the LLM generates a response to the user:

```txt
1 USD is 147.54 JPY
```

## RAG (Retrieval Augmented Generation)

It is possible to create an AI agent, which embeds associated articles from
vector database into the prompt before calling the LLM. Here is an example.

```yaml
title: Olympic 2022
temperature: 0
embeddings:
  db_type: pinecone
  api_key: PINECONE_API_KEY
  api_env: us-east4-gcp
  name: olympic-2022
prompt:
- Use the below articles on the 2022 Winter Olympics to answer the subsequent question.
  If the answer cannot be found in the articles, write 'I could not find an answer'.
- '{articles}'
```

The *embeddings* specifies the type and the location of the embedding database
(a Pinecode database in this case). Notice that the api_key is not the key
itself, but the name of environment variable, which stores the API key.

When the user enters "Please list the names of Japanese athletes won the gold
medal at the 2022 Winter Olympics along with event names they won the medal.",
SlashGPT creates an embedding vector for this string, accesses the embedding
database to retrieve related articles.

Then, SlashGPT will embed those articles in the prompt (as specified in
'{articles}' in the *prompt* property), passes it to LLM to retrieves the
response.

## GraphQL

It is also quite straightforward to use graphQL to retrieve information. Here
is an example, which uses the graphQL endpoint provided by SpaceX.

```yaml
title: SpaceX Information
description: Anything about SpaceX
temperature: 0
actions:
  call_graphQL:
    type: graphQL
    url: https://spacex-production.up.railway.app/graphql
functions:
- description: access graphQL endpoint
  name: call_graphQL
  parameters:
    properties:
      query:
        description: graphQL query
        type: string
    required:
    - query
    type: object
resource: ./resources/templates/spacex.json
prompt:
- You are an expert in GraphQL and use call_graphQL function to retrieve necessary
  information.
- Ask for clarification if a user request is ambiguous.
- 'Here is the schema of GraphQL query:'
- '{resource}'
```

The *resource* specifies the location of graphQL schema file, which will be
embedded in the prompt (as specified by '{resource}' in the *prompt* property).

When the user enters "Who is CEO of SpaceX?" as the question, the LLM indicates
that it needs to call the following function:

```py
call_graphQL('{  "query": "{ company { ceo } }"}')
```

SlashGPT accesses SpaceX's graphQL endpoint, which returns the following reply:

```json
 {"company": {"ceo": "Elon Musk"}}
```

SlashGPT passes this reply to the LLM, and the LLM generates a reply to the user:

```txt
The CEO of SpaceX is Elon Musk.
```
