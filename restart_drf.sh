#!/bin/bash

PORT=8000

echo "Checking for processes using port $PORT..."
PID=$(sudo lsof -t -i :$PORT)

if [ -n "$PID" ]; then
    echo "Killing process $PID on port $PORT..."
    sudo kill -9 $PID
else
    echo "No process found on port $PORT."
fi

echo "Starting Django server on port $PORT..."
python manage.py runserver 0.0.0.0:$PORT
