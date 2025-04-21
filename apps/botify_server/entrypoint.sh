#!/bin/bash

COMMAND=("uvicorn" "app.main:app" "--host" "0.0.0.0" "--port" "8000" )

# Run with exec to handle SIGINT (shutdown signals)
exec "${COMMAND[@]}" "$@"
