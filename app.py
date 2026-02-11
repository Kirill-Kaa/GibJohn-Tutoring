from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = "SECRET123"

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)