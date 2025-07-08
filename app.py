from app import create_app


# API_KEY = "9c13f6cefbb7427eb50eb8c8ca977114"  

app = create_app()
if __name__ == "__main__":
    app.run(debug=True)