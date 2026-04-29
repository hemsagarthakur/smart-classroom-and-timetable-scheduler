import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    CHARTS_FOLDER = "static/charts"
    MAX_TIMETABLE_VARIANTS = 5
    GA_POPULATION = 200
    GA_GENERATIONS = 300
    GA_CROSSOVER_PROB = 0.7
    GA_MUTATION_PROB = 0.2
    EXPORT_FOLDER = os.path.join("static", "exports")