from flask import Flask, render_template, request
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

API_KEY = "4cd3c945dc863303d11d4646f46a9590"

analyzer = SentimentIntensityAnalyzer()

# 🎯 Mood → Genre
mood_genre_map = {
    "happy": 35,
    "sad": 18,
    "excited": 28,
    "romantic": 10749,
    "bored": 53
}

# 🧠 Mood detection
def detect_mood(text):
    score = analyzer.polarity_scores(text)
    text = text.lower()

    if "love" in text:
        return "romantic"
    elif "bored" in text:
        return "bored"
    elif score['compound'] >= 0.5:
        return "happy"
    elif score['compound'] <= -0.5:
        return "sad"
    else:
        return "excited"

# 🎬 Get movies with language + fallback
def get_movies(genre_id, language):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres={genre_id}&with_original_language={language}&sort_by=popularity.desc"
    data = requests.get(url).json()
    movies = data.get("results", [])

    # fallback if empty
    if not movies:
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres={genre_id}&sort_by=popularity.desc"
        data = requests.get(url).json()
        movies = data.get("results", [])

    return movies[:25]

# 🎭 Cast
def get_cast(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}"
    data = requests.get(url).json()
    cast = data.get("cast", [])[:3]
    return [c["name"] for c in cast]

# 📺 OTT + TMDb watch link
def get_ott(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={API_KEY}"
    data = requests.get(url).json()

    providers = data.get("results", {}).get("IN", {}).get("flatrate", [])
    link = f"https://www.themoviedb.org/movie/{movie_id}/watch"

    return [{"name": p["provider_name"], "link": link} for p in providers] if providers else [{"name": "Not Available", "link": "#"}]

# 🌐 Main route
@app.route("/", methods=["GET", "POST"])
def home():
    movies = []
    mood = ""

    if request.method == "POST":
        user_input = request.form.get("feeling", "")
        language = request.form.get("language", "en")

        mood = detect_mood(user_input)
        genre_id = mood_genre_map.get(mood, 28)

        movies_data = get_movies(genre_id, language)

        def process_movie(m):
            return {
                "title": m.get("title"),
                "poster": m.get("poster_path"),
                "overview": m.get("overview"),
                "rating": m.get("vote_average"),
                "cast": get_cast(m.get("id")),
                "ott": get_ott(m.get("id"))
            }

        # ⚡ parallel processing (fast)
        with ThreadPoolExecutor(max_workers=10) as executor:
            movies = list(executor.map(process_movie, movies_data))

    return render_template("index.html", movies=movies, mood=mood)

if __name__ == "__main__":
    app.run(debug=True)