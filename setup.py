from setuptools import setup, find_packages

setup(
    name="bill-sharing-app",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.3.0",
        "Flask-SQLAlchemy>=3.0.0",
        "Werkzeug>=2.3.0",
        "gunicorn>=20.1.0",
        "python-dotenv>=1.0.0",
        "psycopg2-binary>=2.9.0",
        "requests>=2.28.0",
    ],
    python_requires=">=3.8",
)
