from app import create_app, scheduler
import os

app = create_app()

if __name__ == "__main__":
    scheduler.start()
    # app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=5000, debug=True)