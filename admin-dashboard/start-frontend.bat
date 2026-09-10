@echo off
echo Starting Admin Dashboard Frontend...
cd frontend

if not exist node_modules (
    echo Installing dependencies...
    call npm install
)

echo Starting Vite dev server...
call npm run dev
