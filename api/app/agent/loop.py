import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.agent.prompt import MODEL, SYSTEM_INSTRUCTION, build_user_message
from app.agent.tools import RUN_SQL_DECLARATION, run_sql

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MAX_TURNS = 8


def repair(intent: str, broken_query: str) -> dict:
    history = [
        types.Content(
            role="user",
            parts=[types.Part(text=build_user_message(intent, broken_query))],
        )
    ]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[types.Tool(function_declarations=[RUN_SQL_DECLARATION])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        response_mime_type="application/json",
        response_schema=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "fixed_query": types.Schema(
                    type=types.Type.STRING,
                    description="The corrected SQL SELECT statement, ready to run as-is.",
                ),
                "explanation": types.Schema(
                    type=types.Type.STRING,
                    description="One or two sentences: what was wrong, and what you changed.",
                ),
            },
            required=["fixed_query", "explanation"],
        ),
    )

    statements = []
    turns = 0
    answer = None

    while turns < MAX_TURNS:
        turns += 1

        response = client.models.generate_content(
            model=MODEL, contents=history, config=config
        )

        candidate = response.candidates[0]
        history.append(candidate.content)

        calls = [p.function_call for p in candidate.content.parts if p.function_call]

        if not calls:
            answer = json.loads(response.text)
            break

        responses = []
        for call in calls:
            sql = call.args.get("sql", "")
            result = run_sql(sql)
            statements.append({"sql": sql, "ok": result["ok"]})
            responses.append(
                types.Part.from_function_response(name=call.name, response=result)
            )

        history.append(types.Content(role="user", parts=responses))

    if answer is not None:
        fixed_query = answer["fixed_query"]
        explanation = answer["explanation"]
    else:
        succeeded = [s["sql"] for s in statements if s["ok"]]
        fixed_query = succeeded[-1] if succeeded else None
        explanation = None

    return {
        "fixed_query": fixed_query,
        "explanation": explanation,
        "statements": statements,
        "turns": turns,
        "converged": answer is not None,
    }