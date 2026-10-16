Congratulations! You are a context engineer

## 0:20–0:40 · THE GAME HAS CHANGED

Over the last 10 years, analytics engineers have prepared data so people could read it and make sense of it. Now the main reader is an AI agent. Our job are changing

## 0:40–1:00 · THE BUSINESS IS MESSY

Here's what I see in almost every company right now. What the business knows is spread across CRMs, ERPs, wikis, docs, spreadsheets, contracts, email and chat. Every team has its own AI tool, each wired straight to all of it. I've done it myself: my own workflows hitting source systems directly, and a dozen colleagues doing the same thing separately. You pay to wire it, you pay again every time a source changes, and you pay a third time when someone acts on a wrong answer.

## 1:00–1:15 · ONE LAYER. WIRED ONCE.

The alternative is to model the business once, as a context layer, and let every tool read from it. Every tool then gets the same tested definitions, every answer traces back to its source, and when something changes, you fix it in one place.

## 1:15–1:30 · WHY THE DATA TEAM

Model quality is answer quality. So who builds that layer? The team that already owns the data. If "on time" is defined wrong in the model, every agent that reads it is wrong, and confidently so. .

## 1:30–1:45 · JAFFLE LOGISTICS → JAFFLE SELLS A PROMISE

Let me show you. You might know the jaffle shop from dbt Fundamentals. Now it's Jaffle Logistics, a carrier across five cities. It sells a promise: deliver on time, or the customer gets a credit.

## 1:45–2:15 · TOP LINE NUMBERS → WE ASKED AN AI TO READ THE RAW TABLES

Here is a board report I built pointing at the source data directly. Revenue over a hundred million euros. On time at 98%, beating the target every year. But it's wrong: joins were made incorrectly and the agent guessed the metric definition incorrectly. Oops.

## 2:15–2:30 · REVENUE GREW. RELIABILITY FELL.

Here's the report with the real numbers, built on governed data from the Semantic Layer Anybody can confidently build this slide on well-governed data, and it's more important now than ever to do so, because many people are building this data without checking the work

## 2:15–2:30 · drilling in 

Let's drill into the numbers for 2025. We can see that Q1 and Q4 had some lower than expected metrics. Why is that?

## 2:30–2:50 · ONE STORM WEEK BROKE PARIS

For Q1, the answer lies in an incident report within my well-prepared Context Layer. We can quickly learn that in January, a truck jackknifed on an icy on-ramp leaving the Paris hub. The driver was fine fortunately, but Paris ran the month at 56.6% on time. You won't find that story in a fact table

## 2:50–3:10 · THE SECOND CAUSE: ONE DOCK BAY

The Q4 blip turned up in the incident reports too. Eleven of fifteen damage incidents in Amsterdam came from a single dock bay, which had none the year before. Finding the trends and surfacing them is something only the Context Layer can help us with.

## 3:30–3:55 · 3/4 LAYERING ON THE CONTEXT

Some estimates put 80% of a business's knowledge is found in text: incident reports, CRM notes, Slack, and more. That Paris incident report, as well as all the other text data, goes through a process parsed, chunked, embedded and lands in a knowledge base table, through the same dbt pipeline, with the same tests and lineage, the delivering a new treasure trove of trusted data

## 3:55–4:15 · 4/4 HOW A QUESTION BECOMES AN ANSWER

Put both together and an agent can answer "why did Paris miss so many deliveries in January?" The semantic layer supplies the number, the context layer supplies the cause, and the lineage proves both. We can quickly act on more data with confidence

## 4:35–5:00 · HOW TO GET STARTED → CONGRATULATIONS

To get started, build the semantic layer first, then add context with the dbt-context-engineering package. The project, the team and the discipline all stay the same. If you've been doing analytics engineering, congratulations: you're already a context engineer. The full demo repo is linked below.
