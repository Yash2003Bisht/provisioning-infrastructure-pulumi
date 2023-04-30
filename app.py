from source import create_app, debug

app = create_app()

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=debug)
