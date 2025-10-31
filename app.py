from app import create_app, scheduler

app = create_app()

if __name__ == "__main__":
    scheduler.start()
    app.run(debug=True)
    app.run(host='localhost', port=5000, debug=True)