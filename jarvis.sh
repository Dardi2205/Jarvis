#!/bin/bash

# JARVIS Service Manager
case "$1" in
    start)
        echo "Starting JARVIS..."
        ollama serve &
        sleep 5
        cd /opt/jarvis
        nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 &
        echo "JARVIS started on port 8080"
        ;;
    stop)
        echo "Stopping JARVIS..."
        pkill -f "uvicorn backend.main"
        echo "JARVIS stopped"
        ;;
    status)
        if pgrep -f "uvicorn backend.main" > /dev/null; then
            echo "JARVIS is running"
        else
            echo "JARVIS is stopped"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac
