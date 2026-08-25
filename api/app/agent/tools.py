from google.genai import types

RUN_SQL_DECLARATION = types.FunctionDeclaration(
    name="run_sql",
    description=(
        "Run a read-only SQL query against the sandbox schema and return the rows. "
        "Returns an error message instead of rows if the query is invalid. "
        "Use this to inspect data and to check whether a query works."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "sql": types.Schema(
                type=types.Type.STRING,
                description="A single SELECT statement. Tables live in the sandbox schema.",
            )
        },
        required=["sql"],
    ),
)